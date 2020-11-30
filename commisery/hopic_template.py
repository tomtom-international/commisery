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

from collections.abc import Mapping
import logging
import sys

import hopic.build

log = logging.getLogger(__name__)


def commisery(volume_vars: Mapping, *, require_ticket: bool = False):
    check_template = {
        'image': None,
        'foreach': 'AUTOSQUASHED_COMMIT',
        'sh': (sys.executable, '-m', 'commisery.checking', '${AUTOSQUASHED_COMMIT}'),
    }

    if require_ticket:
        hopic_git_info = hopic.build.HopicGitInfo.from_repo(volume_vars['WORKSPACE'])

        if hopic_git_info.target_commit:
            check_template = {
                'image': None,
                'sh': (sys.executable, '-m', 'commisery.checking', '-j', f'{hopic_git_info.target_commit}..HEAD'),
            }
        else:
            log.info('Not checking ticket presence in commit messages, since no target was prepared.')

    return [
        check_template,
        {
            'sh': (sys.executable, '-m', 'commisery.checking', 'HEAD'),
        },
    ]
