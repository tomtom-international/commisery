# Copyright (c) 2020 - 2021 TomTom N.V.
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

import re
from typing import (
    List,
    Mapping,
    Tuple,
    Union,
)

from hopic.errors import ConfigurationError
from hopic.template.utils import module_command


def _commisery_command(*ranges: str, **kwargs):
    return module_command("commisery.checking", *ranges, **kwargs)


def commisery(
    volume_vars: Mapping[str, str],
    *,
    exclude_commits: Union[List[str], Tuple[str, ...], str] = (),
    require_ticket: bool = False,
):
    if not isinstance(exclude_commits, (list, tuple)):
        exclude_commits = (exclude_commits,)

    for idx, commit in enumerate(exclude_commits):
        if not re.match(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", commit):
            raise ConfigurationError(f"option 'commisery.exclude-commits[{idx}] is not a full SHA-1 or SHA-256 commit hash but '{commit}' instead")

    yield {
        'image': None,
        'description': "Checking all commits provided in the Pull Request",
        'sh': _commisery_command(
            '${AUTOSQUASHED_COMMITS}',
            *(f"^{commit}" for commit in exclude_commits),
            ticket=require_ticket,
        ),
    }

    yield {
            'image': None,
            'description': "Checking merge commit. The subject and content of which may originate from your Pull Request's title and description",
            'sh': _commisery_command('HEAD', ticket=False),
    }
