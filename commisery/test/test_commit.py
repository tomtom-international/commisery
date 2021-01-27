# Copyright (c) 2019 - 2019 TomTom N.V. (https://tomtom.com)
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

from ..commit import *

import pytest
import re


def test_basic_message_strip_and_splitup():
    """
    This tests these bits of functionality:

      * white space and comment stripping similar to how git-commit does it
      * line splitting
      * subject extraction
      * paragraph splitting
      * body extraction
    """
    m = CommitMessage('''\

# test stripping of comments and preceding empty lines

improvement(config): display config error messages without backtrace

In order to prevent users from thinking they're seeing a bug in Hopic.


This changes the type of ConfigurationError such that Click will display
its message without a backtrace. This ensures the displayed information
is more to the point.

# ------------------------ >8 ------------------------

This line and every other line after the 'cut' line above should not be present
in the output.

# test stripping of comments and succeeding empty lines

''')
    assert m.subject == '''improvement(config): display config error messages without backtrace'''
    assert m.lines[0] == m.subject

    assert m.paragraphs[0] == '''In order to prevent users from thinking they're seeing a bug in Hopic.'''
    assert m.paragraphs[0] == m.body.splitlines()[0]
    assert m.body.splitlines()[0] == m.message.splitlines()[2]

    assert m.paragraphs[1].splitlines(keepends=True)[0] == '''This changes the type of ConfigurationError such that Click will display\n'''

    assert m.paragraphs[-1].splitlines(keepends=True)[-1] == '''is more to the point.'''
    assert m.paragraphs[-1].splitlines()[-1] == m.body.splitlines()[-1]
    assert m.body.splitlines()[-1] == m.message.splitlines()[-1]

def test_commit_has_hexsha():
    commit = CommitMessage('fix: something', '0000000000000000000000000000000000000000')
    assert isinstance(commit.hexsha, str)

    conventional_commit = ConventionalCommit('fix: something', '0000000000000000000000000000000000000000')
    assert isinstance(conventional_commit.hexsha, str)

    reparsed_conventional_commit = CommitMessage(commit)
    assert isinstance(reparsed_conventional_commit.hexsha, str)

def test_conventional_missing_separator():
    with pytest.raises(RuntimeError, match=r'(lack|miss).*separator'):
        ConventionalCommit('fix display config error messages without backtrace')

    with pytest.raises(RuntimeError, match=r'(lack|miss).*separator'):
        ConventionalCommit('fix:display config error messages without backtrace')

def test_conventional_wrong_case_type_tag():
    with pytest.raises(RuntimeError, match=r'type.*tag.*upper.*case'):
        ConventionalCommit('Fix: display config error messages without backtrace')

def test_conventional_scoped_improvement():
    m = ConventionalCommit('improvement(config): display config error messages without backtrace')
    assert m.type_tag == 'improvement'
    assert m.scope == 'config'
    assert m.description == 'display config error messages without backtrace'
    assert not m.has_breaking_change()
    assert not m.has_new_feature()
    assert not m.has_fix()

def test_conventional_scope_with_space():
    ConventionalCommit('docs(git tips): improve documentation on amending')

def test_conventional_badly_scoped():
    with pytest.raises(RuntimeError, match=r'scope.*empty'):
        ConventionalCommit('fix(): display config error messages without backtrace')

    with pytest.raises(RuntimeError, match=r'scope.*whitespace'):
        ConventionalCommit('fix( config ): display config error messages without backtrace')

def test_conventional_fix():
    m = ConventionalCommit('fix: use the common ancestor of the source and target commit for autosquash')
    assert m.type_tag == 'fix'
    assert m.scope is None
    assert not m.has_breaking_change()
    assert not m.has_new_feature()
    assert m.has_fix()

def test_conventional_new_feature():
    m = ConventionalCommit('''feat: make execution possible with 'hopic' as command''')
    assert m.type_tag == 'feat'
    assert m.scope is None
    assert not m.has_breaking_change()
    assert m.has_new_feature()
    assert not m.has_fix()

def test_conventional_break():
    m = ConventionalCommit('''\
chore: cleanup old cfg.yml default config file name

BREAKING-CHANGE: "${WORKSPACE}/cfg.yml" is no longer the default location
of the config file. Instead only "${WORKSPACE}/hopic-ci-config.yaml" is
looked at.
''')
    assert m.type_tag == 'chore'
    assert m.scope is None
    assert m.has_breaking_change()
    assert not m.has_new_feature()
    assert not m.has_fix()

    footer, = m.footers
    assert footer.token == 'BREAKING CHANGE'
    assert 'default location' in footer.value

def test_conventional_subject_break():
    m = ConventionalCommit('''chore!: delete deprecated 'ci-driver' command''')
    assert m.type_tag == 'chore'
    assert m.scope is None
    assert m.has_breaking_change()
    assert not m.has_new_feature()
    assert not m.has_fix()

def test_conventional_subject_breaking_fix():
    m = ConventionalCommit('''fix!: take parameter as unsigned instead of signed int''')
    assert m.type_tag == 'fix'
    assert m.scope is None
    assert m.has_breaking_change()
    assert not m.has_new_feature()
    assert m.has_fix()

def test_conventional_badly_marked_as_breaking():
    with pytest.raises(RuntimeError, match=r'breaking.*indicator'):
        ConventionalCommit('fix !: display config error messages without backtrace')

    with pytest.raises(RuntimeError, match=r'breaking.*indicator'):
        ConventionalCommit('fix! : display config error messages without backtrace')

    with pytest.raises(RuntimeError, match=r'breaking.*indicator'):
        ConventionalCommit('fix ! : display config error messages without backtrace')

def test_conventional_subject_breaking_new_feature():
    m = ConventionalCommit('''feat!: support multiple non-global current working directories''')
    assert m.type_tag == 'feat'
    assert m.scope is None
    assert m.has_breaking_change()
    assert m.has_new_feature()
    assert not m.has_fix()

def test_conventional_fixup_fix():
    m = ConventionalCommit('fixup! fix: only restore mtime for regular files and symlinks')
    assert m.type_tag == 'fix'
    assert m.scope is None
    assert m.description == 'only restore mtime for regular files and symlinks'
    assert not m.has_breaking_change()
    assert not m.has_new_feature()
    assert m.has_fix()


def test_conventional_multiple_errors_in_message():
    with pytest.raises(RuntimeError) as ex_info:
        ConventionalCommit('Fix( ) something')

    for regex in (
        '.*upper[^\n]*case[^\n]*letters',
        '.*scope[^\n]*whitespace',
        '.*type[^\n]*tag[^\n]*upper[^\n]*case',
    ):
        assert re.match(regex, str(ex_info.value), flags=re.DOTALL) != None


def test_multiple_fixups():
    """Permit multiple stacked fixup! and squash! prefixes"""
    m = CommitMessage('fixup! squash! fixup! something')
    assert m.autosquashed_subject == 'something'


def test_basic_footers():
    m = CommitMessage('''\
Merge #63: something

Bla bla

BREAKING CHANGE: something changed in an unpredicted way

Addresses #42 by working on finding the question
Implements: PIPE-123 through the obliviator
Acked-by: Alice <alice@example.com>
Merged-by: Hopic 1.21.2
Acked-by: Bob <bob@example.com>
''')
    with pytest.raises(KeyError):
        # git-trailer format for footers doesn't permit spaces in the token name
        _ = m.footers['BREAKING CHANGE']

    assert tuple(tuple(footer) for footer in m.footers) == (
            ('Addresses' , '#42 by working on finding the question'),
            ('Implements', 'PIPE-123 through the obliviator'),
            ('Acked-by'  , 'Alice <alice@example.com>'),
            ('Merged-by' , 'Hopic 1.21.2'),
            ('Acked-by'  , 'Bob <bob@example.com>'),
        )


def test_conventional_footers():
    m = ConventionalCommit('''\
Merge #63: improvement(groovy): retrieve execution graph in a single 'getinfo' call

This should reduce the amount of Jenkins master/slave interactions and
their associated Groovy script engine "context switches" (state
serialization and restoration). As a result performance should increase.

Addresses #279 by adding a test framework.

Acked-by: Anton Indrawan <Anton.Indrawan@tomtom.com>
Acked-by: Joost Muller <Joost.Muller@tomtom.com>
Acked-by: Martijn Leijssen <Martijn.Leijssen@tomtom.com>
Acked-by: Rene Kempen <Rene.Kempen@tomtom.com>
Merged-by: Hopic 0.10.2.dev7+g840ca0c
''')
    assert m.type_tag == 'improvement'
    assert m.scope == 'groovy'

    assert tuple(tuple(footer) for footer in m.footers) == (
            ('Addresses', '#279 by adding a test framework.'),

            ('Acked-by' , 'Anton Indrawan <Anton.Indrawan@tomtom.com>'),
            ('Acked-by' , 'Joost Muller <Joost.Muller@tomtom.com>'),
            ('Acked-by' , 'Martijn Leijssen <Martijn.Leijssen@tomtom.com>'),
            ('Acked-by' , 'Rene Kempen <Rene.Kempen@tomtom.com>'),

            ('Merged-by', 'Hopic 0.10.2.dev7+g840ca0c'),
        )
