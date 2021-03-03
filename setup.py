# Copyright (c) 2018 - 2021 TomTom N.V.
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

from setuptools import setup
import re

with open('README.md', encoding='UTF-8') as fh:
    long_description = fh.read()

# Extract first paragraph
description = re.sub(r'^\s*(?:#+[^\n]*\s*)*', r'', long_description, count=1, flags=re.DOTALL|re.MULTILINE)
description = re.sub(r'\n\n.*', r'', description, flags=re.DOTALL|re.MULTILINE)
# Eliminate link annotation
description = re.sub(r'\[([^\]]+)\]', r'\1', description)
# Convert line breaks into spaces
description = description.replace('\n', ' ')

setup(
    name='commisery',
    author='TomTom N.V.',
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=('commisery','commisery.cli'),
    py_modules=('commisery',),
    python_requires='>=3.6.5',
    install_requires=(
      'click>=7.1.2,<9',
      'click-log',
      'GitPython>=3,<4',
      'regex',
      'stemming>=1,<2',
    ),
    setup_requires=(
      'pytest-runner',
      'setuptools_scm',
      'setuptools_scm_git_archive',
    ),
    tests_require=(
      'pytest',
    ),
    extras_require={
      'github': [
        'PyGithub>=1.53,<2',
      ],
    },
    use_scm_version={"relative_to": __file__},
    entry_points={
      'console_scripts': [
        'commisery-verify-msg = commisery.cli:main',
        'commisery-verify-github-pullrequest = commisery.github:main [github]',
      ],
      'hopic.plugins.yaml': [
        'commisery = commisery.hopic_template:commisery',
      ],
    },
    zip_safe=True,
    url='https://github.com/tomtom-international/commisery',
    project_urls={
      'Source Code': 'https://github.com/tomtom-international/commisery',
    },
    classifiers=(
      'License :: OSI Approved :: Apache Software License',
    ),
    license='Apache License 2.0',
    license_file='LICENSE',
)
