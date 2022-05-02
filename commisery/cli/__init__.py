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

import itertools
import logging
import os
import re
import subprocess
import sys

import click
import click_log

from commisery.checking import (
    check_commit,
    DEFAULT_ACCEPTED_TAGS,
)
from commisery.range import check_commit_rev_range


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
log.addHandler(logging.NullHandler())


@click.command()
@click.argument('target', nargs=-1)
@click.option('--ticket', '-j',
              default=None,
              is_flag=True,
              help='When provided, the commit messages in the provided revision range '
                   + 'must contain at least one ticket reference, in the form of regex:\n'
                   + '\\b[A-Z]+-[0-9]+\\b'
              )
@click.option('--tags', '-t',
              multiple=True,
              help='Comma-separated list of accepted conventional commit tags to allow '
                   + 'aside from the default "feat" and "fix".\n'
                   + f'If omitted, uses the following list:\n{", ".join(DEFAULT_ACCEPTED_TAGS)}'
              )
@click_log.simple_verbosity_option(__package__.split('.')[0])
def main(target, tags, ticket):
    """
    Checks whether commit messages adhere to the Convention Commits standard.

    \b
    TARGET can be:
     - a single commit hash
     - a file containing the commit message to check
     - a revision range that `git rev-list` can interpret
    When TARGET is omitted, 'HEAD' is implied.

    Optional parameters may be provided to specify which tags are allowed
    and/or whether the commits in the revision range should contain a ticket reference.
    """

    custom_accepted_tags = None if not tags else (frozenset(itertools.chain.from_iterable(x.split(',') for x in tags)))
    target = target or ('HEAD',)
    target_str = ' '.join(target)

    # We will treat the input as a revision range if:
    # the target is not a full SHA-1 hash (i.e. 40 hex digits) and does not represent an existing file
    # and the result of a `git rev-parse <target>` yields more than one line
    try:
        if not re.match(r'^[0-9a-fA-F]{40}$', target_str) and \
           not os.path.exists(target_str) and \
           len(subprocess.check_output(('git', 'rev-parse') + target,
                                       stderr=subprocess.DEVNULL).decode(encoding='UTF-8').splitlines()) > 1:
            log.debug(f'Handling as range: {target_str}')
            result = check_commit_rev_range(target, custom_accepted_tags=custom_accepted_tags, require_ticket=ticket)
        else:
            log.debug(f'Handling as commitish: {target_str}')
            result = check_commit(target_str, custom_accepted_tags=custom_accepted_tags, require_ticket=ticket)
    except subprocess.CalledProcessError:
        result = 1
        log.error('Could not parse target revision spec %s', target_str)

    sys.exit(result)


if __name__ == '__main__':
    sys.exit(main())
