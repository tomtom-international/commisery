# Copyright (c) 2020 - 2020 TomTom N.V. (https://tomtom.com)
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

try:
    # Python >= 3.8
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata


commisery_range_cli = [ep for ep in metadata.entry_points()['console_scripts'] if ep.name == 'commisery-verify-msg'][0].load()


@pytest.fixture()
def commisery_cli():
    def _cli(commit_messages, rev_range=None, with_ticket=False, with_tags=(), verbose=True):
        runner = CliRunner(mix_stderr=False)
        with runner.isolated_filesystem():
            with git.Repo.init() as repo:
                if isinstance(commit_messages, types.GeneratorType):
                    commit_messages = list(commit_messages)
                for msg in commit_messages:
                    repo.index.commit(msg, author=git.Actor('Bob', 'bob@tester.org>'))

                if rev_range is None:
                    # We'll check all messages if revision range is not provided
                    rev_range = ('HEAD',)

                assert isinstance(rev_range, collections.abc.Sequence)

                args = ['-v', 'DEBUG'] if verbose else []
                if with_ticket:
                    args.extend(('-j',))
                if with_tags:
                    args.extend(('-t', ','.join(with_tags)))
                args.extend(rev_range)

                result = runner.invoke(commisery_range_cli, args=args, color=True)

                if result.stdout_bytes:
                    print(result.stdout, end='')
                if result.stderr_bytes:
                    print(result.stderr, end='', file=sys.stderr)

                if result.exception is not None and not isinstance(result.exception, SystemExit):
                    raise result.exception

                return result

    return _cli
