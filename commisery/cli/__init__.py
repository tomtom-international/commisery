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
import os
import re
import subprocess
import sys

import click
import click_log
from git import Repo

from commisery.checking import (
    check_commit,
    validate_commit_message,
)
from commisery.cli import inquirer
from commisery.commit import CommitMessage
from commisery.config import DEFAULT_ACCEPTED_TAGS, Configuration, get_default_rules
from commisery.range import check_commit_rev_range


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
        config.tags = {
            key: "No description available (provided by CLI)" for key in tags.split(",")
        }

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
        "[\033[92mo\033[0m]: \033[90mrule is enabled\033[0m, [\033[91mx\033[0m]: \033[90mrule has been disabled\033[0m"
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
    type=click.Choice(DEFAULT_ACCEPTED_TAGS),
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
            tag_choices = [
                f"{tag}: {description}" for tag, description in config.tags.items()
            ]

            questions.append(
                inquirer.Choice(
                    name="type",
                    message="Select the (conventional commit) type of your change",
                    choices=tag_choices,
                    default=f"fix: {config.tags['fix']}",
                )
            )

        if not scope:
            questions.append(
                inquirer.Input(name="scope", message="Specify the scope (Optional)")
            )

        if not description:
            questions.append(
                inquirer.Input(
                    name="description", message="Specify the subject of the commit"
                )
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

        answers["scope"] = answers.get("scope") if answers.get("scope") else None
        answers["type"] = answers.get("type").split(":")[0]
        answers["breaking_change"] = "!" if answers.get("breaking_change", "No") == "Yes" else ""
        _body = answers.get("body", None)
        if _body:
            answers["body"] = (os.linesep + answers.get("body")).split(os.linesep)

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
                subprocess.check_output(
                    ("git", "rev-parse") + target, stderr=subprocess.DEVNULL
                )
                .decode(encoding="UTF-8")
                .splitlines()
            )
            > 1
        ):
            log.debug(f"Handling as range: {target_str}")
            result = check_commit_rev_range(target, config=config)
        else:
            log.debug(f"Handling as commitish: {target_str}")
            result = check_commit(target_str, config=config)
    except subprocess.CalledProcessError:
        result = 1
        log.error("Could not parse target revision spec %s", target_str)

    sys.exit(result)


if __name__ == "__main__":
    sys.exit(main())
