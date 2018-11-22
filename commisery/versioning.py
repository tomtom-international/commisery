from .execution import echo_cmd
from collections import namedtuple
import click
import re
import subprocess
import sys

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__all__ = (
        'bump_version',
        'stringify_semver',
    )

SemVer = namedtuple('SemVer', ('major', 'minor', 'patch', 'prerelease', 'build'))

_semver_re = re.compile(r'^(?:version=)?(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)(?:-(?P<prerelease>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z])*))?(?:\+(?P<build>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z])*))?$')
def parse_semver(s):
    m = _semver_re.match(s)
    if not m:
        return None

    major, minor, patch, prerelease, build = m.groups()

    major, minor, patch = int(major), int(minor), int(patch)

    if prerelease is None:
        prerelease = ()
    else:
        prerelease = tuple(prerelease.split('.'))

    if build is None:
        build = ()
    else:
        build = tuple(build.split('.'))

    return SemVer(major, minor, patch, prerelease, build)

def stringify_semver(major, minor, patch, prerelease, build):
    ver = '.'.join(str(x) for x in (major, minor, patch))
    if prerelease:
        ver += '-' + '.'.join(prerelease)
    if build:
        ver += '+' + '.'.join(build)
    return ver

_number_re = re.compile(r'^\d+$')
def bump_version(workspace, file, format='semver', bump='prerelease', **_):
    version = None
    new_content = StringIO()
    with open(file, 'r') as f:
        for l in f:
            ver = None
            if format == 'semver':
                ver = parse_semver(l)
            if ver is None:
                new_content.write(l)
                continue

            assert version is None, "multiple versions are not supported"
            version = ver

            if bump:
                major, minor, patch, prerelease, build = version

                if bump == 'prerelease':
                    increment_idx = None
                    for idx, elem in reversed(list(enumerate(prerelease))):
                        if _number_re.match(elem):
                            increment_idx = idx
                            break
                    if increment_idx is not None:
                        prerelease = (
                                prerelease[:increment_idx]
                              + (str(int(prerelease[increment_idx]) + 1),)
                              + prerelease[increment_idx + 1:]
                            )
                    else:
                        prerelease = prerelease + ('1',)

                    # When bumping the prerelease tag the build tags need to be dropped always
                    build = ()
                elif bump == 'patch':
                    if not prerelease:
                        patch += 1

                    # When bumping version the prerelease and build tags need to be dropped always
                    prerelease, build = (), ()
                elif bump == 'minor':
                    if not (prerelease and patch == 0):
                        minor += 1
                    patch = 0

                    # When bumping version the prerelease and build tags need to be dropped always
                    prerelease, build = (), ()
                elif bump == 'major':
                    if not (prerelease and minor == 0 and patch == 0):
                        major += 1
                    major = 0
                    minor = 0

                    # When bumping version the prerelease and build tags need to be dropped always
                    prerelease, build = (), ()
                else:
                    click.echo("Invalid version bumping target: {bump}".format(**locals()), err=True)
                    sys.exit(1)

                version = SemVer(major, minor, patch, prerelease, build)

                # Replace version in source line
                m = _semver_re.match(l)
                new_line = l[:m.start(1)] + stringify_semver(*version) + l[m.end(m.lastgroup)]
                new_content.write(new_line)

    if bump:
        assert version is not None, "no version found"
        with open(file, 'w') as f:
            f.write(new_content.getvalue())
        echo_cmd(subprocess.check_call, ('git', 'add', file), cwd=workspace)

    return version
