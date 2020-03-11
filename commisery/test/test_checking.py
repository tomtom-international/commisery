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


def strip_terminal_ctrl_codes(msg):
    return re.sub(r'\x1B\[(?:\d+(?:;\d+)*)?m', '', msg)


def get_verification_failures(tmp_path, capsys, msg, nr=None):
    if nr is None:
        tmp_path /= f"msg.txt"
    else:
        tmp_path /= f"msg-{nr:03d}.txt"
    with open(tmp_path, 'w', encoding='UTF-8') as f:
        f.write(msg)

    exit_code = checking.main((None, tmp_path))

    out, err = capsys.readouterr()
    sys.stdout.write(out)
    sys.stderr.write(err)

    assert out == ''

    diagnostics = []
    line_re = re.compile('^' + re.escape(str(tmp_path)) + r':\d+:\d+: (?:error|note): ')
    for line in strip_terminal_ctrl_codes(err).splitlines(keepends=True):
        if line_re.match(line):
            diagnostics.append(line)
        else:
            if not diagnostics:
                print((line, line_re), file=sys.stderr)
            diagnostics[-1] += line

    assert diagnostics or exit_code == 0
    return diagnostics


def test_initial_capital(tmp_path, capsys):
    diagnostic, = get_verification_failures(tmp_path, capsys, 'fix: Change the thingy')
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
def test_reject_referring_to_review_comments(tmp_path, capsys, msg):
    error, note = get_verification_failures(tmp_path, capsys, msg)
    assert re.search(r'\bcontext\b.*\binstead\b.*\brefer.*\breview.*\b(?:comment|message)', error)
    assert '--fixup' in note


@pytest.mark.parametrize('msg', (
    'fix: force XML encoding to UTF-8',
    'fix: check computed SHA-256 hash against expected value',
    'feat: display colors using VT-100/VT-220 control codes',
    'feat: implement AES-128 CTR mode en/decryption',
    'fix: ensure generated version numbers adhere to PEP-440',
))
def test_accept_common_abbreviations_as_not_Jira(tmp_path, capsys, msg):
    assert not get_verification_failures(tmp_path, capsys, msg)


def test_accept_capital_TomTom(tmp_path, capsys):
    assert not get_verification_failures(tmp_path, capsys, 'feat: TomTom home screen redecorated')


def test_type_tag_typo(tmp_path, capsys):
    diagnostic, = get_verification_failures(tmp_path, capsys, 'impovemtn: verify the thingamajig')
    assert diagnostic.splitlines()[-1] == 'improvement'


def test_scope_whitespace(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'improvement( verifier ): verify the thingamajig')
    assert re.search(r'\bwhite.*space\b.*\bscope\b', error)


def test_missing_separator(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'improvement verify the thingamajig')
    assert re.search(r'\bseparator\b.*\btype\b.*\btag\b', error)


def test_description_whitespace(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'improvement: verify the   thingamajig')
    assert re.search(r'\bwhite.*space\b.*\bdescription\b', error)


def test_jira_ticket(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'improvement: verify the thingamajig introduced with PIPE-423')
    assert re.search(r'\bcontains?\b.*\bjira tickets?\b', error, re.IGNORECASE)


def test_punctuation(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'improvement: verify the thingamajig.')
    assert 'punctuation' in error


def test_body_unseparated_from_subject(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, '''\
improvement: verify the thingamajig
Hmpf
Bla bla...
''')
    assert re.search(r'\bsubject\b.*\bbody\b.*\bseparat.*\bempty line\b', error)


def test_non_imperative(tmp_path, capsys):
    error, note = get_verification_failures(tmp_path, capsys, 'fix: added missing files')
    assert re.search(r'\bdescription\b.*\b(?:blacklisted|imperative)\b', error)
    assert 'imperative' in note


def test_whitespace_breaking(tmp_path, capsys):
    error, = get_verification_failures(tmp_path, capsys, 'refactor(mooh) !: revamp API to be more awesome')
    assert re.search(r'\bbreaking change indicator\b.*\b(?:whitespace|should\b.*\bexactly)\b', error)


def test_review_comment_spread_out_in_body(tmp_path, capsys):
    error, note = get_verification_failures(tmp_path, capsys, '''feat: something awesome

Perform
some review
rework.

Implements #PIPE-123''')

    assert re.search(r'\bcontext\b.*\binstead\b.*\brefer.*\breview.*\b(?:comment|message)', error)
    assert '--fixup' in note
