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

"""Configuration tests"""

import pytest

from commisery.config import DEFAULT_ACCEPTED_TAGS, Configuration


def test_default_configuration():
    """Validate default ignore list"""
    config = Configuration()

    assert config.max_subject_length == 80
    assert config.tags == DEFAULT_ACCEPTED_TAGS


def test_configuration_from_valid_yaml(tmp_path):
    """Validates initialization using valid yaml format"""
    config_path = tmp_path / ".commisery.yml"
    config_path.write_text(
        """\
max-subject-length: 120
tags:
  chore: This is a chore! snooooore!
  docs: Who needs documentation anyways?
"""
    )

    config = Configuration.from_yaml(config_path)
    assert config.max_subject_length == 120
    assert list(config.tags.keys()) == ["chore", "docs", "fix", "feat"]


def test_configuration_from_invalid_yaml(tmp_path):
    """Validates initialization using invalid yaml format"""
    config_path = tmp_path / ".commisery.yml"

    # Incorrect file format
    config_path.write_text("& This is plain text")
    with pytest.raises(Exception):
        Configuration.from_yaml(config_path)

    # Incorrect key
    config_path.write_text("wrong-key: awesome value")
    with pytest.raises(TypeError):
        Configuration.from_yaml(config_path)

    # Incorrect type for 'max-subject-length:'
    config_path.write_text("max-subject-length: {wrong: type}")
    with pytest.raises(TypeError):
        Configuration.from_yaml(config_path)

    # Incorrect type for 'tags:'
    config_path.write_text("tags: 42")
    with pytest.raises(TypeError):
        Configuration.from_yaml(config_path)

    # Incorrect yaml layout
    config_path.write_text("- unexpected")
    with pytest.raises(TypeError):
        Configuration.from_yaml(config_path)


def test_configuration_from_missing_yaml(tmp_path):
    """Validates incorrect file path resulting in default Configuration object"""
    assert Configuration.from_yaml(tmp_path / "does-not-exist.yml") == Configuration()
