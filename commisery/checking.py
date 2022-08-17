#!/usr/bin/env python3

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

# This is a simplistic implementation of checking adherance to Conventional Commits https://www.conventionalcommits.org/

import re
import subprocess

from commisery.config import Configuration
from commisery.commit import CommitMessage
from commisery.rules import validate_commit_message_rule


def check_commit(commit, config: Configuration):
    """Validates provided commit message against specification"""
    try:
        if re.match(r"^[0-9a-fA-F]{40}$", str(commit)):
            raise IOError("a full commit hash should never be treated as a file")

        with open(commit, encoding="UTF-8") as file:
            message = file.read()

    except IOError:
        commit = subprocess.check_output(("git", "rev-parse", commit))[:-1].decode(
            "UTF-8"
        )
        message = subprocess.check_output(
            ("git", "show", "-q", "--format=%B", commit, "--")
        )[:-1].decode("UTF-8")

    commit_message = CommitMessage.from_message(message)
    commit_message.hexsha = commit

    return validate_commit_message(commit_message, config)


def validate_commit_message(message: CommitMessage, config: Configuration):
    """Validates the provided commit message against specification"""
    error_count = 0
    for rule in config.rules:
        error_count += validate_commit_message_rule(
            rule=rule, message=message, config=config
        )

    return 1 if error_count > 0 else 0
