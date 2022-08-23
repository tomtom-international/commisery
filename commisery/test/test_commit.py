# Copyright (c) 2019 - 2022 TomTom N.V. (https://tomtom.com)
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

from commisery.checking import validate_commit_message
from commisery.config import Configuration
import pytest
from ..commit import CommitMessage, Footer


def test_basic_message_strip_and_splitup():
    """
    This tests these bits of functionality:

      * white space and comment stripping similar to how git-commit does it
      * line splitting
      * subject extraction
      * paragraph splitting
      * body extraction
    """
    message = CommitMessage.from_message(
        """\

# test stripping of comments and preceding empty lines

improvement(config): display config error messages without backtrace

In order to prevent users from thinking they're seeing a bug in Hopic.


This changes the type of ConfigurationError such that Click will display
its message without a backtrace. This ensures the displayed information
is more to the point.

# ------------------------ >8 ------------------------

This line and every other line after the 'cut' line above should not be present
in the output.

# test stripping of comments and succeeding empty lines

"""
    )
    assert (
        message.subject
        == """improvement(config): display config error messages without backtrace"""
    )

    assert (
        message.body[1]
        == """In order to prevent users from thinking they're seeing a bug in Hopic."""
    )


def test_conventional_scoped_improvement():
    message = CommitMessage.from_message(
        "improvement(config): display config error messages without backtrace"
    )

    assert message.type == "improvement"
    assert message.scope == "config"
    assert message.description == "display config error messages without backtrace"
    assert not message.has_breaking_change()
    assert not message.has_new_feature()
    assert not message.has_fix()


def test_conventional_scope_with_space():
    CommitMessage.from_message("docs(git tips): improve documentation on amending")


def test_conventional_fix():
    message = CommitMessage.from_message(
        "fix: use the common ancestor of the source and target commit for autosquash"
    )
    assert message.type == "fix"
    assert message.scope is None
    assert not message.has_breaking_change()
    assert not message.has_new_feature()
    assert message.has_fix()


def test_conventional_new_feature():
    message = CommitMessage.from_message(
        """feat: make execution possible with 'hopic' as command"""
    )
    assert message.type == "feat"
    assert message.scope is None
    assert not message.has_breaking_change()
    assert message.has_new_feature()
    assert not message.has_fix()


def test_conventional_break():
    message = CommitMessage.from_message(
        """\
chore: cleanup old cfg.yml default config file name

BREAKING-CHANGE: "${WORKSPACE}/cfg.yml" is no longer the default location
  of the config file. Instead only "${WORKSPACE}/hopic-ci-config.yaml" is
  looked at.
"""
    )
    assert message.type == "chore"
    assert message.scope is None
    assert message.has_breaking_change()
    assert not message.has_new_feature()
    assert not message.has_fix()

    assert "BREAKING CHANGE" in [footer.token for footer in message.footers]


def test_conventional_subject_break():
    message = CommitMessage.from_message(
        """chore!: delete deprecated 'ci-driver' command"""
    )
    assert message.type == "chore"
    assert message.scope is None
    assert message.has_breaking_change()
    assert not message.has_new_feature()
    assert not message.has_fix()


def test_conventional_subject_breaking_fix():
    message = CommitMessage.from_message(
        """fix!: take parameter as unsigned instead of signed int"""
    )
    assert message.type == "fix"
    assert message.scope is None
    assert message.has_breaking_change()
    assert not message.has_new_feature()
    assert message.has_fix()


def test_conventional_subject_breaking_new_feature():
    message = CommitMessage.from_message(
        """feat!: support multiple non-global current working directories"""
    )
    assert message.type == "feat"
    assert message.scope is None
    assert message.has_breaking_change()
    assert message.has_new_feature()
    assert not message.has_fix()


def test_conventional_fixup_fix():
    message = CommitMessage.from_message(
        "fixup! fix: only restore mtime for regular files and symlinks"
    )
    assert message.type == "fix"
    assert message.scope is None
    assert message.description == "only restore mtime for regular files and symlinks"
    assert not message.has_breaking_change()
    assert not message.has_new_feature()
    assert message.has_fix()


def test_basic_footers():
    message = CommitMessage.from_message(
        """\
Merge #63: something

Bla bla

BREAKING CHANGE: something changed in an unpredicted way

Addresses #42 by working on finding the question
Implements: PIPE-123 through the obliviator
Acked-by: Alice <alice@example.com>
Merged-by: Hopic 1.21.2
Acked-by: Bob <bob@example.com>
"""
    )

    assert message.footers == [
        Footer("BREAKING CHANGE", ["something changed in an unpredicted way"]),
        Footer("Addresses", ["#42 by working on finding the question"]),
        Footer("Implements", ["PIPE-123 through the obliviator"]),
        Footer("Acked-by", ["Alice <alice@example.com>"]),
        Footer("Merged-by", ["Hopic 1.21.2"]),
        Footer("Acked-by", ["Bob <bob@example.com>"]),
    ]


def test_conventional_footers():
    message = CommitMessage.from_message(
        """\
Merge #63: improvement(groovy): retrieve execution graph in a single 'getinfo' call

This should reduce the amount of Jenkins master/slave interactions and
their associated Groovy script engine "context switches" (state
serialization and restoration). As a result performance should increase.

vv The next two trailers will be rejected as there is a blank line inbetween vv
Addresses #279 by adding a test framework.
Addresses #301 due to the performance improvements
 made to the scripting engine

Addresses #167 by updating testing framework dependencies
 and validating behavior
Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
Acked-by: Joost Muller <Joost.Muller@tomtom.com>
Acked-by: Martijn Leijssen <Martijn.Leijssen@tomtom.com>
Acked-by: Rene Kempen <Rene.Kempen@tomtom.com>
Merged-by: Hopic 0.10.2.dev7+g840ca0c
"""
    )
    assert message.type == "improvement"
    assert message.scope == "groovy"

    # NOTE: Unfortunately we cannot make a correct judgement for the
    #       rejected git-trailers, for now we will ignore them and
    #       they will be considered to be part of the body of the
    #       commit message.

    assert message.footers == [
        Footer(
            "Addresses",
            [
                "#167 by updating testing framework dependencies",
                " and validating behavior",
            ],
        ),
        Footer("Acked-by", ["Anton Indrawan <Anton.Indrawan@tomtom.com>"]),
        Footer("Acked-by", ["Joost Muller <Joost.Muller@tomtom.com>"]),
        Footer("Acked-by", ["Martijn Leijssen <Martijn.Leijssen@tomtom.com>"]),
        Footer("Acked-by", ["Rene Kempen <Rene.Kempen@tomtom.com>"]),
        Footer("Merged-by", ["Hopic 0.10.2.dev7+g840ca0c"]),
    ]


@pytest.mark.parametrize(
    "msg",
    (
        "Merge branch 'main' into my-great-branch",
        "Merge branch 'main' into 'my-great-branch'",
        "Merge branch main into my-great-branch",
        "Merge branch main into 'my-great-branch'",
        "Merge branch main",
    ),
)
def test_merge_commit(msg):
    assert CommitMessage.from_message(msg).is_merge()

@pytest.mark.parametrize(
    "msg, expectation",
    (
        ("feat: execute inside docker container if requested", "feat"),
        ("feat execute inside docker container if requested", "feat"),
        ("[feat]: execute inside docker container if requested", None),
        ("[feat] execute inside docker container if requested", None),
        ("[NAV-1234] execute inside docker container if requested", None),
    ),
)
def test_commit_types(msg, expectation):
    assert CommitMessage.from_message(msg).type == expectation
