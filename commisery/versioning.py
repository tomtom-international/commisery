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
        'SemVer',
        'read_version',
        'replace_version',
    )

class _IdentifierList(tuple):
    def __str__(self):
        return '.'.join(self)

class SemVer(object):
    __slots__ = ('major', 'minor', 'patch', 'prerelease', 'build')

    def __init__(self, major, minor, patch, prerelease, build):
        assert isinstance(major, int)
        assert isinstance(minor, int)
        assert isinstance(patch, int)

        super(SemVer, self).__init__()
        self.major      = major
        self.minor      = minor
        self.patch      = patch
        self.prerelease = _IdentifierList(prerelease)
        self.build      = _IdentifierList(build)

    def __iter__(self):
        return iter(getattr(self, attr) for attr in self.__class__.__slots__)

    def __repr__(self):
        return '%s(major=%r, minor=%r, patch=%r, prerelease=%r, build=%r)' % ((self.__class__.__name__,) + tuple(self))

    def __str__(self):
        ver = '.'.join(str(x) for x in tuple(self)[:3])
        if self.prerelease:
            ver += '-' + str(self.prerelease)
        if self.build:
            ver += '+' + str(self.build)
        return ver

    version_re = re.compile(r'^(?:version=)?(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)(?:-(?P<prerelease>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z])*))?(?:\+(?P<build>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z])*))?$')
    @classmethod
    def parse(cls, s):
        m = cls.version_re.match(s)
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

        return cls(major, minor, patch, prerelease, build)

    def next_major(self):
        if self.prerelease and self.minor == 0 and self.patch == 0:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major + 1, 0, 0, (), ())

    def next_minor(self):
        if self.prerelease and self.patch == 0:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major, self.minor + 1, 0, (), ())

    def next_patch(self):
        if self.prerelease:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major, self.minor, self.patch + 1, (), ())

    _number_re = re.compile(r'^(?:[1-9][0-9]*|0)$')
    def next_prerelease(self):
        # Find least significant numeric identifier to increment
        increment_idx = None
        for idx, elem in reversed(list(enumerate(self.prerelease))):
            if self._number_re.match(elem):
                increment_idx = idx
                break
        if increment_idx is None:
            return SemVer(self.major, self.minor, self.patch, self.prerelease + ('1',), ())

        # Increment only the specified identifier
        prerelease = (
                self.prerelease[:increment_idx]
              + (str(int(self.prerelease[increment_idx]) + 1),)
              + self.prerelease[increment_idx + 1:]
            )
        return SemVer(self.major, self.minor, self.patch, prerelease, ())

    def next_version(self, bump='prerelease', *args, **kwargs):
        return {
                'prerelease': self.next_prerelease,
                'patch'     : self.next_patch     ,
                'minor'     : self.next_minor     ,
                'major'     : self.next_major     ,
            }[bump](*args, **kwargs)

    def __eq__(self, rhs):
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        if tuple(self)[:4] != tuple(rhs)[:4]:
            return False
        if self.build != rhs.build:
            return NotImplemented
        return True

    def __ne__(self, rhs):
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        if tuple(self)[:4] != tuple(rhs)[:4]:
            return True
        if self.build != rhs.build:
            return NotImplemented
        return False

    def __lt__(self, rhs):
        if tuple(self)[:3] < tuple(rhs)[:3]:
            return True
        if tuple(self)[:3] != tuple(rhs)[:3]:
            return False

        if self.prerelease and not rhs.prerelease:
            # Having a prerelease sorts before not having one
            return True
        elif not self.prerelease:
            return False

        assert self.prerelease and rhs.prerelease

        for a, b in zip(self.prerelease, rhs.prerelease):
            try:
                a = int(a)
            except ValueError:
                pass
            try:
                b = int(b)
            except ValueError:
                pass
            if isinstance(a, int) and not isinstance(b, int):
                # Numeric identifiers sort before non-numeric ones
                return True
            elif isinstance(a, int) != isinstance(b, int):
                return False
            if a < b:
                return True
            elif b < a:
                return False

        return len(self.prerelease) < len(rhs.prerelease)

    def __le__(self, rhs):
        return self < rhs or self == rhs

    def __gt__(self, rhs):
        return rhs < self

    def __ge__(self, rhs):
        return rhs <= self

_fmts = {
        'semver': SemVer,
    }

def read_version(fname, format='semver'):
    fmt = _fmts[format]

    with open(fname, 'r') as f:
        for line in f:
            version = fmt.parse(line)
            if version is not None:
                return version

def replace_version(fname, new_version):

    new_content = StringIO()
    with open(fname, 'r') as f:
        for line in f:
            # Replace version in source line
            m = new_version.version_re.match(line)
            if m:
                line = line[:m.start(1)] + str(new_version) + line[m.end(m.lastgroup)]
            new_content.write(line)

    with open(fname, 'w') as f:
        f.write(new_content.getvalue())
