# Copyright (c) 2018 - 2021 TomTom N.V. (https://tomtom.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import logging
import os
from pathlib import PurePath
import re
import sys
from typing import (
    Any,
    IO,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    NoReturn,
    Optional,
    Pattern,
    Tuple,
    Type,
    Union,
)

if sys.version_info[:2] >= (3, 8):
    from typing import (
        Final,
        Protocol,
    )
else:
    from typing_extensions import (
        Final,
        Protocol,
    )

from io import (
    open,
)

from .errors import VersioningError
from .types import (
    Stringable,
    TBD,
)


__all__ = (
    'CarusoVer',
    'GitVersion',
    'SemVer',
    "Version",
    'read_version',
    'replace_version',
)

log = logging.getLogger(__name__)


class _IdentifierList(tuple):
    def __str__(self) -> str:
        return '.'.join(self)


class Version(Protocol):
    version_re: Pattern  # mypy doesn't handle ClassVar
    default_tag_name: str  # mypy doesn't handle ClassVar

    major: int
    minor: int
    patch: int
    prerelease: Tuple[str, ...]

    def __iter__(self) -> Iterator[Any]: ...

    @classmethod
    def parse(cls, s: str) -> Optional["Version"]: ...

    def next_version(self, bump: Any, **kwargs: Any) -> "Version": ...
    def next_version_for_commits(self, commits: Iterable[TBD]) -> "Version": ...

    def __eq__(self, rhs: Any) -> bool: ...
    def __ne__(self, rhs: Any) -> bool: ...
    def __lt__(self, rhs: "Version") -> bool: ...
    def __le__(self, rhs: "Version") -> bool: ...
    def __gt__(self, rhs: "Version") -> bool: ...
    def __ge__(self, rhs: "Version") -> bool: ...


class SemVer(Version):
    """
    Semantic versioning policy.

    This policy is based on Semantic Versioning 2.0.0: https://semver.org/spec/v2.0.0.html

     * Parsing and serialization is according to the syntax specified by 'semver'.
     * Version comparison and ordering is implemented exactly as specified by 'semver'.
     * Version incrementing is implemented exactly as specified by 'semver' for the major, minor and patch fields.
      - 'semver' doesn't specify a strategy for incrementing of the prerelease field, thus:
       + given a version B, constructed by incrementing the prerelease field of A
       + and a version C, constructed by incrementing the prerelease of B
       + and a version D, constructed by incrementing the patch field of A
       + we ensure that:
        * A always sorts before B; and
        * B always sorts before C; and
        * C always sorts before D; and
        * that this relationship is transitive
    """
    __slots__ = ('major', 'minor', 'patch', 'prerelease', 'build')
    default_tag_name = "{version.major}.{version.minor}.{version.patch}{version.prerelease_separator}{version.prerelease}"

    def __init__(self, major: int, minor: int, patch: int, prerelease: Tuple[str, ...], build: Tuple[str, ...]):
        super().__init__()
        self.major      = major
        self.minor      = minor
        self.patch      = patch
        self.prerelease = prerelease
        self.build      = build

    def __setattr__(self, name, value):
        if name in {'major', 'minor', 'patch'}:
            return super().__setattr__(name, int(value))
        elif name in {'prerelease', 'build'}:
            return super().__setattr__(name, _IdentifierList(value))

    def __iter__(self) -> Iterator[TBD]:
        return iter(getattr(self, attr) for attr in self.__class__.__slots__)

    def __repr__(self) -> str:
        return '%s(major=%r, minor=%r, patch=%r, prerelease=%r, build=%r)' % ((self.__class__.__name__,) + tuple(self))

    @property
    def prerelease_separator(self) -> str:
        return "-" if self.prerelease else ""

    @property
    def build_separator(self) -> str:
        return "+" if self.build else ""

    def __str__(self) -> str:
        ver = '.'.join(str(x) for x in tuple(self)[:3])
        ver += f"{self.prerelease_separator}{self.prerelease}"
        ver += f"{self.build_separator}{self.build}"
        return ver

    version_re = re.compile(
        r'^(?:version=)?'
      + r'(?P<major>0|[1-9][0-9]*)'                                  # noqa: E131
      + r'\.(?P<minor>0|[1-9][0-9]*)'
      + r'\.(?P<patch>0|[1-9][0-9]*)'
      + r'(?:-(?P<prerelease>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z]+)*))?'
      + r'(?:\+(?P<build>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z]+)*))?'
      + r'\s*$'
    )

    @classmethod
    def parse(cls, s: str) -> Optional["SemVer"]:
        m = cls.version_re.match(s)
        if not m:
            return None

        major, minor, patch = (int(c) for c in m.groups()[:3])

        if m.group("prerelease") is not None:
            prerelease = tuple(m.group("prerelease").split("."))
        else:
            prerelease = ()

        if m.group("build") is not None:
            build = tuple(m.group("build").split("."))
        else:
            build = ()

        return cls(major, minor, patch, prerelease, build)

    def next_major(self) -> "SemVer":
        if self.prerelease and self.minor == 0 and self.patch == 0:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major + 1, 0, 0, (), ())

    def next_minor(self) -> "SemVer":
        if self.prerelease and self.patch == 0:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major, self.minor + 1, 0, (), ())

    def next_patch(self) -> "SemVer":
        if self.prerelease:
            # Just strip pre-release
            return SemVer(self.major, self.minor, self.patch, (), ())

        return SemVer(self.major, self.minor, self.patch + 1, (), ())

    _number_re = re.compile(r'^(?:[1-9][0-9]*|0)$')
    def next_prerelease(self, seed: Optional[Stringable] = None) -> "SemVer":  # noqa: E301 'expected 1 blank line'
        # Special case for if we don't have a prerelease: bump patch and seed prerelease
        if not self.prerelease:
            if isinstance(seed, str):
                seed = (seed,)
            elif not seed:
                seed = ('1',)
            seed = tuple(str(i) for i in seed)

            return SemVer(self.major, self.minor, self.patch + 1, seed, ())

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
          + (str(int(self.prerelease[increment_idx]) + 1),)  # noqa: E131
          + self.prerelease[increment_idx + 1:]
        )
        return SemVer(self.major, self.minor, self.patch, prerelease, ())

    def next_version(self, bump="prerelease", **kwargs: TBD) -> "SemVer":
        if bump == 'prerelease' and 'prerelease_seed' in kwargs:
            kwargs = kwargs.copy()
            kwargs['seed'] = kwargs.pop('prerelease_seed')
        return {  # type: ignore[operator]
            'prerelease': self.next_prerelease,
            'patch'     : self.next_patch,
            'minor'     : self.next_minor,
            'major'     : self.next_major,
        }[bump](**kwargs)

    def next_version_for_commits(self, commits: Iterable[TBD]) -> "SemVer":
        has_new_feature = False
        has_fix = False
        for commit in commits:
            if commit.has_breaking_change():
                return self.next_major()
            if commit.has_new_feature():
                has_new_feature = True
            if commit.has_fix():
                has_fix = True
        if has_new_feature:
            return self.next_minor()
        elif has_fix:
            return self.next_patch()
        return self

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        if tuple(self)[:4] != tuple(rhs)[:4]:
            return False
        if self.build != rhs.build:
            return NotImplemented
        return True

    def __ne__(self, rhs: object) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        if tuple(self)[:4] != tuple(rhs)[:4]:
            return True
        if self.build != rhs.build:
            return NotImplemented
        return False

    def __lt__(self, rhs: Version) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
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

        a: Union[int, str]
        b: Union[int, str]
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
            if a < b:  # type: ignore[operator]
                return True
            elif b < a:  # type: ignore[operator]
                return False

        return len(self.prerelease) < len(rhs.prerelease)

    def __le__(self, rhs: Version) -> bool:
        return self < rhs or tuple(self)[:-1] == tuple(rhs)[:-1]

    def __gt__(self, rhs: Version) -> bool:
        return rhs < self

    def __ge__(self, rhs: Version) -> bool:
        return rhs <= self


class CarusoVer(Version):
    """Caruso-specific versioning policy, overlaps with semantic versioning in syntax but definitely not compatible."""
    __slots__ = ('major', 'minor', 'patch', 'prerelease', 'increment', 'fix')
    default_tag_name = "{version.major}.{version.minor}.{version.patch}{version.prerelease_separator}{version.prerelease}+PI{version.increment}.{version.fix}"

    def __init__(self, major: int, minor: int, patch: int, prerelease: Tuple[str, ...], increment: int, fix: int):
        super().__init__()
        self.major      = major
        self.minor      = minor
        self.patch      = patch
        self.prerelease = prerelease
        self.increment  = increment
        self.fix        = fix

    def __setattr__(self, name, value):
        if name in {'major', 'minor', 'patch', 'increment', 'fix'}:
            return super().__setattr__(name, int(value))
        elif name in {'prerelease'}:
            return super().__setattr__(name, _IdentifierList(value))

    def __iter__(self) -> Iterator[TBD]:
        return iter(getattr(self, attr) for attr in self.__class__.__slots__)

    def __repr__(self) -> str:
        return '%s(major=%r, minor=%r, patch=%r, prerelease=%r, increment=%r, fix=%r)' % ((self.__class__.__name__,) + tuple(self))

    @property
    def prerelease_separator(self) -> str:
        return "-" if self.prerelease else ""

    def __str__(self) -> str:
        ver = '.'.join(str(x) for x in tuple(self)[:3])
        ver += f"{self.prerelease_separator}{self.prerelease}"
        ver += f"+PI{self.increment}.{self.fix}"
        return ver

    version_re = re.compile(
        r'^(?:version=)?'
      + r'(?P<major>0|[1-9][0-9]*)'                                  # noqa: E131
      + r'\.(?P<minor>0|[1-9][0-9]*)'
      + r'\.(?P<patch>0|[1-9][0-9]*)'
      + r'(?:-(?P<prerelease>[-0-9a-zA-Z]+(?:\.[-0-9a-zA-Z]+)*))?'
      + r'\+PI(?P<increment>0|[1-9][0-9]*)\.(?P<fix>0|[1-9][0-9]*)'
      + r'\s*$'
    )

    @classmethod
    def parse(cls, s: str) -> Optional["CarusoVer"]:
        m = cls.version_re.match(s)
        if not m:
            return None

        major = int(m.group("major"))
        minor = int(m.group("minor"))
        patch = int(m.group("patch"))
        increment = int(m.group("increment"))
        fix = int(m.group("fix"))

        if m.group("prerelease") is not None:
            prerelease = tuple(m.group("prerelease").split("."))
        else:
            prerelease = ()

        return cls(major, minor, patch, prerelease, increment, fix)

    def next_fix(self) -> "CarusoVer":
        if self.prerelease:
            # Just strip pre-release
            return CarusoVer(self.major, self.minor, self.patch, (), self.increment, self.fix)

        return CarusoVer(self.major, self.minor, self.patch, (), self.increment, self.fix + 1)

    _number_re = re.compile(r'^(?:[1-9][0-9]*|0)$')
    def next_prerelease(self, seed: Optional[Stringable] = None) -> "CarusoVer":  # noqa: E301 'expected 1 blank line'
        # Special case for if we don't have a prerelease: bump patch and seed prerelease
        if not self.prerelease:
            if isinstance(seed, str):
                seed = (seed,)
            elif not seed:
                seed = ('1',)
            seed = tuple(str(i) for i in seed)

            return CarusoVer(self.major, self.minor, self.patch, seed, self.increment, self.fix + 1)

        # Find least significant numeric identifier to increment
        increment_idx = None
        for idx, elem in reversed(list(enumerate(self.prerelease))):
            if self._number_re.match(elem):
                increment_idx = idx
                break
        if increment_idx is None:
            return CarusoVer(self.major, self.minor, self.patch, self.prerelease + ('1',), self.increment, self.fix)

        # Increment only the specified identifier
        prerelease = (
            self.prerelease[:increment_idx]
          + (str(int(self.prerelease[increment_idx]) + 1),)  # noqa: E131
          + self.prerelease[increment_idx + 1:]
        )
        return CarusoVer(self.major, self.minor, self.patch, prerelease, self.increment, self.fix)

    def next_version(self, bump="prerelease", **kwargs: TBD) -> "CarusoVer":
        if bump == 'prerelease' and 'prerelease_seed' in kwargs:
            kwargs = kwargs.copy()
            kwargs['seed'] = kwargs.pop('prerelease_seed')
        return {  # type: ignore[operator]
            'prerelease': self.next_prerelease,
            'fix'       : self.next_fix,
        }[bump](**kwargs)

    def next_version_for_commits(self, commits: Iterable[TBD]) -> NoReturn:
        raise NotImplementedError

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        return tuple(self) == tuple(rhs)

    def __ne__(self, rhs: object) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        return tuple(self) != tuple(rhs)

    def __lt__(self, rhs: Version) -> bool:
        if not isinstance(rhs, self.__class__):
            return NotImplemented
        lhs_t = tuple(self)[:3] + tuple(self)[4:6]
        rhs_t = tuple(rhs)[:3] + tuple(rhs)[4:6]
        if lhs_t < rhs_t:
            return True
        if lhs_t > rhs_t:
            return False

        if self.prerelease and not rhs.prerelease:
            # Having a prerelease sorts before not having one
            return True
        elif not self.prerelease:
            return False

        assert self.prerelease and rhs.prerelease

        a: Union[str, int]
        b: Union[str, int]
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
            if a < b:  # type: ignore[operator]
                return True
            elif b < a:  # type: ignore[operator]
                return False

        return len(self.prerelease) < len(rhs.prerelease)

    def __le__(self, rhs: Version) -> bool:
        return self < rhs or self == rhs

    def __gt__(self, rhs: Version) -> bool:
        return rhs < self

    def __ge__(self, rhs: Version) -> bool:
        return rhs <= self


_rejected_hotfix_prefixes = frozenset((
    "a",
    "b",
    "c",
    "rc",
    "alpha",
    "beta",
    "pre",
    "preview",
    "post",
    "rev",
    "r",
    "dev",
))


def hotfix_id(pat: Union[str, Pattern], branch_name: Optional[str]) -> Tuple[str, ...]:
    """
    Extracts a hotfix ID from a hotfix branch name using the given regular expression.
    """
    if branch_name is None:
        return ()

    if not isinstance(pat, Pattern):
        pat = re.compile(pat)

    idx = pat.groupindex.get("id", pat.groupindex.get("ID", 1))

    m = pat.match(branch_name)
    if not m:
        return ()

    hotfix = m.group(idx)

    if not re.match(r"^[a-zA-Z](?:[-.a-zA-Z0-9]*[a-zA-Z0-9])?$", hotfix):
        raise VersioningError(f"Hotfix ID '{hotfix}' is not a valid identifier")
    prefix = re.split(r"[-.]", hotfix)[0]
    if re.sub(r"[0-9]+$", "", prefix) in _rejected_hotfix_prefixes:
        raise VersioningError(f"Hotfix ID '{hotfix}' starts with reserved prefix {prefix}")

    return _IdentifierList(hotfix.split("."))


_fmts: Mapping[str, Type[Version]] = {
    'semver': SemVer,
    'carver': CarusoVer,
}


def read_version(fname, format="semver", encoding: Optional[str] = None) -> Optional[Version]:
    fmt = _fmts[format]

    with open(fname, 'r', encoding=encoding) as f:
        for line in f:
            version = fmt.parse(line)
            if version is not None:
                return version

    return None


# NOTE: while this is a regular language, it's one who's captures cannot be described if put in a single regex
_git_describe_commit_re: Final = re.compile(r"^(?:(.*)-g)?([0-9a-f]+)$")
_git_describe_distance_re: Final = re.compile(r"^(.*)-([0-9]+)$")

_semver_tag_cleanup: Final = re.compile(r"^[^0-9]+")


class GitVersion(NamedTuple):
    tag_name     : str
    dirty        : bool = False
    commit_count : Optional[int] = None
    commit_hash  : Optional[str] = None

    @property
    def exact(self) -> bool:
        return not self.dirty and self.commit_count == 0

    @classmethod
    def from_description(cls, description: str) -> "GitVersion":
        dirty = description.endswith('-dirty')
        if dirty:
            description = description[:-len('-dirty')]

        abbrev_commit_hash = None
        commit_match = _git_describe_commit_re.match(description)
        if commit_match:
            description, abbrev_commit_hash = commit_match.groups()
            if description is None:
                description = ''

        commit_count = None
        count_match = _git_describe_distance_re.match(description)
        if count_match:
            commit_count = int(count_match.group(2))
            tag_name = count_match.group(1)
        else:
            tag_name = description

        return cls(tag_name=tag_name, dirty=dirty, commit_count=commit_count, commit_hash=abbrev_commit_hash)

    def to_version(self, format="semver", dirty_date: Optional[datetime] = None) -> Optional[Version]:
        assert format == 'semver', f"Wrong format: {format}"
        version_part = _semver_tag_cleanup.sub("", self.tag_name)
        tag_version = SemVer.parse(version_part)
        if tag_version is None:
            if log.isEnabledFor(logging.WARNING):
                if self.commit_count is not None:
                    describe_out = f"{self.tag_name}-{self.commit_count}"
                else:
                    describe_out = self.tag_name
                if self.commit_hash is not None:
                    if describe_out:
                        describe_out += "-"
                    describe_out += self.commit_hash
                if describe_out and self.dirty:
                    describe_out += "-dirty"

                log.warning("Failed to parse version string %r as %s (from 'git describe' output %r)", version_part, format, describe_out)
            return None

        if (self.commit_count or self.dirty) and not tag_version.prerelease:
            tag_version = tag_version.next_patch()

        if self.commit_count:
            tag_version.prerelease = tag_version.prerelease + (str(self.commit_count),)
        if self.dirty:
            if dirty_date is None:
                dirty_date = datetime.utcnow()
            if not self.commit_count:
                # Ensure that 'dirty' commits sort before the next non-dirty commit
                tag_version.prerelease = tag_version.prerelease + ('0',)
            tag_version.prerelease = tag_version.prerelease + ('dirty', dirty_date.strftime('%Y%m%d%H%M%S'))
        if self.commit_hash is not None:
            tag_version.build = tag_version.build + ('g' + self.commit_hash,)
        return tag_version


def replace_version(fname: PurePath, new_version: Version, encoding: Optional[str] = None, outfile: Optional[IO[str]] = None) -> None:

    out = outfile
    temp = None
    if out is None:
        out = temp = open(fname.with_suffix(fname.suffix + ".tmp"), "w", encoding=encoding)

    try:
        with open(fname, 'r', encoding=encoding) as f:
            for line in f:
                # Replace version in source line
                m = new_version.version_re.match(line)
                if m:
                    line = line[:m.start(1)] + str(new_version) + line[m.end(m.lastindex or 0):]
                out.write(line)
    except:  # noqa: E722: we re-raise, so it's not a problem
        if temp is not None:
            temp.close()
            os.remove(temp.name)
        raise
    else:
        if temp is not None:
            temp.close()
            os.rename(temp.name, fname)
