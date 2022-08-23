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
from typing import Any, Mapping
import yaml


@dataclass
class TagConfig:
    """Conventional Commit Tag configuration"""

    description: str
    bump: bool = False

    @classmethod
    def from_data(cls, data: Any):
        """Initiate Tag Configuration from data entry"""
        if isinstance(data, str):
            return cls(description=data)

        if not isinstance(data, dict):
            raise TypeError(
                f"Got an unexpected type '{type(data).__name__}' for 'tags', expected '{dict.__name__}'"
            )

        _bump = data.get("bump", False)

        if not isinstance(_bump, bool):
            raise TypeError(
                f"Got an unexpected type '{type(_bump).__name__}' for 'bump', expected '{bool.__name__}'"
            )

        return cls(**data)

    def __repr__(self):
        if not self.bump:
            return self.description

        return f"{self.description} (PATCH)"


DEFAULT_CONFIGURATION_FILE = ".commisery.yml"
DEFAULT_ACCEPTED_TAGS = {
    "fix": TagConfig(description="Patches a bug in your codebase", bump=True),
    "feat": TagConfig(description="Introduces a new feature to the codebase"),
    "build": TagConfig(description="Changes towards the build system"),
    "chore": TagConfig(description="General maintenance changes to the codebase"),
    "ci": TagConfig(description="Changes related to your CI configuration"),
    "docs": TagConfig(
        description="Documentation changes (not part of the public API)",
    ),
    "perf": TagConfig(description="Performance improvements"),
    "refactor": TagConfig(
        description="Refactoring the code base (no behaviorial changes)"
    ),
    "revert": TagConfig(description="Reverts previous change(s) from your codebase"),
    "style": TagConfig(description="Coding style improvements"),
    "test": TagConfig(description="Updates tests"),
    "improvement": TagConfig(
        description="Introduces improvements to the code quality of the codebase"
    ),
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
    rules: Mapping = field(
        default_factory=lambda: get_default_rules()  # pylint: disable=W0108
    )

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
        tags.setdefault(
            "fix", TagConfig(description="Patches a bug in your codebase", bump=True)
        )
        tags.setdefault(
            "feat", TagConfig(description="Introduces a new feature to the codebase")
        )
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
                raise TypeError(
                    f"'{config_path}' got an unexpected keyword type for the root"
                )

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

            data["_tags"] = {}
            for key, value in data.pop("tags", {}).items():
                data["_tags"].setdefault(key, TagConfig.from_data(value))

            # Default tags in case none are specified in the configuration file
            if not data["_tags"]:
                data["_tags"] = DEFAULT_ACCEPTED_TAGS

            return cls(**{key.replace("-", "_"): value for key, value in data.items()})
