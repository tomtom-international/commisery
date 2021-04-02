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

from typing import Mapping

from hopic.template.utils import module_command


def _commisery_command(*ranges: str, **kwargs):
    return module_command("commisery.checking", *ranges, **kwargs)


def commisery(volume_vars: Mapping[str, str], *, require_ticket: bool = False):
    yield {
        'image': None,
        'description': "Checking all commits provided in the Pull Request",
        'sh': _commisery_command(
            '${AUTOSQUASHED_COMMITS}',
            ticket=require_ticket,
        ),
    }

    yield {
            'image': None,
            'description': "Checking merge commit. The subject and content of which may originate from your Pull Request's title and description",
            'sh': _commisery_command('HEAD', ticket=False),
    }
