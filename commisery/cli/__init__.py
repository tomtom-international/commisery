#!/usr/bin/env python3

# Copyright (c) 2020 - 2022 TomTom N.V. (https://tomtom.com)
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
import math
import os
import re
import subprocess
import sys

import click
import click_log
from git import Repo, GitCommandError, InvalidGitRepositoryError

from commisery.checking import (
    check_commit,
    validate_commit_message,
)
from commisery.cli import inquirer
from commisery.commit import parse_commit_message
from commisery.config import DEFAULT_ACCEPTED_TAGS, Configuration, get_default_rules
from commisery.range import check_commit_rev_range
from commisery.versioning import GitVersion

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
log.addHandler(logging.NullHandler())


@click.group()
@click.option("--config", "-c", help="Path towards a configuration file")
@click.option(
    "--tags",
    "-t",
    help="Comma-separated list of accepted conventional commit tags to allow "
    + 'aside from the default "feat" and "fix".\n'
    + f'If omitted, uses the following list:\n{", ".join(DEFAULT_ACCEPTED_TAGS)}',
)
@click.option(
    "--max-subject-length",
    "-l",
    type=click.INT,
    help="Maximum characters allowed in the subject of the commit message",
)
@click.option(
    "--disable",
    "-d",
    multiple=True,
    help="List of commit message rules to disable.\n"
    + f"Can be one of:\n{', '.join(get_default_rules().keys())}",
)
@click_log.simple_verbosity_option(__package__.split(".", maxsplit=1)[0])
@click.pass_context
def main(ctx, config, tags, max_subject_length, disable):
    """
    Manages conventional commit messages
    """

    ctx.ensure_object(dict)
    config = Configuration.from_yaml(config)
    if tags:
        config.tags = {key: "No description available (provided by CLI)" for key in tags.split(",")}

    if max_subject_length:
        config.max_subject_length = max_subject_length

    if disable:
        for item in disable:
            config.rules[item]["enabled"] = False

    ctx.obj["CONFIG"] = config


@main.command()
@click.pass_context
def overview(ctx):
    """Lists the accepted Conventional Commit tags and Rules (including description)"""
    ctx.ensure_object(dict)
    config = ctx.obj["CONFIG"]

    print()
    print("Conventional Commit tags")
    print("------------------------")
    for tag, description in config.tags.items():
        print(f"{tag}: \033[90m{description}\033[0m")
    print()

    print("Commisery Validation rules")
    print("--------------------------")
    print(
        "[\033[92mo\033[0m]: \033[90mrule is enabled\033[0m, [\033[91mx\033[0m]: \033[90mrule has been disabled\033[0m"  # pylint: disable=line-too-long
    )
    print()
    for rule, value in config.rules.items():
        status = "\033[92mo\033[0m" if value.get("enabled") else "\033[91mx\033[0m"
        print(f"[{status}] {rule}: \033[90m{value.get('description')}\033[0m")
    print()


@main.command()
@click.option(
    "-t",
    "--type",
    type=click.Choice(tuple(DEFAULT_ACCEPTED_TAGS.keys())),
    help="Conventional Commit type",
)
@click.option("-s", "--scope", help="Conventional commit scope")
@click.option("-d", "--description", help="Commit description")
@click.option("-b", "--breaking-change", is_flag=True, help="This is a breaking change")
@click.pass_context
def commit(ctx, type, scope, description, breaking_change):
    """Creates a conventional commit"""
    ctx.ensure_object(dict)
    config = ctx.obj["CONFIG"]

    def _read_commit_message():
        questions = []

        if not type:
            tag_choices = [f"{tag}: {description}" for tag, description in config.tags.items()]

            questions.append(
                inquirer.Choice(
                    name="type",
                    message="Select the (conventional commit) type of your change",
                    choices=tag_choices,
                    default=f"fix: {config.tags['fix']}",
                )
            )

        if not scope:
            questions.append(inquirer.Input(name="scope", message="Specify the scope (Optional)"))

        if not description:
            questions.append(
                inquirer.Input(name="description", message="Specify the subject of the commit")
            )

        questions.append(
            inquirer.Editor(
                name="body",
                message="Describe the commit in more details (ESC+ENTER to quit)",
            )
        )

        if not breaking_change:
            questions.append(
                inquirer.Choice(
                    name="breaking_change",
                    message="Is this a change breaking the API",
                    choices=["Yes", "No"],
                    default="No",
                )
            )

        answers = inquirer.prompt(questions)

        answers["scope"] = answers.get("scope") if answers.get("scope", None) else None
        answers["type"] = answers.get("type").split(":")[0]
        answers["breaking_change"] = "!" if answers.get("breaking_change", "No") == "Yes" else ""

        if answers.get("body"):
            answers["body"] = ("\n" + answers.get("body")).splitlines()

        return CommitMessage(**answers, separator=": ")

    confirmation = False
    while not confirmation:
        commit_message = _read_commit_message()

        confirmation = inquirer.prompt(
            [
                inquirer.Confirm(
                    name="confirmation",
                    message=f"""\
Commit message:

---
{commit_message}
---

Is this correct?""",
                    default=True,
                )
            ]
        ).get("confirmation")

    print(os.linesep)

    if validate_commit_message(commit_message, config) == 0:
        repo = Repo(os.getcwd(), search_parent_directories=True)
        repo.index.commit(message=str(commit_message))


@main.command()
@click.argument("target", nargs=-1)
@click.pass_context
def check(ctx, target):
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

    ctx.ensure_object(dict)
    config = ctx.obj.get("CONFIG", Configuration())

    target = target or ("HEAD",)
    target_str = " ".join(target)

    try:
        if (
            not re.match(r"^[0-9a-fA-F]{40}$", target_str)
            and not os.path.exists(target_str)
            and len(
                subprocess.check_output(("git", "rev-parse") + target, stderr=subprocess.DEVNULL)
                .decode(encoding="UTF-8")
                .splitlines()
            )
            > 1
        ):
            log.debug(f"Handling as range: %s", target_str)
            result = check_commit_rev_range(target, config=config)
        else:
            log.debug(f"Handling as commitish: %s", target_str)
            result = check_commit(target_str, config=config)
    except subprocess.CalledProcessError:
        result = 1
        log.error("Could not parse target revision spec %s", target_str)

    sys.exit(result)


@main.command()
@click.argument("target", default="")
@click.pass_context
def next_version(ctx, target):
    """
    Provides the next version based on Conventional Commit messages since the
    last tag.
    Accepts tags with prefix, (eg. "v0.1.2",) but returns _only_ the semantic
    version after bumping (eg. "0.1.3").

    TARGET can optionally be provided to override the "to"-revision.
    If TARGET can be parsed as a file, its contents shall be interpreted as a
    single commit.
    In all other cases, TARGET can be used to exclude some commits from the
    revision range since the last tag. For example, specifying "HEAD~" will
    run the logic excluding the HEAD commit.\n
    If not provided, TARGET will default to "HEAD".

    \b
    The list of commits this function will consider is identical to:
        git rev-list ^LAST_TAG TARGET
    where LAST_TAG is the latest topological tag in the current branch.

    \b
    Prints the version on a successful bump, otherwise:
      - exits with 2 if the commits version is not bumped
      - exits with 1 on any trouble (no version tag found, invalid input, etc.)
    """
    config = ctx.obj["CONFIG"]
    valid_repo = False
    try:
        repo = Repo(search_parent_directories=True)
        if repo.active_branch.is_valid():
            valid_repo = True
    except InvalidGitRepositoryError:
        pass
    except TypeError:
        log.error("Could not resolve HEAD; is HEAD detached?")
        ctx.exit(1)

    if not valid_repo:
        log.error(f"Current directory ({os.getcwd()}) is not in a (valid) Git repository")
        ctx.exit(1)

    # Repeatability caveat: the length of the describe abbrev is by
    # default dependent on the amount of Git objects in a repo.
    #   length = int((log2(git_objects) + 1) / 2)
    # For the sake of repeatability, we choose a very large number.
    _max_git_objects = 100e6
    _git_abbrev_len = math.ceil(math.log2(_max_git_objects) / 2)
    try:
        version = GitVersion.from_description(
            repo.git.describe(
                tags=True,
                long=True,
                dirty=True,
                always=True,
                abbrev=_git_abbrev_len,
            ),
        )
    except GitCommandError:
        log.error("Error during `git describe`; ensure the branch's last tag is a SemVer")
        ctx.exit(1)

    current_version = version.to_version(format="semver")

    if target and os.path.exists(target):
        with open(target, "r") as file:
            commits = (file.read(),)
    elif version.exact or current_version is None:
        # We're either on the latest tag or the current latest tag is not parseable
        log.info("Nothing to bump")
        ctx.exit(2)
    elif target:
        try:
            commits = tuple(repo.iter_commits(rev=target))
        except GitCommandError:
            log.error(f"Provided target '{target}' is invalid")
            ctx.exit(1)
    else:
        current_tag = repo.git.describe(tags=True, abbrev=0)
        commits = tuple(repo.iter_commits(rev=(f"^{current_tag}", "HEAD")))

    if len(tuple(commits)) == 0:
        if target:
            if os.path.exists(target):
                log.error("The file '%s' is empty" % target)
            else:
                log.error("The revision range '%s' resulted in an empty commit list" % target)
        else:
            log.error("No commits found")
        ctx.exit(1)

    # We only want to get a list of correct conventional commits to consider; disable error output
    config.silent = True

    log.debug("Yielding " + str(commits))
    def _check_commits(commits):
        for commit in commits:
            msg = parse_commit_message(commit if isinstance(commit, str) else commit.message)
            if validate_commit_message(msg, config) == 0:
                yield msg

    new_version = current_version.next_version_for_commits(_check_commits(commits))
    if new_version > current_version:
        print(new_version)
        ctx.exit(0)

    log.info(f"Not bumping from {current_version}")
    ctx.exit(2)


if __name__ == "__main__":
    sys.exit(main())
