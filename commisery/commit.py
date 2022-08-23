# Copyright (c) 2018 - 2022 TomTom N.V. (https://tomtom.com)
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

import os
import re

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from commisery.config import Configuration

BREAKING_CHANGE_TOKEN = "BREAKING CHANGE"

CONVENTIONAL_COMMIT_REGEX = re.compile(
    r"""
        # 1. Commits MUST be prefixed with a type, which consists of a noun, feat, fix, etc.,
        # followed by the OPTIONAL scope, OPTIONAL !, and REQUIRED terminal colon and space.
        (?P<type>\w+)?
        # 4. A scope MAY be provided after a type. A scope MUST consist of a noun describing a
        # section of the codebase surrounded by parenthesis, e.g., fix(parser):
        (?: \( (?P<scope> [^()]* ) \) )?
        # 1. Commits MUST be prefixed with a type, which consists of a noun, feat, fix, etc.,
        # followed by the OPTIONAL scope, OPTIONAL !, and REQUIRED terminal colon and space.
        (?P<breaking_change>((\s*)+[!]+(\s*)?)?)
        # 5. A description MUST immediately follow the colon and space after the type/scope prefix.
        # The description is a short summary of the code changes, e.g., fix: array parsing issue when
        # multiple spaces were contained in string.
        (?P<separator>((\s+)?:?(\s+)?))
        # 5. A description MUST immediately follow the colon and space after the type/scope prefix.
        # The description is a short summary of the code changes, e.g., fix: array parsing issue when
        # multiple spaces were contained in string.
        (?P<description>.*)
        """,
    re.VERBOSE,
)

FOOTER_REGEX = re.compile(
    r"""
        # 8. One or more footers MAY be provided one blank line after the body. Each footer MUST consist
        # of a word token, followed by either a :<space> or <space># separator, followed by a string value
        # (this is inspired by the git trailer convention).
        #
        # 9. A footer’s token MUST use - in place of whitespace characters, e.g., Acked-by (this helps
        # differentiate the footer section from a multi-paragraph body). An exception is made for
        # BREAKING CHANGE, which MAY also be used as a token.
        ^(?P<token>[\w\- ]+|BREAKING\sCHANGE)(?::[ ]|[ ](?=[#]))(?P<value>.*)
    """,
    re.VERBOSE,
)


@dataclass
class Footer:
    """Git Trailer"""

    _token: str
    value: Sequence[str]

    def __post_init__(self):
        """Post initializer"""

        # NOTE: Required to use apply the property decorator on construction
        self.token = self._token

    @property
    def token(self):
        """Retrieve the token name"""
        return self._token

    @token.setter
    def token(self, token: str):
        """Sets the token name"""

        # 16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE`, when used as a token in a footer.
        if token == "BREAKING-CHANGE":
            token = BREAKING_CHANGE_TOKEN

        self._token = token

    def __str__(self):
        if self.value[0].startswith("#"):
            return f"{self.token} {os.linesep.join(self.value)}"

        return f"{self.token}: {os.linesep.join(self.value)}"


@dataclass
class CommitMessage:
    """Conventional Commit Message"""

    body: Sequence[str] = field(default_factory=list)
    breaking_change: Optional[str] = None
    description: Optional[str] = None
    footers: Sequence[Footer] = field(default_factory=list)
    hexsha: Optional[str] = None
    separator: Optional[str] = None
    scope: Optional[str] = None
    type: Optional[str] = None

    @property
    def subject(self):
        """Composes the subject line from the provided elements"""

        subject = self.type or ""

        if self.scope:
            subject += f"({self.scope})"

        subject += f"{self.breaking_change}{self.separator}{self.description}"

        return subject

    @property
    def squashed_subject(self):
        """(Auto-) squashed subject"""
        return strip_subject(self.subject)

    @property
    def full_subject(self):
        """To maintain backwards compatibility"""
        return self.subject

    def __str__(self):
        """Full commit message representation"""
        message = self.subject

        if len(self.body) > 0:
            message += os.linesep + os.linesep.join(self.body)

        if len(self.footers) > 0:
            message += os.linesep + os.linesep.join(
                [str(footer) for footer in self.footers]
            )

        return message

    @classmethod
    def from_message(cls: Any, message: str):
        """Converts commit message to Class object"""

        message = strip_message(message).split(os.linesep)

        subject = message[0]
        footers, body = [], []
        has_breaking_change = False

        # Retrieve subject, body and footers
        if len(message) > 1:
            end_of_body = 1
            for idx, line in enumerate(message[1:], 1):
                matches = FOOTER_REGEX.match(line)

                # Git trailer found
                if matches:
                    footers.append(
                        Footer(matches.group("token"), [matches.group("value")])
                    )
                    if footers[-1].token == BREAKING_CHANGE_TOKEN:
                        has_breaking_change = True

                # Multiline trailers use folding
                elif len(footers) > 0 and line.startswith(" "):
                    footers[-1].value.append(line)

                # Allow blank lines after BREAKING[- ]CHANGE
                elif has_breaking_change and not line:
                    # Insert empty footer items for blank lines between
                    # git trailers following BREAKING CHANGE
                    if footers[-1].token != BREAKING_CHANGE_TOKEN:
                        footers.append(Footer("", [""]))
                    continue

                # Discard detected git trailers as non-compliant item has been found
                else:
                    end_of_body = idx
                    footers = []

            # Set the body
            body = message[1:end_of_body] if end_of_body > 1 else [message[end_of_body]]

        # (OPTIONAL) Parse Conventional Commit properties
        conventional_subject = CONVENTIONAL_COMMIT_REGEX.match(strip_subject(subject))
        if not conventional_subject:
            conventional_subject = {}

        return cls(
            **conventional_subject.groupdict(),
            body=body,
            footers=footers,
        )

    def is_merge(self):
        """Return whether the commit message is a merge commit"""

        return self.type is not None and self.type.lower() == "merge"

    def has_fix(self):
        """Returns whether the commit message is a (bug) fix"""

        # 3. The type fix MUST be used when a commit represents a bug fix for your application.
        return self.type is not None and self.type.lower() == "fix"

    def has_new_feature(self):
        """Returns whether the commit contains a new feature"""

        # 2. The type feat MUST be used when a commit adds a new feature to your application
        # or library.
        return self.type is not None and self.type.lower() == "feat"

    def has_breaking_change(self):
        """Returns whether the commit contains a breaking change"""
        if self.breaking_change:
            return True

        for footer in self.footers:
            # 16. `BREAKING-CHANGE` MUST be synonymous with `BREAKING CHANGE`, when used as a token in a footer.
            if footer.token == BREAKING_CHANGE_TOKEN:
                return True

        return False


def parse_commit_message(message, policy=None, strict=False):
    """Creates a Commit Message based on the provided policy"""

    from commisery.checking import validate_commit_message

    commit_message = CommitMessage.from_message(message)

    if (
        policy == "conventional-commits"
        and strict
        and validate_commit_message(commit_message, Configuration()) > 0
    ):
        raise RuntimeError(
            "Commit message is not according to the Conventional Commit specification"
        )

    return commit_message


def strip_message(message: str):
    """Removes comments and all lines after the cut-line"""
    cut_line = message.find("# ------------------------ >8 ------------------------\n")
    if cut_line >= 0 and (cut_line == 0 or message[cut_line - 1] == "\n"):
        message = message[:cut_line]

    # Remove comments
    message = re.sub(r"^#[^\n]*\n?", "", message, flags=re.MULTILINE)

    # Remove trailing empty lines
    while message[0] == os.linesep:
        message = message[1:]

    while message[-1] == os.linesep:
        message = message[:-1]

    return message


def strip_subject(subject: str):
    """Autosquashes the commit and removes Merge statements from subject"""
    autosquash = re.compile(r"^(?:(?:fixup|squash)!\s+)+").match(subject)
    if autosquash:
        subject = subject[autosquash.end() :]

    merge = re.compile(r"^Merge.*?:[ \t]*").match(subject)
    if merge:
        subject = subject[merge.end() :]

    return subject
