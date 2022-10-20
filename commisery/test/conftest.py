# Copyright (c) 2020 - 2022 TomTom N.V. (https://tomtom.com)
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

import collections
import sys
import types

import git
import pytest
from click.testing import CliRunner
from .util import CommitAndTag

try:
    # Python >= 3.8
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata


_eps = metadata.entry_points().select(group="console_scripts")

commisery_range_cli = [ep for ep in _eps if ep.name == "cm"][0].load()


@pytest.fixture()
def commisery_cli():
    def _cli(
        commit_messages,
        rev_range=None,
        with_tags=(),
        verbose=True,
        command="check",
    ):
        runner = CliRunner(mix_stderr=False)
        with runner.isolated_filesystem():
            with git.Repo.init() as repo:
                if isinstance(commit_messages, types.GeneratorType):
                    commit_messages = list(commit_messages)
                for commit in commit_messages:
                    if isinstance(commit, CommitAndTag):
                        message = commit.message
                        tag = commit.tag
                    else:
                        message = commit
                        tag = None
                    with open("test_file", "a") as f:
                        f.write(".")
                    repo.index.add(("test_file",))

                    assert isinstance(message, str)
                    repo.index.commit(message, author=git.Actor("Bob", "bob@tester.org>"))

                    if tag is not None:
                        assert isinstance(tag, str)
                        repo.create_tag(path=tag, ref="HEAD")

                args = ["-v", "DEBUG"] if verbose else []
                if with_tags:
                    args.extend(("-t", ",".join(with_tags)))
                args.append(command)

                if rev_range is None:
                    # We'll check all messages if revision range is not provided by the test
                    rev_range = ("HEAD",)
                assert isinstance(rev_range, collections.abc.Sequence)

                # Empty string means default/not-defined
                if rev_range != "":
                    args.extend(rev_range)

                result = runner.invoke(commisery_range_cli, args=args, color=True)
                if result.stdout_bytes:
                    print(result.stdout, end="")
                if result.stderr_bytes:
                    print(result.stderr, end="", file=sys.stderr)

                if result.exception is not None and not isinstance(result.exception, SystemExit):
                    raise result.exception

                return result

    return _cli
