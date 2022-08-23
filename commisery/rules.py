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

import difflib
import os
import re

import llvm_diagnostics as logging

from commisery.commit import BREAKING_CHANGE_TOKEN, CommitMessage
from commisery.config import Configuration, get_default_rules


def C001_non_lower_case_type(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """The commit message's tag type should be in lower case"""
    # No need to verify merge commits
    if message.is_merge():
        return

    try:
        # No need to verify tag in case it is missing
        C012_missing_type_tag(message, config)
    except logging.Error:
        return

    if not message.type.islower():
        raise logging.Error(
            message=C001_non_lower_case_type.__doc__,
            line=message.subject,
            column_number=logging.Range(
                message.subject.find(message.type) + 1, len(message.type)
            ),
            expectations=message.type.lower(),
        )


def C002_one_whiteline_between_subject_and_body(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """Only one empty line between subject and body"""
    if not message.body or message.is_merge():
        return

    if len(message.body) >= 2 and message.body[1].strip() == "":
        raise logging.Error(
            message=C002_one_whiteline_between_subject_and_body.__doc__,
            line=os.linesep.join(message.body),
            column_number=logging.Range(0, len(message.body[-1])),
        )


def C003_title_case_description(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """The commit message's description should not start with a capital case letter"""
    # No need to verify merge commits
    if message.is_merge():
        return

    try:
        # No need to run this rule in case the description is not present
        C009_missing_description(message, config)
    except logging.Error:
        return

    first_word = message.description[0]
    if not first_word.islower():
        raise logging.Error(
            message=C003_title_case_description.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find(message.description) + 1,
                range=len(message.description),
            ),
            expectations=first_word.lower() + message.description[1:],
        )


def C004_unknown_tag_type(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """Commit message's subject should not contain an unknown tag type"""
    # No need to verify merge commits
    if message.is_merge():
        return

    try:
        # No need to verify tag in case it is missing
        C012_missing_type_tag(message, config)
    except logging.Error:
        return

    if message.type not in config.tags:
        closest_match = difflib.get_close_matches(
            message.type.lower(), config.tags, n=1
        )
        closest_match = (
            closest_match[0] if closest_match else f"{', '.join(config.tags)}"
        )

        raise logging.Error(
            message=f"{C004_unknown_tag_type.__doc__}. Use one of: feat, fix, {', '.join(config.tags)}",
            line=message.subject,
            column_number=logging.Range(
                message.subject.find(message.type) + 1, len(message.type)
            ),
            expectations=closest_match,
        )


def C005_separator_contains_trailing_whitespaces(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """Only one whitespace allowed after the ":" separator"""
    # No need to verify merge commits
    if message.is_merge():
        return

    try:
        # No need to verify for whitespacing when the separator is missing
        C008_missing_separator(message, config)
    except logging.Error:
        return

    if message.separator != ": ":
        raise logging.Error(
            message=C005_separator_contains_trailing_whitespaces.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=len(message.subject)
                - len(message.squashed_subject)
                + message.squashed_subject.find(message.separator)
                + 1,
                range=len(message.separator) + len(message.description),
            ),
            expectations=f": {message.description}",
        )


def C006_scope_should_not_be_empty(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message's scope should not be empty"""
    # NOTE: the scope is OPTIONAL
    if message.scope is None:
        return

    if not message.scope:
        raise logging.Error(
            message=C006_scope_should_not_be_empty.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find("(") + 1, range=len(message.scope) + 2
            ),
        )


def C007_scope_contains_whitespace(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """The commit message's scope should not contain any whitespacing"""
    # NOTE: the scope is OPTIONAL
    if message.scope is None:
        return

    try:
        C006_scope_should_not_be_empty(message, config)
    except logging.Error:
        return

    if len(message.scope) != len(message.scope.strip()):
        raise logging.Error(
            message=C007_scope_contains_whitespace.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find("(") + 2, range=len(message.scope)
            ),
            expectations=message.scope.strip(),
        )


def C008_missing_separator(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message's subject requires a separator (": ") after the type tag"""
    # No need to verify merge commits
    if message.is_merge():
        return

    if ":" not in message.separator:
        raise logging.Error(
            message=C008_missing_separator.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find(message.description)
                - len(message.separator)
                + 1,
                range=len(message.description) + len(message.separator),
            ),
            expectations=f": {message.description}",
        )


def C009_missing_description(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message requires a description"""

    if not message.description:
        raise logging.Error(
            message=C009_missing_description.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=len(message.subject) + 1,
            ),
        )


def C010_breaking_indicator_contains_whitespacing(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """No whitespace allowed around the "!" indicator"""
    if not message.breaking_change:
        return

    if message.breaking_change.strip() is not message.breaking_change:
        raise logging.Error(
            message=C010_breaking_indicator_contains_whitespacing.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=len(message.subject)
                - len(message.squashed_subject)
                + message.squashed_subject.find(message.breaking_change)
                + 1,
                range=len(message.breaking_change),
            ),
            expectations=f"!{message.separator}{message.description}",
        )


def C011_only_single_breaking_indicator(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """Breaking separator should consist of only one indicator"""

    # NOTE: the breaking indicator is OPTIONAL
    if not message.breaking_change:
        return

    if len(message.breaking_change.strip()) > 1:
        raise logging.Error(
            message=C011_only_single_breaking_indicator.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=len(message.subject)
                - len(message.squashed_subject)
                + message.squashed_subject.find("!")
                + 1,
                range=len(message.breaking_change.strip()),
            ),
            expectations="!",
        )


def C012_missing_type_tag(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message's subject requires a type"""

    if not message.type:
        raise logging.Error(
            message=C012_missing_type_tag.__doc__,
            line=message.subject,
        )


def C013_subject_should_not_end_with_punctuation(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message's subject should not end with punctuation"""
    # No need to verify merge commits
    if message.is_merge():
        return

    if re.match(r".*[.!?,]$", message.description):
        raise logging.Error(
            message=C013_subject_should_not_end_with_punctuation.__doc__,
            line=message.subject,
            column_number=logging.Range(start=len(message.subject)),
        )


def C014_subject_exceeds_line_lenght_limit(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """The commit message's subject should be within the line length limit"""
    # No need to verify merge commits
    if message.is_merge():
        return

    if len(message.subject) > config.max_subject_length:
        raise logging.Error(
            message=f"{C014_subject_exceeds_line_lenght_limit.__doc__} ({config.max_subject_length}), exceeded by {len(message.subject) - config.max_subject_length + 1} characters",
            line=message.subject,
            column_number=logging.Range(
                start=config.max_subject_length,
                range=len(message.subject) - config.max_subject_length + 1,
            ),
        )


def C015_no_repeated_tags(
    message: CommitMessage, config: Configuration
):  # pylint: disable=C0103
    """Description should not start with a repetition of the tag"""

    try:
        # No need to verify repeated tags if the tag and description are missing
        C012_missing_type_tag(message, config)
        C009_missing_description(message, config)
    except logging.Error:
        return

    if message.description.lower().startswith(message.type.lower()):
        raise logging.Error(
            message=C015_no_repeated_tags.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find(message.description) + 1,
                range=len(message.type),
            ),
        )


def C016_description_in_imperative_mood(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message's description should be written in imperative mood"""

    common_non_imperative_verbs = (
        "added",
        "adds",
        "adding",
        "applied",
        "applies",
        "applying",
        "edited",
        "edits",
        "editing",
        "expanded",
        "expands",
        "expanding",
        "fixed",
        "fixes",
        "fixing",
        "removed",
        "removes",
        "removing",
        "renamed",
        "renames",
        "renaming",
        "deleted",
        "deletes",
        "deleting",
        "updated",
        "updates",
        "updating",
        "ensured",
        "ensures",
        "ensuring",
        "resolved",
        "resolves",
        "resolving",
        "verified",
        "verifies",
        "verifying",
    )
    blacklist = re.compile(
        "|".join(re.escape(w) for w in common_non_imperative_verbs), re.IGNORECASE
    )
    blacklisted_verbs = blacklist.match(message.description)

    if blacklisted_verbs:
        raise logging.Error(
            message=C016_description_in_imperative_mood.__doc__,
            line=message.subject,
            column_number=logging.Range(
                start=message.subject.find(message.description) + 1,
                range=len(message.description.split(" ")[0]),
            ),
        )


def C017_subject_contains_review_remarks(
    _: CommitMessage, __: Configuration
):  # pylint: disable=C0103
    """Subject should not contain reference to review comments"""
    # TODO: implement this rule


def C018_missing_empty_line_between_subject_and_body(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The commit message should contain an empty line between subject and body"""

    # NOTE: the body is OPTIONAL
    if not message.body:
        return

    if message.body[0]:
        raise logging.Error(
            message=C018_missing_empty_line_between_subject_and_body.__doc__,
        )


def C019_subject_contains_issue_reference(
    message: CommitMessage, _: Configuration
):  # pylint:  disable=C0103
    """The commit message's subject should not contain a ticket reference"""
    # No need to verify merge commits
    if message.is_merge():
        return

    issue_regex = re.compile(
        r"\b(?!"
        + "|".join(
            re.escape(i + "-")
            for i in (
                "AES",  # AES-128
                "PEP",  # PEP-440
                "SHA",  # SHA-256
                "UTF",  # UTF-8
                "VT",  # VT-220
            )
        )
        + r")[A-Z]+-[0-9]+\b"
    )
    issues = issue_regex.findall(message.subject)

    if len(issue_regex.findall(message.subject)) > 0:
        raise logging.Error(
            message=C019_subject_contains_issue_reference.__doc__,
            line=message.subject,
            column_number=logging.Range(
                message.subject.find(issues[0]) + 1, len(issues[0])
            ),
        )


def C020_git_trailer_contains_whitespace(
    message: CommitMessage, _: Configuration
):  # pylint:  disable=C0103
    """Git-trailer should not contain whitespace(s)"""
    for item in message.footers:
        if " " in item.token and item.token != "BREAKING CHANGE":
            raise logging.Error(
                message=C020_git_trailer_contains_whitespace.__doc__,
                line=f"{item.token}: {item.value[0]}",
                column_number=logging.Range(0, len(item.token)),
            )


def C022_footer_contains_blank_line(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """Footer should not contain any blank line(s)"""
    for item in message.footers:
        if not item.token or len(item.value) == 0:
            raise logging.Error(
                message=C022_footer_contains_blank_line.__doc__,
            )


def C023_breaking_change_must_be_first_git_trailer(
    message: CommitMessage, _: Configuration
):  # pylint: disable=C0103
    """The BREAKING CHANGE git-trailer should be the first element in the footer"""
    for idx, item in enumerate(message.footers):
        if item.token == BREAKING_CHANGE_TOKEN:
            if idx != 0:
                raise logging.Error(
                    message=C023_breaking_change_must_be_first_git_trailer.__doc__,
                    line=f"{item.token}: {item.value[0]}",
                    column_number=logging.Range(0, len(item.token)),
                )


def validate_commit_message_rule(
    rule: str, message: CommitMessage, config: Configuration
):
    """Validates the specified rule #"""
    try:
        if config.rules[rule].get("enabled"):
            get_default_rules()[rule].get("obj")(message, config)
    except logging.Error as err:
        err.message = f"[{rule}] {err.message}"
        err.file_path = message.hexsha
        err.report()
        return 1

    return 0
