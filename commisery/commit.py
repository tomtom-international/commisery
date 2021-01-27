# Copyright (c) 2018 - 2019 TomTom N.V. (https://tomtom.com)
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

from collections import namedtuple
import re
import typing


_Footer = namedtuple('Footer', ('token', 'value'))


class CommitMessage(object):
    line_separator = '\n'
    paragraph_separator = '\n\n'
    autosquash_re = re.compile(r'^(?:(?:fixup|squash)!\s+)+')
    merge_re = re.compile(r'^Merge.*?:[ \t]*')

    # Variation of conventional commits footer that more closely matches 'git trailers'.
    # In particular it doesn't permit 'BREAKING CHANGE' (with a space, instead of '-') as a footer's token.
    footer_re = re.compile(r'''
    # 8.  One or more footers MAY be provided one blank line after the body. ...
    \n

    # 8.  ... Each footer MUST consist of a word token, ...
    (?P<token>

    # 9.  A footer's token MUST use `-` in place of whitespace characters, e.g. `Acked-by` (this helps differentiate
    #     the footer section from a multi-paragraph body). ...
        \w+(?:-\w+)*
    )

    # 8.  ..., followed by either a `: ` or ` #` separator, followed by a string value (this is inspired by the git
    #     trailer convention).
    (?::[ ]|[ ](?=[#]))
    ''', re.VERBOSE)

    def __init__(self, message, hexsha=None):
        if isinstance(message, str):
            self.message = _strip_message(message)
        else:
            self.message = _strip_message(message.message)
            try:
                if hexsha is None:
                    hexsha = message.hexsha
            except AttributeError:
                pass
        if hexsha is not None:
            self.hexsha = hexsha

        # Discover starts of lines
        self._line_index = [m.end() for m in re.finditer(self.line_separator, self.message)]
        self._line_index.insert(0, 0)
        if len(self._line_index) < 2 or self._line_index[-1] < len(self.message):
            self._line_index.append(len(self.message) + 1)

        autosquash = self.autosquash_re.match(self.message)
        self._autosquash_end = autosquash.end() if autosquash is not None else 0

        merge = self.merge_re.match(self.message[self._autosquash_end:])
        self._subject_start = self._autosquash_end + (merge.end() if merge is not None else 0)

        # Discover starts of paragraphs
        self._paragraph_index = [m.end() for m in re.finditer(self.paragraph_separator, self.message)]
        if not self.message[self._line_index[1] - len(self.line_separator):].startswith(self.paragraph_separator):
            self._paragraph_index.insert(0, self._line_index[1])
        self._paragraph_index.append(len(self.message) + len(self.paragraph_separator))

        # Strip last line terminator from the last paragraph.
        if self.message and self.message[-1] == self.line_separator:
            self._paragraph_index[-1] -= 1

        self._footer_index = [(m.group('token'), m.start(), m.end()) for m in self.footer_re.finditer(self.message)]

    @property
    def lines(self):
        return _IndexedList(self.message, self._line_index, self.line_separator)

    @property
    def full_subject(self):
        return self.message[:self._line_index[1] - 1]

    @property
    def subject_start(self):
        return self._subject_start

    @property
    def subject(self):
        return self.full_subject[self.subject_start:]

    @property
    def autosquash_end(self):
        return self._autosquash_end

    def needs_autosquash(self):
        return self.autosquash_end > 0

    @property
    def autosquashed_subject(self):
        return self.full_subject[self.autosquash_end:]

    @property
    def body(self):
        return self.message[self._paragraph_index[0]:]

    @property
    def paragraphs(self):
        return _IndexedList(self.message, self._paragraph_index, self.paragraph_separator)

    def paragraph_line(self, idx):
        if idx < 0:
            idx += len(self._paragraph_index) - 1
        idx = self._paragraph_index[idx]
        return self.message[:idx].count(self.line_separator)

    @property
    def footers(self):
        return _FooterList(self.message, self._footer_index)

    def has_breaking_change(self):
        return None

    def has_new_feature(self):
        return None

    def has_fix(self):
        return None

    def __repr__(self):
        try:
            return f"{self.__class__.__name__}({self.message!r}, {self.hexsha!r})"
        except AttributeError:
            return f"{self.__class__.__name__}({self.message!r})"


class ConventionalCommit(CommitMessage):
    strict_subject_re = re.compile(r'''
    ^
    # 1. Commits MUST be prefixed with a type, which consists of a noun, feat, fix, etc., ...
    (?P<type_tag>\w+)

    # 4. A scope MAY be provided after a type. A scope MUST consist of a noun describing a section of the codebase
    #    surrounded by parenthesis, e.g., `fix(parser):`
    (?: \( (?P<scope> [^()]* ) \) )?

    # 1. Commits MUST be prefixed with a type, ..., followed by ..., OPTIONAL `!`, ...
    (?P<breaking>\s*!(?:\s+(?=:))?)?

    # 1. Commits MUST be prefixed with a type, ..., and REQUIRED terminal colon and space.
    (?P<separator>:?[ ]?)

    # 5. A description MUST immediately follow the colon and space after the type/scope prefix. The description is a
    #    short description of the code changes, e.g., fix: array parsing issue when multiple spaces were contained in
    #    string.
    (?P<description>.*)
    $
    ''', re.VERBOSE)

    footer_re = re.compile(r'''
    # 8.  One or more footers MAY be provided one blank line after the body. ...
    \n

    # 8.  ... Each footer MUST consist of a word token, ...
    (?P<token>

    # 9.  A footer's token MUST use `-` in place of whitespace characters, e.g. `Acked-by` (this helps differentiate
    #     the footer section from a multi-paragraph body). ...
        \w+(?:-\w+)*

    # 9.  ... An exception is made for `BREAKING CHANGE`, which MAY
    #     also be used as a token.
    | BREAKING[ ]CHANGE
    )

    # 8.  ..., followed by either a `: ` or ` #` separator, followed by a string value (this is inspired by the git
    #     trailer convention).
    (?::[ ]|[ ](?=[#]))
    ''', re.VERBOSE)

    def __init__(self, message, hexsha=None):
        super().__init__(message, hexsha=hexsha)
        m = self.strict_subject_re.match(self.subject)
        if not m:
            raise RuntimeError(f"commit message's subject ({self.subject!r}) not formatted according to Conventional Commits ({self.strict_subject_re.pattern})")
        self.type_tag     = m.group('type_tag')
        self.scope        = m.group('scope')
        self._is_breaking = m.group('breaking')
        self.description  = m.group('description')

        issues = []
        if re.search(r'[A-Z]', self.type_tag):
            issues.append("commit message's type tag ({self.type_tag!r}) contains upper case letters but isn't allowed to".format(self=self))

        if self.scope is not None and not re.match(r'^\S+(?:.*\S+)?$', self.scope):
            issues.append("commit message's scope ({self.scope!r}) is empty or contains excess whitespace but shouldn't".format(self=self))

        if self._is_breaking is not None and self._is_breaking != '!':
            issues.append("breaking change indicator in commit message's subject should be exactly '!' (have: {self._is_breaking!r})".format(self=self))

        if m.group('separator') != ': ':
            issues.append("commit message's subject lacks a ': ' separator after the type tag (subject={self.subject!r})".format(self=self))

        if not self.description:
            issues.append("commit message's subject lacks a description after the type tag (subject={self.subject!r})".format(self=self))

        if issues:
            raise RuntimeError('\n'.join(issues))

        # 10. A footer's value MAY contain spaces and newlines, and parsing MUST terminate when the next valid footer
        #     token/separator pair is observed.
        self._footer_index = [(m.group('token'), m.start(), m.end()) for m in self.footer_re.finditer(self.message)]

    @property
    def footers(self):
        return _ConventionalFooterList(self.message, self._footer_index)

    def has_breaking_change(self):
        if self._is_breaking:
            return True

        for token, value in self.footers:
            if token == 'BREAKING CHANGE':
                return True

        return False

    def has_new_feature(self):
        return self.type_tag.lower() == 'feat'

    def has_fix(self):
        return self.type_tag.lower() == 'fix'


def parse_commit_message(message, policy=None, strict=False):
    if policy == 'conventional-commits':
        try:
            return ConventionalCommit(message)
        except RuntimeError:
            if strict:
                raise
    return CommitMessage(message)


class _IndexedList(object):
    def __init__(self, message, index, separator):
        self._message = message
        self._index = index
        self.separator = separator

    def __len__(self):
        return len(self._index) - 1

    def __getitem__(self, idx):
        if idx < 0:
            idx += len(self)
        return self._message[self._index[idx] : self._index[idx+1] - len(self.separator)]


class _FooterList(object):
    def __init__(self, message, index):
        self._message = message
        self._index = index

    def __len__(self):
        return len(self._index)

    def __getitem__(self, idx):
        if isinstance(idx, str):
            matches = [footer.value for footer in self if footer.token.casefold() == idx.casefold()]
            if not matches:
                raise KeyError(f"{idx} not found in footer list")
            return matches

        if idx < 0:
            idx += len(self)
        token, token_start, content_start = self._index[idx]
        content_end = self._index[idx+1][1] if idx + 1 < len(self) else len(self._message)
        while content_end > content_start and self._message[content_end-1] == '\n':
            content_end -= 1

        # 16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE`, when used as a token in a footer.
        if token == 'BREAKING-CHANGE':
            token = 'BREAKING CHANGE'

        return _Footer(token=token, value=self._message[content_start:content_end])

    def get(self, key : str, default=()) -> typing.Sequence:
        if not isinstance(key, str):
            raise TypeError(f"Only 'str' keys are supported, '{type(key).__name__}' passed instead")
        try:
            return self[key]
        except KeyError:
            return default


class _ConventionalFooterList(_FooterList):
    def __getitem__(self, idx):
        # 16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE`, when used as a token in a footer.
        if isinstance(idx, str):
            if idx.casefold() == 'BREAKING-CHANGE'.casefold():
                idx = 'BREAKING CHANGE'
            return super().__getitem__(idx)
        else:
            footer = super().__getitem__(idx)
            if footer.token == 'BREAKING-CHANGE':
                return _Footer('BREAKING CHANGE', footer.value)
            else:
                return footer


def _strip_message(message):
    cut_line = message.find('# ------------------------ >8 ------------------------\n')
    if cut_line >= 0 and (cut_line == 0 or message[cut_line - 1] == '\n'):
        message = message[:cut_line]

    # Strip comments
    message = re.sub(r'^#[^\n]*\n?', '', message, flags=re.MULTILINE)
    # Strip trailing whitespace from lines
    message = re.sub(r'[ \t]+$', '', message, flags=re.MULTILINE)
    # Merge consecutive empty lines into a single empty line
    message = re.sub(r'(?<=\n\n)\n+', '', message)
    # Remove empty lines from the beginning and end
    while message[:1] == '\n':
        message = message[1:]
    while message[-2:] == '\n\n':
        message = message[:-1]

    return message
