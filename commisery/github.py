#!/usr/bin/env python3

# Copyright (C) 2020-2020, TomTom (http://tomtom.com).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import click
import tempfile

from github import Github
from . import checking


def check_message(message: str) -> bool:
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(message.encode('UTF-8'))
        tmp.flush()

        return checking.check_commit(tmp.name) == 0


@click.command()
@click.option('-t', '--token',
              required=True, help='GitHub Token')
@click.option('-r', '--repository',
              required=True,  help='GitHub repository')
@click.option('-p', '--pull-request-id',
              required=True, help='Pull Request identifier')
def main(token: str, repository: str, pull_request_id: int) -> int:
    errors = 0

    repo = Github(token).get_repo(repository)
    pr = repo.get_pull(int(pull_request_id))

    if not check_message(pr.title):
        errors += 1

    commits = pr.get_commits()

    for commit_info in commits:
        if not check_message(commit_info.commit.message):
            errors += 1

    exit(1 if errors else 0)


if __name__ == '__main__':
    main()
