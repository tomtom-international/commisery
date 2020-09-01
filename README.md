# Commisery

Commisery is a package to help check whether given commit messages adhere to [Conventional Commits].
Specifically it checks the syntax and some small aspects of the semantics.

The purpose of this is several fold:

1. Achieving a common layout for commit messages in order to help humans more quickly extract useful information from them.
2. Making these messages partially machine processable in order to classify changes for proper version management.
3. Identifying a subset of common mistakes that render a message useless to your future self or colleagues.

The latter goal usually requires your commit messages to answer these questions:
* What: a short summary of _what_ you changed in the subject line.
* Why: what the intended outcome of the change is (arguably the _most_ important piece of information that should go into a message).
* How: if multiple approaches for achieving your goal were available, you also want to explain _why_ you chose the used implementation strategy.
    - Note that you should not explain how your change achieves your goal in your commit message.
      That should be obvious from the code itself.
      If you cannot achieve that clarity with the used programming language, use comments within the code instead.
    - The commit message is primarily the place for documenting the _why_.

Unfortunately, checking whether these last questions get answered is also the most difficult to do automatically.
This tool only checks for a few common errors other than syntax errors:
1. Usage of Jira ticket numbers in the subject line.
    - Because the subject line is expensive real estate every character should be most efficiently used to convey meaning to humans.
    - Jira ticket numbers are not equal to the tickets themselves and thus convey very little information.
      These ticket numbers should go in message footers where tools can still extract them for automatic linking.
2. Using non-imperative verb forms (adds, added or adding instead of add) in the subject line.
    - These other forms convey no more meaning but use extra precious characters.
3. Referring to review comments that cannot be found anywhere in the commit history itself.
    - Commit messages should be self-contained.
      Only mentioning that a commit is created in response to a review comment, without mentioning the reasoning of that comment is clearly not self-contained.
    - Whenever your workflow permits it, prefer amending the original commit (or using `--fixup`) instead.
    - If your workflow doesn't permit that, or it seems suboptimal in a given context, describe what, why and how you are changing (as mentioned before).

## Installation

You can install this package with pip as follows:

```sh
pip3 install --user --upgrade commisery
```

You can verify commit messages with the included CLI tool:

```sh
$ commisery-verify-msg 8c3349528888a62382afd056eea058843dfb7690
$ commisery-verify-msg master
$ commisery-verify-msg .git/COMMIT_EDITMSG
$ commisery-verify-msg my-own-message.txt
```

The exit code of that tool will be zero if and only if it found errors in the given commit message.

After that you can use it as a hook in Git to check messages you wrote by creating a `.git/hooks/commit-msg` file with these contents:
```sh
#!/bin/sh
exec commisery-verify-msg "$@"
```

## Hopic

Using it as a check in Hopic can be accomplished with a configuration fragment like this:
```yaml
phases:
  style:
    commit-messages:
      - python3 -m virtualenv --clear venv
      - venv/bin/python -m pip install --upgrade 'commisery>=0,<1'
      # Require each commit message to adhere to our requirements
      - foreach: AUTOSQUASHED_COMMIT
        sh: venv/bin/python venv/bin/commisery-verify-msg ${AUTOSQUASHED_COMMIT}
      # Optional: check the produced merge commit message too (this includes the PR title)
      - venv/bin/python venv/bin/commisery-verify-msg HEAD
```

This exact form can also be used through the `commisery` template:

```yaml
phases:
  style:
    commit-messages: !template "commisery"
```

[Conventional Commits]: https://www.conventionalcommits.org/en/v1.0.0/
