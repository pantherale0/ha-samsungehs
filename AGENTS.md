# Project rules

## Commit messages and pull requests

Every commit you create must follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>[optional scope][!]: <description>

[optional body]

[optional footers]
```

Use `feat` for new features and `fix` for bug fixes. Use descriptive types such
as `docs`, `ci`, `chore`, `refactor`, or `test` for other work. Prefer lowercase
types. Mark breaking changes with `!` immediately before the colon or an
uppercase `BREAKING CHANGE:` or `BREAKING-CHANGE:` footer with a description.
Separate the header from any body or footers with a blank line.

PR titles must also use this format, and the final squash commit message must
preserve it. Generated Git merge commits are exempt from the automated check;
their constituent commits are checked. Do not rewrite existing history to fix
old messages unless the user asks.

Before creating a commit, validate its proposed message:

```bash
python scripts/check_commits.py --message-file /tmp/commit-message.txt
```

Before submitting a PR, validate its commits and run the validator tests:

```bash
python scripts/check_commits.py --range origin/main..HEAD
python -m unittest discover -s tests -p 'test_check_commits.py'
```

Release Please manages release versions, tags, and the changelog. See
[CONTRIBUTING.md](CONTRIBUTING.md#release-process) for the release workflow.
