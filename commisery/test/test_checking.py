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
import re
import sys

def test_initial_capital(capsys, tmp_path):
    tmp_path /= 'msg.txt'
    with open(tmp_path, 'w', encoding='UTF-8') as f:
        f.write('fix: Change the thingy')

    assert checking.main((None, tmp_path)) != 0

    out, err = capsys.readouterr()
    sys.stdout.write(out)
    sys.stderr.write(err)

    assert out == ''

    txt = re.sub(r'\x1B\[(?:\d+(?:;\d+)*)?m', '', err)
    errors = [line for line in txt.splitlines() if ' error: ' in line]

    assert len(errors) == 1
    assert errors[0].startswith(f"{tmp_path}:1:6: error: ")
    assert re.search(r'\btitle case\b.*\bdescription\b', errors[0])
