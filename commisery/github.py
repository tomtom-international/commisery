#!/usr/bin/env python3

# Copyright (c) 2022 - 2022 TomTom N.V. (https://tomtom.com)
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

import tempfile
import click
from github import Github

from commisery.config import Configuration
from commisery import checking

DEPENDABOT_USER = "dependabot[bot]"
DEPENDABOT_SUBJECT_LENGTH_OVERRIDE = 160


def check_message(message: str, config: Configuration) -> bool:
    """Validates message for compliance"""
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(message.encode("UTF-8"))
        tmp.flush()
        return checking.check_commit(tmp.name, config) == 0


@click.command()
@click.option("-t", "--token", required=True, help="GitHub Token")
@click.option("-r", "--repository", required=True, help="GitHub repository")
@click.option("-p", "--pull-request-id", required=True, help="Pull Request identifier")
def main(token: str, repository: str, pull_request_id: int) -> int:
    """GitHub Conventional Commit Message checker"""
    errors = 0

    repo = Github(token).get_repo(repository)
    pull_request = repo.get_pull(int(pull_request_id))

    config = Configuration()
    if pull_request.user.login == DEPENDABOT_USER:
        config.max_subject_length = DEPENDABOT_SUBJECT_LENGTH_OVERRIDE

    if not check_message(pull_request.title, config):
        errors += 1

    commits = pull_request.get_commits()

    for commit_info in commits:
        if not check_message(commit_info.commit.message, config):
            errors += 1

    exit(1 if errors else 0)


if __name__ == "__main__":
    main(None, None, None)
