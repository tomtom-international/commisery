..
   Copyright (c) 2020 - 2020 TomTom N.V.
  
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
  
       http://www.apache.org/licenses/LICENSE-2.0
  
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

Hopic Configuration Template
============================

In order to reduce the amount of copy-pasted boiler plate configuration, Commisery provides a template for Hopic.

Commisery will be executed on each commit in your pull requests by this snippet:

.. code-block:: yaml

  phases:
    style:
      commit-messages: !template "commisery"

In case you'd like to enforce a Jira-style ticket to be present in the commits comprising a pull request, provide the `require-ticket` parameter to the template:

.. code-block:: yaml

  phases:
    style:
      commit-messages: !template
        name: commisery
        require-ticket: true
