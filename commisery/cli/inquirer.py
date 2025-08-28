#!/usr/bin/env python3

# Copyright (c) 2020 - 2022 TomTom N.V. (https://tomtom.com)
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

"""Helper methods for inquirer"""

from dataclasses import dataclass, field
from typing import Optional, Sequence

import inquirer


@dataclass
class Choice:
    """List of Choices"""

    name: str
    message: str
    type: str = "list"
    choices: Sequence[str] = field(default_factory=list)
    default: Optional[str] = None


@dataclass
class Input:
    """Text Input"""

    name: str
    message: str
    type: str = "input"


@dataclass
class Editor:
    """Multiline editor"""

    name: str
    message: str
    type: str = "editor"


@dataclass
class Confirm:
    """Confirmation dialog"""

    name: str
    message: str
    default: bool
    type: str = "confirm"


def prompt(questions) -> dict:
    """Prompt questions on the CLI"""
    # Convert our dataclass questions to inquirer question objects
    inquirer_questions = []

    for question in questions:
        if question.type == "list":
            inquirer_questions.append(
                inquirer.List(
                    name=question.name,
                    message=question.message,
                    choices=question.choices,
                    default=question.default,
                )
            )
        elif question.type == "input":
            inquirer_questions.append(
                inquirer.Text(name=question.name, message=question.message)
            )
        elif question.type == "editor":
            inquirer_questions.append(
                inquirer.Editor(name=question.name, message=question.message)
            )
        elif question.type == "confirm":
            inquirer_questions.append(
                inquirer.Confirm(
                    name=question.name,
                    message=question.message,
                    default=question.default,
                )
            )

    return inquirer.prompt(inquirer_questions)
