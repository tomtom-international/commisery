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
import pytest

from .util import CommitAndTag

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    ("commits", "version", "exitcode"),
    (
        # Doubles for fix, feat and breaking change
        (
            (
                CommitAndTag("docs: test", "1.0.1"),
                CommitAndTag("fix: test", None),
                CommitAndTag("fix: test", None),
            ),
            "1.0.2",
            0,
        ),
        (
            (
                CommitAndTag("docs: test", "10.0.1"),
                CommitAndTag("feat: test", None),
                CommitAndTag("feat: test", None),
            ),
            "10.1.0",
            0,
        ),
        (
            (
                CommitAndTag("docs: test", "1.2.3"),
                CommitAndTag("feat!: test", None),
            ),
            "2.0.0",
            0,
        ),
        (
            (
                CommitAndTag("docs: test", "1.2.3"),
                CommitAndTag("feat: test\n\nBody\n\nBREAKING CHANGE: Test", None),
                CommitAndTag("feat!: test", None),
            ),
            "2.0.0",
            0,
        ),
        # Priority / order
        (
            (
                CommitAndTag("docs: test", "0.0.1"),
                CommitAndTag("feat: test", None),
                CommitAndTag("ci: test", None),
                CommitAndTag("fix: test", None),
            ),
            "0.1.0",
            0,
        ),
        (
            (
                CommitAndTag("docs: test", "0.0.1"),
                CommitAndTag("fix: test", None),
                CommitAndTag("ci: test", None),
            ),
            "0.0.2",
            0,
        ),
        (
            (
                CommitAndTag("docs: test", "0.0.1"),
                CommitAndTag("fix: test", None),
                CommitAndTag("ci: test", None),
                CommitAndTag("feat: test", None),
            ),
            "0.1.0",
            0,
        ),
        # No bump
        (
            (
                CommitAndTag("docs: test", "0.0.1"),
                CommitAndTag("ci: test", None),
            ),
            "",
            2,
        ),
        # No commits
        (
            (CommitAndTag("feat: test", "0.0.1"),),
            "",
            2,
        ),
        # No conventional commits
        (
            (
                CommitAndTag("initial commit", "0.0.1"),
                CommitAndTag("fix something", None),
            ),
            "",
            2,
        ),
        # Mix conventional/non-conventional
        (
            (
                CommitAndTag("initial commit", "0.0.1"),
                CommitAndTag("fix something", None),
                CommitAndTag("fix: test", None),
                CommitAndTag("fix: add missing header `banana.h`", None),
            ),
            "0.0.2",
            0,
        ),
    ),
)
def test_next_version_generic(commisery_cli, commits, version, exitcode):
    result = commisery_cli(commit_messages=commits, command="next-version", rev_range="")

    assert result.stdout.strip() == version
    assert result.exit_code == exitcode


@pytest.mark.parametrize(
    ("commits", "version", "exitcode", "target"),
    (
        (
            (
                CommitAndTag("docs: test", "1.0.1"),
                CommitAndTag("fix: test", None),
                CommitAndTag("feat: test", None),
            ),
            "1.0.2",
            0,
            ("HEAD^",),
        ),
        (
            (
                CommitAndTag("docs: test", "1.0.1"),
                CommitAndTag("fix: test", None),
                CommitAndTag("feat: test", None),
            ),
            "",
            1,
            ("HEAD^^",),
        ),
    ),
)
def test_next_version_target(commisery_cli, commits, version, exitcode, target):
    result = commisery_cli(commit_messages=commits, command="next-version", rev_range=target)
    assert result.stdout.strip() == version
    assert result.exit_code == exitcode


def test_next_version_no_commits(commisery_cli):
    result = commisery_cli(commit_messages=[], command="next-version", rev_range="")
    assert result.stdout == ""
    assert result.exit_code != 0


def test_next_version_no_tags(commisery_cli):
    result = commisery_cli(commit_messages=("test: no tags",), command="next-version", rev_range="")
    assert result.stdout == ""
    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("target", "exitcode", "log_content"),
    (
        (
            ("HEAD^3",),
            1,
            "invalid",
        ),
        (
            ("^HEAD^",),
            1,
            "empty commit list",
        ),
        (
            ("HEAD^",),
            0,
            None,
        ),
    ),
)
def test_next_version_target(commisery_cli, caplog, target, exitcode, log_content):
    result = commisery_cli(
        commit_messages=(
            CommitAndTag("docs: test", "1.0.1"),
            CommitAndTag("fix: test", None),
            CommitAndTag("feat: test", None),
        ),
        command="next-version",
        rev_range=target,
    )
    if log_content is not None:
        assert log_content in caplog.text

    assert result.exit_code == exitcode


@pytest.mark.parametrize(
    ("msg", "version", "exitcode"),
    (
        (
            "feat: add X",
            "1.1.0",
            0,
        ),
        (
            "fix: replace bad with good",
            "1.0.1",
            0,
        ),
        (
            "chore(componentA): cleanup",
            "",
            2,
        ),
    ),
)
def test_next_version_file(commisery_cli, tmp_path, msg, version, exitcode):
    tmp_file = tmp_path / "test_commit_msg"
    tmp_file.write_text(msg)

    result = commisery_cli(
        commit_messages=(CommitAndTag("docs: test", "1.0.0"),),
        command="next-version",
        rev_range=(str(tmp_file),),
    )
    assert result.stdout.strip() == version

    assert result.exit_code == exitcode
