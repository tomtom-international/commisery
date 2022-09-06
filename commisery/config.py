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

"""Configuration"""

from inspect import getmembers, isfunction
import os

from dataclasses import dataclass, field
import re
import sys
from typing import Mapping
import yaml

DEFAULT_CONFIGURATION_FILE = ".commisery.yml"
DEFAULT_ACCEPTED_TAGS = {
    "fix": "Patches a bug in your codebase",
    "feat": "Introduces a new feature to the codebase",
    "build": "Changes towards the build system",
    "chore": "General maintenance changes to the codebase",
    "ci": "Changes related to your CI configuration",
    "docs": "Documentation changes (not part of the public API)",
    "perf": "Performance improvements",
    "refactor": "Refactoring the code base (no behaviorial changes)",
    "revert": "Reverts previous change(s) from your codebase",
    "style": "Coding style improvements",
    "test": "Updates tests",
    "improvement": "Introduces improvements to the code quality of the codebase",
}


def get_default_rules():
    """Determine the default Commit Message ruleset"""
    rule_re = re.compile(r"(?P<rule>C[0-9]{3})_.*")

    return {
        rule_re.match(name).group("rule"): {
            "description": obj.__doc__,
            "obj": obj,
            "enabled": True,
        }
        for name, obj in getmembers(sys.modules["commisery.rules"], isfunction)
        if rule_re.match(name)
    }


@dataclass
class Configuration:
    """Configuration"""

    max_subject_length: int = 80
    _tags: Mapping = field(default_factory=lambda: DEFAULT_ACCEPTED_TAGS)
    rules: Mapping = field(default_factory=lambda: get_default_rules())
    silent: bool = False

    def __post_init__(self):
        """Post initializer"""

        # NOTE: Required to use apply the property decorator on construction
        self.tags = self._tags

    @property
    def tags(self):
        """Conventional Commit tag types"""
        return self._tags

    @tags.setter
    def tags(self, tags: Mapping):
        """Sets the provided tag types, while ensuring that fix and feat are always present"""
        tags.setdefault("fix", DEFAULT_ACCEPTED_TAGS["fix"])
        tags.setdefault("feat", DEFAULT_ACCEPTED_TAGS["feat"])
        self._tags = tags

    @classmethod
    def from_yaml(cls, config_path: str):
        """Converts yaml file to class instance"""

        # Default configuration file path.
        if not config_path:
            config_path = DEFAULT_CONFIGURATION_FILE

        # Default settings in case the configuration file does not exist.
        if not os.path.exists(config_path):
            return cls()

        with open(config_path, encoding="utf8") as file:
            data = yaml.safe_load(file)

            if not isinstance(data, dict):
                raise TypeError(f"'{config_path}' got an unexpected keyword type for the root")

            for item, expected in [
                ("max-subject-length", Configuration.max_subject_length),
                (
                    "tags",
                    {},
                ),  # Configuration.tags is not (yet) initialized at this stage due to usage of the `default_factory`
                (
                    "disable",
                    [],
                ),  # Configuration.disable is not (yet) initialized at this stage due to usage of the `default_factory`
            ]:
                value = data.get(item, None)
                if value and not isinstance(value, type(expected)):
                    raise TypeError(
                        f"'{config_path}' got an unexpected type '{type(value).__name__}' for '{item}', expected '{type(expected).__name__}'"
                    )

            data["rules"] = get_default_rules().copy()
            for rule in data.pop("disable", []):
                data["rules"][rule]["enabled"] = False

            data["_tags"] = data.pop("tags", DEFAULT_ACCEPTED_TAGS)
            return cls(**{key.replace("-", "_"): value for key, value in data.items()})
