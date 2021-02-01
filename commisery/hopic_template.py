# Copyright (c) 2020 - 2020 TomTom N.V.
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
import sys
from typing import Any, List, Mapping

import hopic.build

log = logging.getLogger(__name__)


def _kebabify(name: str):
    return name.replace('_', '-')


def _kwarg_to_arg(name, value):
    if value is True:
        return [f"--{_kebabify(name)}"]
    elif value is not False and value is not None:
        return [f"--{_kebabify(name)}", str(value)]
    else:
        return []


def _kwargs_to_args(**kwargs: Mapping[str, Any]):
    for key, val in kwargs.items():
        yield from _kwarg_to_arg(key, val)


def _commisery_command(*ranges: List[str], **kwargs):
    return (sys.executable, '-m', 'commisery.checking', *_kwargs_to_args(**kwargs), '--', *ranges)


def commisery(volume_vars: Mapping[str, str], *, require_ticket: bool = False):
    hopic_git_info = hopic.build.HopicGitInfo.from_repo(volume_vars['WORKSPACE'])

    if hopic_git_info.target_commit and hopic_git_info.autosquashed_commits:
        yield {
            'image': None,
            'description': "Checking all commits provided in the Pull Request",
            'sh': _commisery_command(
                f'{hopic_git_info.target_commit}..{hopic_git_info.autosquashed_commits[0]}',
                ticket=require_ticket,
            ),
        }
    else:
        yield {
            'image': None,
            'foreach': 'AUTOSQUASHED_COMMIT',
            'sh': _commisery_command('${AUTOSQUASHED_COMMIT}'),
        }

    yield {
            'image': None,
            'description': "Checking merge commit. The subject and content of which may originate from your Pull Request's title and description",
            'sh': _commisery_command('HEAD', ticket=False),
    }
