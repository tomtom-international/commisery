# Copyright (c) 2019 - 2020 TomTom N.V.
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

from collections import OrderedDict
import json
import os
import re
import sys

import pytest

try:
    # Python >= 3.8
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata


try:
    _hopic_version = tuple(
            (int(x) if re.match('^[0-9]+$', x) else x)
            for x in metadata.version('hopic').split('.')
        )
    hopic_cli = [ep for ep in metadata.entry_points()['console_scripts'] if ep.name == 'hopic'][0].load()
    from click.testing import CliRunner
    import git
except metadata.PackageNotFoundError:
    _hopic_version = ()

_git_time = f"{7 * 24 * 3600} +0000"


def run_with_config(config, args, files={}, env=None, cfg_file='hopic-ci-config.yaml'):
    runner = CliRunner(mix_stderr=False, env=env)
    with runner.isolated_filesystem():
        with git.Repo.init() as repo:
            if '/' in cfg_file and not os.path.exists(os.path.dirname(cfg_file)):
                os.makedirs(os.path.dirname(cfg_file))
            with open(cfg_file, 'w') as f:
                f.write(config)
            for fname, content in files.items():
                if '/' in fname and not os.path.exists(os.path.dirname(fname)):
                    os.makedirs(os.path.dirname(fname))
                with open(fname, 'w') as f:
                    f.write(content)
            repo.index.add((cfg_file,) + tuple(files.keys()))
            repo.index.commit(message='Initial commit', author_date=_git_time, commit_date=_git_time)
        if cfg_file != 'hopic-ci-config.yaml':
            args = ('--config', cfg_file) + tuple(args)
        result = runner.invoke(hopic_cli, args)

    if result.stdout_bytes:
        print(result.stdout, end='')
    if result.stderr_bytes:
        print(result.stderr, end='', file=sys.stderr)

    if result.exception is not None and not isinstance(result.exception, SystemExit):
        raise result.exception

    return result


@pytest.mark.skipif(_hopic_version < (1,15), reason="Hopic >= 1.15.0 not available")
def test_commisery_template(capfd):
    result = run_with_config('''\
phases:
  style:
    commit-messages: !template "commisery"
''', ('show-config',))

    assert result.exit_code == 0
    output = json.loads(result.stdout, object_pairs_hook=OrderedDict)
    expanded = output['phases']['style']['commit-messages']
    assert expanded[0]['image'] is None
    commits, head = [e['sh'] for e in expanded]
    assert 'commisery.checking' in commits
    assert head[-2:] == ['commisery.checking', 'HEAD']
