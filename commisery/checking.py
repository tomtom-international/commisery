#!/usr/bin/env python3

# Copyright (c) 2019 - 2020 TomTom N.V. (https://tomtom.com)
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

from pathlib import Path
from .commit import CommitMessage

from collections import namedtuple
from functools import wraps
from inspect import getfullargspec
import difflib
import itertools
import os
import re
import sys
import subprocess
from typing import (
        get_type_hints,
        Iterable,
        Sequence,
    )
try:
    from stemming.porter2 import stem
except ImportError:
    stem = None
try:
    import regex
except ImportError:
    regex = None

def type_check(f):
    @wraps(f)
    def validate_parameters(*args, **kwargs):
        func_args = getfullargspec(f)[0]
        kw = kwargs.copy()
        kw.update(dict(zip(func_args, args)))

        for attr_name, attr_type in get_type_hints(f).items():
            if attr_name == 'return':
                continue

            if attr_name in kw and not isinstance(kw[attr_name], attr_type):
                raise TypeError(f"Argument {attr_name!r} is not of type {attr_type}")
        return f(*args, **kwargs)
    return validate_parameters


MatchGroup = namedtuple('MatchGroup', ('text', 'name', 'start', 'end'))


def main(argv=None):
    if argv is None:
        argv = sys.argv[:]

    commit = 'HEAD'
    if len(argv) >= 2:
        commit = argv[1]

    try:
        if re.match(r'^[0-9a-fA-F]{40}$', str(commit)):
            raise IOError('a full commit hash should never be treated as a file')

        with open(commit, encoding='UTF-8') as f:
            message = CommitMessage(f.read())
    except IOError:
        commit = subprocess.check_output(('git', 'rev-parse', commit))[:-1].decode('UTF-8')
        message = CommitMessage(subprocess.check_output(('git', 'show', '-q', '--format=%B', commit, '--'))[:-1].decode('UTF-8'))

    errors = []

    if not message.lines[-1]:
        errors.append(f"\x1B[1m{commit}:{len(message.lines)}:1: \x1B[31merror\x1B[39m: commit message body is followed by empty lines\x1B[m")

    if re.match(r"^Merge (?:branch|tag) '.*?'(?:into '.*')?$", message.subject):
        # Ignore branch/tag merges
        sys.exit(0)

    subject_re = re.compile(r'''
        ^
        # 1. Commits MUST be prefixed with a type, which consists of a noun, feat, fix, etc., ...
        (?P<type_tag>\w+)

        # 4. A scope MAY be provided after a type. A scope MUST consist of a noun describing a section of the codebase
        #    surrounded by parenthesis, e.g., `fix(parser):`
        (?: \( (?P<scope> [^()]* ) \) )?

        # 1. Commits MUST be prefixed with a type, ..., followed by ..., OPTIONAL `!`, ...
        (?P<breaking>\s*!(?:\s+(?=:))?)?

        # 1. Commits MUST be prefixed with a type, ..., and REQUIRED terminal colon and space.
        (?P<separator>:?[ ]?)

        # 5. A description MUST immediately follow the colon and space after the type/scope prefix. The description is a
        #    short description of the code changes, e.g., fix: array parsing issue when multiple spaces were contained in
        #    string.
        (?P<description>.*)

        $
        ''', re.VERBOSE)
    subject = subject_re.match(message.subject)
    if not subject:
        error = f"\x1B[1m{commit}:1:1: \x1B[31merror\x1B[39m: commit message's subject not formatted according to Conventional Commits\x1B[m\n{subject_re.pattern}\n"
        error += message.full_subject + '\n'
        error += ' ' * message.subject_start + '\x1B[32m' + '^' * max(len(message.full_subject) - message.subject_start, 1) + '\x1B[39m'
        errors.append(error)

    def extract_match_group(match, group, start=0):
        if match is None or match.group(group) is None:
            return None
        return MatchGroup(name=group, text=match.group(group), start=match.start(group)+start, end=match.end(group)+start)

    type_tag    = extract_match_group(subject, 'type_tag'   , message.subject_start)
    scope       = extract_match_group(subject, 'scope'      , message.subject_start)
    breaking    = extract_match_group(subject, 'breaking'   , message.subject_start)
    separator   = extract_match_group(subject, 'separator'  , message.subject_start)
    description = extract_match_group(subject, 'description', message.subject_start)

    @type_check
    def complain_about_excess_space(match: MatchGroup, line: int = 0) -> None:
        excess_whitespace = list(itertools.chain.from_iterable(
                range(*space.span()) for space in re.finditer(r'\s{2,}|^\s+|\s+$', match.text)))
        if excess_whitespace:
            error = "\x1B[1m{commit}:{line}:{col}: \x1B[31merror\x1B[39m: excess whitespace in {match.name}\x1B[m\n".format(line=line + 1, col=match.start + 1 + excess_whitespace[0], match=match, commit=commit)
            error += message.full_subject + '\n'
            error += '\x1B[32m'
            cur = -match.start
            for pos in excess_whitespace:
                error += ' ' * (pos - cur) + '^'
                cur = pos + 1
            error += '\x1B[39m'
            errors.append(error)

    accepted_tags = (
            'build',
            'chore',
            'ci',
            'docs',
            'perf',
            'refactor',
            'revert',
            'style',
            'test',
            'improvement',
        )

    # 1. Commits MUST be prefixed with a type, which consists of a noun, feat, fix, etc., followed by a colon and a space.
    # 2. The type feat MUST be used when a commit adds a new feature to your application or library.
    # 3. The type fix MUST be used when a commit represents a bug fix for your application.
    if type_tag and type_tag.text not in accepted_tags and type_tag.text not in ('feat', 'fix'):
        error = f"\x1B[1m{commit}:1:1: \x1B[31merror\x1B[39m: use of type tag that's neither 'feat', 'fix' nor whitelisted ({', '.join(accepted_tags)})\x1B[m\n"
        error += message.full_subject + '\n'
        error += ' ' * type_tag.start + '\x1B[31m' + '~' * (type_tag.end - type_tag.start) + '\x1B[39m'
        possibilities = difflib.get_close_matches(type_tag.text, ('feat', 'fix') + accepted_tags, n=1)
        if possibilities:
            error += '\n' + possibilities[0]
        errors.append(error)

    # 4. An optional scope MAY be provided after a type. A scope is a phrase describing a section of the codebase enclosed
    #    in parenthesis, e.g., fix(parser):
    if scope is not None:
        complain_about_excess_space(scope)

    # 13. If included in the type/scope prefix, breaking changes MUST be indicated by a `!` immediately before the `:`.
    #     If `!` is used, `BREAKING CHANGE: ` MAY be ommitted from the footer section, and the commit description SHALL be
    #     used to describe the breaking change.
    if breaking is not None and breaking.text != '!':
        error = f"\x1B[1m{commit}:1:{breaking.start + 1}: \x1B[31merror\x1B[39m: breaking change indicator in commit message's subject should be exactly '!'\x1B[m\n"
        error += message.full_subject + '\n'
        error += breaking.start * ' ' + '\x1B[31m' + breaking.text.find('!') * '~' + ' ' + (len(breaking.text) - 1 - breaking.text.find('!')) * '~' + '\x1B[39m'
        errors.append(error)

    # 1. Commits MUST be prefixed with a type, ..., followed by a colon and a space.
    if separator and separator.text != ': ':
        error = f"\x1B[1m{commit}:1:{separator.start + 1}: \x1B[31merror\x1B[39m: commit message's subject lacks a ': ' separator after the type tag\x1B[m\n"
        error += message.full_subject + '\n'
        error += separator.start * ' ' + '\x1B[32m^' * max(1, separator.end - separator.start) + '\x1B[39m'
        errors.append(error)

    # 5. A description MUST immediately follow the type/scope prefix. The description is a short description of the
    #    code changes, e.g., fix: array parsing issue when multiple spaces were contained in string.
    if description and not description.text:
        error = f"\x1B[1m{commit}:1:{description.start + 1}: \x1B[31merror\x1B[39m: commit message's subject lacks a description after the type tag\x1B[m\n"
        error += message.full_subject + '\n'
        error += ' ' * description.start + '\x1B[32m^\x1B[39m'
        errors.append(error)

    def complain_about_review_refs(component, component_start=0, lineno=0, quote_text=None):
        """
        Disallow referring to review comments because it's a poor excuse for a proper commit message
        """

        review_comment_ref = None
        if stem is not None:
            words = tuple((word.group(), stem(word.group()).lower(), word.start(), word.end()) for word in re.finditer(r'\b(?:\w|[-])+\b', component))
            opt_prefix = frozenset({
                    'all',
                    'as',
                    'code',
                    'edit',
                    'for',
                    'minor',
                    'per',
                    'request',
                })
            opt_suffix = frozenset({
                    'comment',
                    'find',
                    'with',
                })
            reference_words = frozenset({
                    'accord',
                    'bitbucket',
                    'address',
                    'appli',
                    'chang',
                    'fix',
                    'implement',
                    'incorpor',
                    'per',
                    'process',
                    'resolv',
                    'rework',
                })
            ref_start, ref_end = None, None
            def encounter(word: str, opts: Sequence[str]) -> bool:
                return bool(word in opts or difflib.get_close_matches(word, opts, cutoff=0.9))
            for idx, (word, stemmed, start, end) in enumerate(words):
                if stemmed not in ('review', 'onlin'):
                    continue
                min_idx = idx
                while min_idx > 0 and encounter(words[min_idx-1][1], opt_prefix):
                    min_idx -= 1
                if min_idx > 0 and encounter(words[min_idx-1][1], reference_words):
                    min_idx -= 1
                    ref_start = words[min_idx][2]
                    ref_end = end
                max_idx = idx
                while max_idx + 1 < len(words) and encounter(words[max_idx+1][1], opt_suffix):
                    max_idx += 1
                    if ref_end is not None:
                        ref_end = max(ref_end, words[max_idx][3])
                if max_idx + 1 < len(words) and encounter(words[max_idx+1][1], reference_words):
                    max_idx += 1
                    if ref_start is None:
                        ref_start = len(component)
                    if ref_end is None:
                        ref_end = 0
                    ref_start = min(ref_start, words[min_idx][2])
                    ref_end = max(ref_end, words[max_idx][3])
                if ref_start is None and ref_end is None:
                    brace_prefix = re.match(r'^.*([(])\s*', component[:start])
                    brace_suffix = re.match(r'\s*([)])', component[words[max_idx][3]:])
                    if brace_prefix and brace_suffix:
                        ref_start = brace_prefix.start(1)
                        ref_end = brace_prefix.end(1)
                if ref_start is None and ref_end is None:
                    for try_idx, (try_word, try_stemmed, _, _) in enumerate(words[min_idx:max_idx+1], min_idx):
                        if encounter(try_stemmed, reference_words):
                            ref_start = words[min_idx][2]
                            ref_end = words[max_idx][3]
                            break
                if ref_start is not None and ref_end is not None:
                    review_comment_ref = MatchGroup(name=0, text=component[ref_start:ref_end], start=ref_start+component_start, end=ref_end+component_start)
                    break
        else:
            review_comment_ref = re.search(r'''
                (?:accord|address|apply|implement|incorporat|process|resolv|rework)(?:e|e?[sd]|ing)?\s+
                (?:all\s+)?
                (?:minor\s+)?
                (?:code\s+)?
                review(?:\s+(?:comment|finding)s?)?\b
                |review\s+comments\s+    (?:accord|address|apply|implement|incorporat|process|resolv|rework)(?:e|e?[sd]|ing)?\s+
                |\breview\s+rework(?:ing|ed)?\b
                |[(] \s* review \s+ (?:comment|finding)s? \s* [)]
                ''',
                component, re.VERBOSE|re.IGNORECASE)
            review_comment_ref = extract_match_group(review_comment_ref, 0, component_start)

        if review_comment_ref:
            if quote_text is None:
                quote_text = component
            quote_start = quote_text.rfind('\n', 0, review_comment_ref.start) + 1
            quote_end = (quote_text + '\n').find('\n', review_comment_ref.end)
            line = lineno + quote_text[:quote_start + 1].count('\n')
            start = review_comment_ref.start - quote_start

            error = f"\x1B[1m{commit}:{line + 1}:{start + 1}: \x1B[31merror\x1B[39m: add context directly to commit messages instead of referring to review comments\x1B[m\n"
            last = 0
            for linem in re.finditer('\n', review_comment_ref.text + '\n'):
                if last == 0:
                    error += quote_text[quote_start:quote_start + start + linem.start() + 1] + '\n'
                    error += ' ' * start
                else:
                    error += review_comment_ref.text[last:linem.start()] + '\n'
                error += '\x1B[32m' + '^' * (linem.start() - last) + '\x1B[39m\n'
                
                last = linem.end()
            error += f"\x1B[1m{commit}:{line + 1}:{start + 1}: \x1B[30mnote\x1B[39m: prefer using --fixup when fixing previous commits in the same pull request\x1B[m"
            errors.append(error)


    if description is not None:
        complain_about_excess_space(description)

        # Prevent upper casing the first letter of the first word, this is not a book-style sentence.
        if regex is None:
            title_case_re = re.compile(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b')
        else:
            title_case_re = regex.compile(r'\b[\p{Lu}\p{Lt}]\p{Ll}*(?:\s+[\p{Lu}\p{Lt}]\p{Ll}*)*\b')
        title_case_word = extract_match_group(title_case_re.match(description.text), 0, description.start)
        safe_words = (
                'TomTom',
            )
        if title_case_word and title_case_word.text not in safe_words:
            error = f"\x1B[1m{commit}:1:{title_case_word.start + 1}: \x1B[31merror\x1B[39m: don't use title case in the description\x1B[m\n"
            error += message.full_subject + '\n'
            error += ' ' * title_case_word.start + '\x1B[32m' + '^' + '~' * (title_case_word.end - title_case_word.start - 1) + '\x1B[39m'
            possibilities = difflib.get_close_matches(title_case_word.text, safe_words, n=1)
            if possibilities:
                error += f"\n\x1B[1m{commit}:1:{title_case_word.start + 1}: \x1B[30mnote\x1B[39m: did you mean {possibilities[0]!r}?\x1B[m"
            errors.append(error)

        complain_about_review_refs(description.text, description.start, quote_text=message.full_subject)

        # Our own requirements on the description
        # No JIRA tickets in the subject line, because it wastes precious screen estate (80 chars)
        non_jira_projects = (
                'AES', # AES-128
                'PEP', # PEP-440
                'SHA', # SHA-256
                'UTF', # UTF-8
                'VT',  # VT-220
            )
        jira_re = re.compile(r'\b(?!' + '|'.join(re.escape(i + '-') for i in non_jira_projects) + r')[A-Z]+-[0-9]+\b')
        jira_tickets = []
        for m in jira_re.finditer(description.text):
            jira_tickets.extend(range(*m.span()))
        if jira_tickets:
            error = "\x1B[1m{commit}:{line}:{col}: \x1B[31merror\x1B[39m: commit message's subject contains Jira tickets\x1B[m\n".format(line=1, col=description.start + 1 + jira_tickets[0], commit=commit)
            error += message.full_subject + '\n'
            error += '\x1B[32m'
            cur = -description.start
            for pos in jira_tickets:
                error += ' ' * (pos - cur) + '^'
                cur = pos + 1
            error += '\x1B[39m'
            errors.append(error)

        # Disallow ending the description with punctuation
        if re.match(r'.*[.!?,]$', description.text):
            error = f"\x1B[1m{commit}:1:{len(message.full_subject)}: \x1B[31merror\x1B[39m: commit message's subject ends with punctuation\x1B[m\n"
            error += message.full_subject + '\n'
            error += ' ' * (len(message.full_subject) - 1) + '\x1B[32m^\x1B[39m'
            errors.append(error)

        blacklist_start_words = (
                'added',
                'adds',
                'adding'
                'applied',
                'applies',
                'applying',
                'edited',
                'edits',
                'editing',
                'expanded',
                'expands',
                'expanding',
                'fixed',
                'fixes',
                'fixing',
                'removed',
                'removes',
                'removing',
                'renamed',
                'renames',
                'renaming',
                'deleted',
                'deletes',
                'deleting',
                'updated',
                'updates',
                'updating',
                'ensured',
                'ensures',
                'ensuring',
                'resolved',
                'resolves',
                'resolving',
                'verified',
                'verifies',
                'verifying',

                # repeating the tag is frowned upon as well
                type_tag.text,
            )
        blacklisted = extract_match_group(re.match(r'^(?:' + '|'.join(re.escape(w) for w in blacklist_start_words) + r')\b', description.text, flags=re.IGNORECASE), 0, description.start)
        if blacklisted:
            error = f"\x1B[1m{commit}:1:{blacklisted.start + 1}: \x1B[31merror\x1B[39m: commit message's description contains blacklisted word or repeats type tag\x1B[m\n"
            error += message.full_subject + '\n'
            error += blacklisted.start * ' ' + '\x1B[32m^' * (blacklisted.end - blacklisted.start) + '\x1B[39m\n'
            error += f"\x1B[1m{commit}:1:{blacklisted.start + 1}: \x1B[30mnote\x1B[39m: prefer using the imperative for verbs\x1B[m"
            errors.append(error)

    if len(message.subject) > 80:
        error = f"\x1B[1m{commit}:1:{81 + message.subject_start}: \x1B[31merror\x1B[39m: commit message's subject exceeds line length of 80 by {len(message.subject) - 80} characters\x1B[m\n"
        error += message.full_subject + '\n'
        error += ' ' * 79 + '\x1B[32m^' + '~' * (len(message.full_subject) - 80) + '\x1B[39m'
        errors.append(error)

    if len(message.lines) > 1 and message.lines[1]:
        error = f"\x1B[1m{commit}:2:1: \x1B[31merror\x1B[39m: commit message subject and body are not separated by an empty line\x1B[m\n"
        error += message.lines[1] + '\n'
        error += '\x1B[31m' + '~' * len(message.lines[1]) + '\x1B[39m'
        errors.append(error)

    # 8. Breaking changes MUST be indicated at the very beginning of the footer or body section of a commit. A breaking
    #    change MUST consist of the uppercase text BREAKING CHANGE, followed by a colon and a space.
    for paraidx, paragraph in enumerate(message.paragraphs):
        lineno = message.paragraph_line(paraidx)
        for m in re.finditer(r'\bBREAKING(\s+)CHANGE\b(\s*)(:?)(\s*)(\S?)', paragraph):
            if m.start() == 0:
                if paragraph[:m.end(4)] != 'BREAKING CHANGE: ' or not m.group(m.lastindex):
                    line_end = paragraph.find('\n')
                    error = f"\x1B[1m{commit}:{lineno + 1}:1: \x1B[31merror\x1B[39m: breaking changes should start with _exactly_ 'BREAKING CHANGE: ' and be followed by text immediately\x1B[m\n"
                    error += paragraph[:line_end] + '\n'
                    error += '\x1B[32m'
                    cur = 0
                    for group, expect in zip(range(1, m.lastindex + 1), (' ', '', ':', ' ')):
                        if m.group(group) != expect:
                            error += ' ' * (m.start(group) - cur)
                            error += '^' * len(m.group(group))
                            cur = m.end(group)
                    # 9. A description MUST be provided after the BREAKING CHANGE:, describing what has changed about the
                    #    API, e.g., BREAKING CHANGE: environment variables now take precedence over config files.
                    if not m.group(m.lastindex):
                        error += ' ' * (m.start(m.lastindex) - cur)
                        error += '^'
                        cur = m.start(m.lastindex) + 1
                    error += '\x1B[39m'
                    errors.append(error)
            else:
                line_start = paragraph.rfind('\n', 0, m.start()) + 1
                line_end = paragraph.find('\n', m.start(2))
                line = lineno + paragraph[:line_start + 1].count('\n')
                start = m.start() - line_start
                error = f"\x1B[1m{commit}:{line + 1}:{start + 1}: \x1B[31merror\x1B[39m: body contains 'BREAKING CHANGE' at other location than start of paragraph\x1B[m\n"
                error += paragraph[line_start:line_end] + '\n'
                error += '\x1B[32m' + ' ' * start
                error += ''.join('\n' if c == '\n' else '^' for c in paragraph[m.start():m.start(2)])
                error += '\x1B[39m'
                errors.append(error)

        complain_about_review_refs(paragraph, lineno=lineno)


    for error in errors:
        print(error, file=sys.stderr)
    return (1 if errors else 0)

if __name__ == "__main__":
    sys.exit(main())
