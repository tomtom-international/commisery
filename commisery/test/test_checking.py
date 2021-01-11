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

from .. import checking
import pytest
import re
import sys
from textwrap import dedent


def strip_terminal_ctrl_codes(msg):
    return re.sub(r'\x1B\[(?:\d+(?:;\d+)*)?m', '', msg)


def get_verification_failures(msg, nr=None):
    err = '\n'.join(checking.check_commit_message('test-commit', msg))
    sys.stderr.write(err)

    diagnostics = []
    line_re = re.compile(r'test-commit:\d+:\d+: (?:error|note): ')
    for line in strip_terminal_ctrl_codes(err).splitlines(keepends=True):
        if line_re.match(line):
            diagnostics.append(line)
        else:
            if not diagnostics:
                print((line, line_re), file=sys.stderr)
            diagnostics[-1] += line

    return diagnostics


def test_initial_capital():
    diagnostic, = get_verification_failures('fix: Change the thingy')
    assert re.search(r'\btitle case\b.*\bdescription\b', diagnostic)


@pytest.mark.parametrize('msg', (
    'fix: change as per review comments',
    'fix: process review comment',
    'fix: use different DLT contexts in Positioning Service - process review comment',
    'fix: introduce ServiceSimulator tool: resolve review findings',
    'fix: use systemd to start the navigationwindowmanager (review comments)',
    'fix: resolve review comments',
    'fix: implement DLT logging in Positioning Service (review comments)',
    'fix: changes according review',
    'fix: processing minor code review comments',
    'fix: implemented review comments',
    'fix: processed all review comments',
    'fix: process review comments (rename version file and remove trailing spaces)',
    'fix: process review comment',
    'fix: gNSS Simulator. Fixes for review comments by Jitendra',
    'fix: code review comments resolved',
    'fix: processed minor review comment',
    'fix: processed review comments for blabla',
    'fix: apply review comments',
    'fix: addressd review comments',
    'fixup! fix: ATF_TestCasesNeedFix_RoadShields test cases - incorporated review comments',
    'fix: edit online with Bitbucket',
    'fix: apply reviewer\'s comments',
))
def test_reject_referring_to_review_comments(msg):
    error, note = get_verification_failures(msg)
    assert re.search(r'\bcontext\b.*\binstead\b.*\brefer.*\breview.*\b(?:comment|message)', error)
    assert '--fixup' in note


def test_accept_blacklisted_words_in_fixup_commit_body():
    assert not get_verification_failures(dedent('''
    fixup! fix: ATF_TestCasesNeedFix_RoadShields test cases

    I like to help my colleagues understand my changes, so I provide extra
    information in my fixups, some of which might be blacklisted,
    like how I refer to review comments or perhaps edit online with Bitbucket.
    '''))


@pytest.mark.parametrize('msg', (
    'fix: force XML encoding to UTF-8',
    'fix: check computed SHA-256 hash against expected value',
    'feat: display colors using VT-100/VT-220 control codes',
    'feat: implement AES-128 CTR mode en/decryption',
    'fix: ensure generated version numbers adhere to PEP-440',
))
def test_accept_common_abbreviations_as_not_Jira(msg):
    assert not get_verification_failures(msg)


def test_accept_capital_TomTom():
    assert not get_verification_failures('feat: TomTom home screen redecorated')


def test_type_tag_typo():
    diagnostic, = get_verification_failures('impovemtn: verify the thingamajig')
    assert diagnostic.splitlines()[-1] == 'improvement'


def test_scope_whitespace():
    error, = get_verification_failures('improvement( verifier ): verify the thingamajig')
    assert re.search(r'\bwhite.*space\b.*\bscope\b', error)
    assert not get_verification_failures('improvement(thingamajig verifier): verify the thingamajig')


def test_empty_scope():
    error, = get_verification_failures('improvement(): verify the thingamajig')
    assert re.search(r'\bscope\b.*\bempty\b', error)


def test_missing_separator():
    error, = get_verification_failures('improvement verify the thingamajig')
    assert re.search(r'\bseparator\b.*\btype\b.*\btag\b', error)


def test_description_whitespace():
    error, = get_verification_failures('improvement: verify the   thingamajig')
    assert re.search(r'\bwhite.*space\b.*\bdescription\b', error)


def test_jira_ticket():
    error, = get_verification_failures('improvement: verify the thingamajig introduced with PIPE-423')
    assert re.search(r'\bcontains?\b.*\bjira tickets?\b', error, re.IGNORECASE)


def test_punctuation():
    error, = get_verification_failures('improvement: verify the thingamajig.')
    assert 'punctuation' in error


def test_body_unseparated_from_subject():
    error, = get_verification_failures('''\
improvement: verify the thingamajig
Hmpf
Bla bla...
''')
    assert re.search(r'\bsubject\b.*\bbody\b.*\bseparat.*\bempty line\b', error)


def test_non_imperative():
    error, *notes = get_verification_failures('fix: added missing files')
    assert re.search(r'\bdescription\b.*\bimperative\b', error)
    assert 'imperative' in notes[0]


@pytest.mark.parametrize('msg, expected_note', (
    ('refactor: refactor stuff', '`refactor` commit contains'),
    ('fix: fix issue', 'fix in more detail'),
))
def test_repeat_tag(msg, expected_note):
    error, *notes = get_verification_failures(msg)
    assert re.search(r'\bdescription\b.*\brepeats\b', error)
    assert expected_note in notes[0]


def test_whitespace_breaking():
    error, = get_verification_failures('refactor(mooh) !: revamp API to be more awesome')
    assert re.search(r'\bbreaking change indicator\b.*\b(?:whitespace|should\b.*\bexactly)\b', error)


def test_review_comment_spread_out_in_body():
    error, note = get_verification_failures('''feat: something awesome

Perform
some review
rework.

Implements #PIPE-123''')

    assert re.search(r'\bcontext\b.*\binstead\b.*\brefer.*\breview.*\b(?:comment|message)', error)
    assert '--fixup' in note
