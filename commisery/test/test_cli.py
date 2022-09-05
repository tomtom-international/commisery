# Copyrighy (c) 2020 - 2022 TomTom N.V. (https://tomtom.com)
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

import logging
from textwrap import dedent

import pytest

from commisery.config import DEFAULT_ACCEPTED_TAGS

log = logging.getLogger(__name__)


def test_cli_range_of_correct_long_commits(commisery_cli):
    long_commit_messages = tuple(
        dedent(
            f"""
            chore: write a long message for this test

            This should be a proper commit body. Nice and long, too.
            Other test cases use more terse commit messages, this one tests a long one.
            It also references UTF-8 for no apparent reason, it doesn't comply with PEP-440,
            is represented by a SHA-1 commit hash and was written on a VT-52 terminal..

            Okay, maybe not that last one, but the rest is mostly accurate.

            Implements: TICKET-{x}
            """
        )
        for x in range(0, 10)
    )

    result = commisery_cli(long_commit_messages)
    assert result.exit_code == 0

    result = commisery_cli(long_commit_messages, with_tags=("foo", "bar"))
    assert result.exit_code == 1


def test_cli_no_conventional_commit(commisery_cli):
    result = commisery_cli(("not a conventional commit message",))
    assert result.exit_code == 1

    result = commisery_cli(("fix the issue",))
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "rev_range, expected_exit_code",
    (
        (("HEAD", "^HEAD~1"), 0),
        (("HEAD~1", "^HEAD~3"), 1),
        (("HEAD~3", "^HEAD~4"), 0),
        (("HEAD~4", "^HEAD~5"), 1),
        (("HEAD~6", "HEAD~6"), 0),
    ),
)
def test_cli_rev_ranges(commisery_cli, rev_range, expected_exit_code):
    commits = (
        "fix: this is a syntactically correct commit message",
        "incorrect commit: number four",
        "incorrect commit: number three",
        "fix: this is a syntactically correct commit message",
        "incorrect commit: number two",
        "incorrect commit: number one",
        "fix: this is a syntactically correct commit message",
    )

    result = commisery_cli(commit_messages=commits, rev_range=rev_range)
    assert result.exit_code == expected_exit_code


@pytest.mark.parametrize(
    "commits, with_tags, expected_exit_code",
    (
        (("chore: correct commit", "fix: correct commit"), (), 0),
        (("mytag: correct commit", "ci: correct commit"), ("mytag", "docs"), 1),
        (("mytag: correct commit", "ci: correct commit"), ("mytag", "ci"), 0),
        (("mytag: correct commit", "mytag: another one"), ("mytag",), 0),
        (
            ("fix: this is a fix", "fox: this is a fox"),
            ("fox",),
            0,
        ),  # 'fix' and 'feat' are
        (
            ("feat: this is a feat", "foot: this is a foot"),
            ("foot",),
            0,
        ),  # always allowed
        (
            (
                "fix: yep ok",
                "notmytag: incorrect tag here",
            ),
            ("mytag",),
            1,
        ),
        (("chore: correct commit", "fix: correct commit"), ("myspecialtag",), 1),
        (("chore: correct commit", "fix: correct commit"), ("chore", "fix"), 0),
    ),
)
def test_cli_with_accepted_tags(commisery_cli, commits, with_tags, expected_exit_code):
    result = commisery_cli(
        commit_messages=commits, rev_range=("HEAD", "HEAD"), with_tags=with_tags
    )
    assert result.exit_code == expected_exit_code


@pytest.mark.parametrize("rev_range", (("HEAD",), ("HEAD", "HEAD")))
@pytest.mark.parametrize("commit", (tag for tag in DEFAULT_ACCEPTED_TAGS))
def test_cli_default_tags(commisery_cli, rev_range, commit):
    result = commisery_cli(
        commit_messages=(f"{commit}: correct commit",), rev_range=rev_range
    )
    assert result.exit_code == 0


def test_single_commit_wrong_tag(commisery_cli):
    result = commisery_cli(commit_messages=("wibble: wrong tag",), rev_range=("HEAD",))
    assert result.exit_code == 1
