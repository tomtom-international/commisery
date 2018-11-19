from .execution import echo_cmd
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
    )

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

    return (major, minor, patch, prerelease, build)

def stringify_semver(major, minor, patch, prerelease, build):
    ver = '.'.join(str(x) for x in (major, minor, patch))
    if prerelease:
        ver += '-' + '.'.join(prerelease)
    if build:
        ver += '+' + '.'.join(build)
    return ver

def bump_version(workspace, file, format='semver', bump='patch', **_):
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

                if bump == 'patch':
                    if not prerelease:
                        patch += 1
                elif bump == 'minor':
                    if not (prerelease and patch == 0):
                        minor += 1
                    patch = 0
                elif bump == 'major':
                    if not (prerelease and minor == 0 and patch == 0):
                        major += 1
                    major = 0
                    minor = 0
                else:
                    click.echo("Invalid version bumping target: {bump}".format(**locals()), err=True)
                    sys.exit(1)

                # When bumping the prerelease tags need to be dropped always
                prerelease, build = (), ()

                version = (major, minor, patch, prerelease, build)

                # Replace version in source line
                m = _semver_re.match(l)
                new_line = l[:m.start(1)] + stringify_semver(*version) + l[m.end(m.lastgroup)]
                new_content.write(new_line)

    if bump:
        assert version is not None, "no version found"
        with open(file, 'w') as f:
            f.write(new_content.getvalue())
        echo_cmd(subprocess.check_call, ('git', 'add', file), cwd=workspace)

    return (stringify_semver(*version) if version is not None else version)
