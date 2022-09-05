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

from textwrap import dedent
import pytest
from commisery.commit import parse_commit_message
from commisery.config import Configuration
from commisery import rules

import llvm_diagnostics as logger


def __validate_rule(rule, message, exception):
    if exception:
        with pytest.raises(logger.Error) as exc_info:
            rule(parse_commit_message(message), Configuration())
        assert exc_info.value.message.startswith(rule.__doc__)
    else:
        rule(parse_commit_message(message), Configuration())


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("fEAT: placeholder description", True),
        ("Feat: placeholder description", True),
        ("FEAT: placeholder description", True),
    ),
)
def test_C001_non_lower_case_type(message, exception):
    __validate_rule(rules.C001_non_lower_case_type, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            dedent(
                """\
                feat: placeholder description
            
                placeholder body
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                feat: placeholder description
                placeholder body
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                feat: placeholder description
                
                
                placeholder body
            """
            ),
            True,
        ),
        ("feat: PLACEHOLDER description", False),
    ),
)
def test_C002_one_whiteline_between_subject_and_body(message, exception):
    __validate_rule(
        rules.C002_one_whiteline_between_subject_and_body, message, exception
    )


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat: pLaceholder description", False),
        ("feat: Placeholder description", True),
        ("feat: PLACEHOLDER description", True),
    ),
)
def test_C003_title_case_description(message, exception):
    __validate_rule(rules.C003_title_case_description, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("fix: placeholder description", False),
        ("feet: placeholder description", True),
        ("fox: placeholder description", True),
    ),
)
def test_C004_unknown_tag_type(message, exception):
    __validate_rule(rules.C004_unknown_tag_type, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat : placeholder description", True),
        ("feat:  placeholder description", True),
    ),
)
def test_C005_separator_contains_trailing_whitespaces(message, exception):
    __validate_rule(
        rules.C005_separator_contains_trailing_whitespaces, message, exception
    )


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat( ): placeholder description", False),
        ("feat(): placeholder description", True),
        ("feat!: placeholder description", False),
        ("feat( )!: placeholder description", False),
        ("feat()!: placeholder description", True),
    ),
)
def test_C006_scope_should_not_be_empty(message, exception):
    __validate_rule(rules.C006_scope_should_not_be_empty, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat(): placeholder description", False),
        ("feat( ): placeholder description", True),
        ("feat(    ): placeholder description", True),
        ("feat(  a  ): placeholder description", True),
        ("feat( )!: placeholder description", True),
    ),
)
def test_C007_scope_contains_whitespace(message, exception):
    __validate_rule(rules.C007_scope_contains_whitespace, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat(test): placeholder description", False),
        ("feat placeholder description", True),
        ("feat(test) placeholder description", True),
    ),
)
def test_C008_missing_separator(message, exception):
    __validate_rule(rules.C008_missing_separator, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat(test): placeholder description", False),
        ("feat", True),
        ("feat!", True),
        ("feat:", True),
        ("feat: ", True),
        ("feat(test):", True),
    ),
)
def test_C009_missing_description(message, exception):
    __validate_rule(rules.C009_missing_description, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat!: placeholder description", False),
        ("feat(test)!: placeholder description", False),
        ("feat !: placeholder description", True),
        ("feat! : placeholder description", True),
        ("feat ! : placeholder description", True),
    ),
)
def test_C010_breaking_indicator_contains_whitespacing(message, exception):
    __validate_rule(
        rules.C010_breaking_indicator_contains_whitespacing, message, exception
    )


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat!: placeholder description", False),
        ("feat(test)!: placeholder description", False),
        ("feat!!: placeholder description", True),
        ("feat!!!: placeholder description", True),
    ),
)
def test_C011_only_single_breaking_indicator(message, exception):
    __validate_rule(rules.C011_only_single_breaking_indicator, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat(test): placeholder description", False),
        (": placeholder description", True),
        ("!: placeholder description", True),
        ("(test)!: placeholder description", True),
    ),
)
def test_C012_missing_type_tag(message, exception):
    __validate_rule(rules.C012_missing_type_tag, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("feat: placeholder description", False),
        ("feat(test): placeholder description", False),
        ("feat: placeholder description!", True),
        ("feat!: placeholder description.", True),
        ("feat(test)!: placeholder description?", True),
    ),
)
def test_C013_subject_should_not_end_with_punctuation(message, exception):
    __validate_rule(
        rules.C013_subject_should_not_end_with_punctuation, message, exception
    )


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            "feat: 12345678901234567890123456789012345678901234567890123456789012345678901234",
            False,
        ),
        (
            "feat: 123456789012345678901234567890123456789012345678901234567890123456789012345",
            True,
        ),
    ),
)
def test_C014_subject_exceeds_line_lenght_limit(message, exception):
    __validate_rule(rules.C014_subject_exceeds_line_lenght_limit, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("fix: placeholder description", False),
        ("fix(test): placeholder description", False),
        ("fix: fix it", True),
        ("fix(test): Fix it", True),
        ("test(test)!: test it", True),
    ),
)
def test_C015_no_repeated_tags(message, exception):
    __validate_rule(rules.C015_no_repeated_tags, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("fix: add something", False),
        ("fix(test): add something", False),
        ("fix: added something", True),
        ("fix(test): adding something", True),
    ),
)
def test_C016_description_in_imperative_mood(message, exception):
    __validate_rule(rules.C016_description_in_imperative_mood, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        ("docs: update changelog", False),
        ("docs: added docs based on review remarks", True),
    ),
)
@pytest.mark.skip(reason="this rules has not yet been implemented")
def test_C017_subject_contains_review_remarks(message, exception):
    __validate_rule(rules.C017_subject_contains_review_remarks, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            dedent(
                """\
                feat: placeholder description
            
                placeholder body
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                feat: placeholder description
                
                
                placeholder body
            """
            ),
            False,
        ),
        ("feat: PLACEHOLDER description", False),
        (
            dedent(
                """\
                feat: placeholder description
                placeholder body
            """
            ),
            True,
        ),
    ),
)
def test_C018_missing_empty_line_between_subject_and_body(message, exception):
    __validate_rule(
        rules.C018_missing_empty_line_between_subject_and_body, message, exception
    )


@pytest.mark.parametrize(
    "message, exception",
    (
        ("fix: add something", False),
        ("fix(test): add something", False),
        ("fix(test): add something for SHA-256", False),
        ("fix: added something for NAV-1234", True),
    ),
)
def test_C019_subject_contains_issue_reference(message, exception):
    __validate_rule(rules.C019_subject_contains_issue_reference, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                Acked-by : Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            True,
        ),
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                Acked by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            True,
        ),
        (
            dedent(
                """\
                Merge #13: feat: add documentation publication

                * feat: add documentation publication

                    Implements NAV-27889

                    Signed-off-by: Alexandru Lazarescu <alexandru.lazarescu@tomtom.com>

                * feat: add documentation publication

                    Implements NAV-27889

                    Signed-off-by: Alexandru Lazarescu <alexandru.lazarescu@tomtom.com>

                Acked by: Martijn Leijssen <Martijn.Leijssen@tomtom.com>
                Merged-by: Hopic 1.22.1.dev37+g1b1a265
                """
            ),
            True
        ),
        (
            dedent(
                """\
                Merge #13: feat: add documentation publication

                * feat: add documentation publication

                    Implements NAV-27889

                    Signed-off-by: Alexandru Lazarescu <alexandru.lazarescu@tomtom.com>

                * feat: add documentation publication

                    Implements NAV-27889

                    Signed-off-by: Alexandru Lazarescu <alexandru.lazarescu@tomtom.com>

                Acked-by: Martijn Leijssen <Martijn.Leijssen@tomtom.com>
                Merged-by: Hopic 1.22.1.dev37+g1b1a265
                """
            ),
            False,
        ),
    ),
)
def test_C020_git_trailer_contains_whitespace(message, exception):
    __validate_rule(rules.C020_git_trailer_contains_whitespace, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                Addresses #12

                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            True,
        ),
        (
            dedent(
                """\
                fix: add something

                BREAKING-CHANGE: This is a breaking change
                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                BREAKING-CHANGE: This is a breaking change

                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                BREAKING-CHANGE: This is a breaking change

                Addresses #12

                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            True,
        ),
    ),
)
def test_C022_footer_contains_blank_line(message, exception):
    __validate_rule(rules.C022_footer_contains_blank_line, message, exception)


@pytest.mark.parametrize(
    "message, exception",
    (
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                BREAKING-CHANGE: This is a breaking change
                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                BREAKING-CHANGE: This is a breaking change

                Addresses #12
                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            False,
        ),
        (
            dedent(
                """\
                fix: add something

                Addresses #12
                BREAKING-CHANGE: This is a breaking change

                Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
            """
            ),
            True,
        ),
    ),
)
def test_C023_breaking_change_must_be_first_git_trailer(message, exception):
    __validate_rule(
        rules.C023_breaking_change_must_be_first_git_trailer, message, exception
    )
