#!/usr/bin/env python3

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

import logging

import git

from commisery.checking import (
    check_commit,
    count_ticket_refs,
)


log = logging.getLogger(__name__)


def check_commit_rev_range(revision_range, custom_accepted_tags=None, require_ticket=False):
    """
    Checks commit messages of the commits in the provided revision range.

    Parameters:
        revision_range: a sequence of `git rev-list`-compatible arguments describing a revision range
        custom_accepted_tags: an optional list of conventional commit tags to allow besides 'feat' and 'fix'
        require_ticket: when set to true, requires a Jira-style ticket to be present anywhere in the commit message
                in one of the commits described by revision_range

    Returns:
        1 on failure, 0 on success.
    """
    log.debug('Revision range: %s', ' '.join(revision_range))
    if custom_accepted_tags:
        log.debug('Custom accepted tags: %s', ' '.join(custom_accepted_tags))

    try:
        with git.Repo(search_parent_directories=True) as repo:
            try:
                commits = list(repo.iter_commits(rev=revision_range))
            except git.GitCommandError:
                log.exception('Error getting list of commits from revision range: %s', ' '.join(revision_range))
                return 1

            log.debug('Repo at %s has %d commits for range: %s',
                      repo.working_dir, len(commits),  ' '.join(revision_range))
            ticket_count = 0
            error_count = 0

            for commit in commits:
                log.debug('Checking commit: %s', commit.hexsha)
                error_count += check_commit(commit.hexsha, custom_accepted_tags=custom_accepted_tags)
                if require_ticket:
                    ticket_count += count_ticket_refs(commit.message)

            log.debug('Done checking commits{}{}'.format(
                f', {error_count} error{"s" if error_count > 1 else ""} found' if error_count else '',
                f', ticket reference count: {ticket_count}' if require_ticket else ''))

            if require_ticket and ticket_count == 0:
                log.error('No ticket is referenced within the provided range of commits')
                error_count += 1

            if error_count == 0:
                return 0

    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        log.error('Not a git repository')

    return 1
