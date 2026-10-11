# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

This custom component is based on [samsungehs template](https://github.com/pantherale0/samsungehs).

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml)
file.

## Release process

[Release Please](https://github.com/googleapis/release-please-action) runs on
pushes to `main` and can also be run manually from the Actions tab on `main`.
It maintains a release pull request with a generated `CHANGELOG.md`, updates
`version.txt` and `.release-please-manifest.json`, and updates the integration's
`version` in `custom_components/samsungehs/manifest.json`.
Merging that pull request causes the next workflow run to create a `vX.Y.Z` tag
and a GitHub release with release notes. HACS installs the integration from the
tagged repository, so no separate ZIP asset is required.

Use Conventional Commit messages for changes merged into `main`:

- `fix: correct quiet mode state` creates a patch release.
- `feat: add a configuration register` creates a minor release.
- `feat!: change configuration format` creates a major release. Explain the
  breaking change in the commit body.

All new commits and PR titles must follow
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).
The **Conventional commits** workflow checks the PR title and each new
non-merge commit on PRs and pushes to `main`. It also checks body separation
and breaking-change footer syntax. Generated Git merge commits are exempt;
their constituent commits are checked. Existing history is not revalidated.
Run the same checks locally with:

```bash
python scripts/check_commits.py --range origin/main..HEAD
python scripts/check_commits.py --message-file /tmp/commit-message.txt
```

When squash merging, use a Conventional Commit message as the final squash
commit title. Documentation and maintenance commits such as `docs:` and `chore:`
do not create a release on their own. Review and merge the generated release PR
when the changes are ready to publish. Let the automation manage version files
and release tags.

### Repository setup

Enable GitHub Actions and **Allow GitHub Actions to create and approve pull
requests** under **Settings > Actions > General**. The workflow uses the built-in
`GITHUB_TOKEN` by default.

Add **Conventional commits** as a required status check in the branch protection
rule or ruleset for `main` to block merging PRs that fail it. Configure squash
merges to use the PR title and preserve that title in the final commit message.

Before making the check required, configure the `RELEASE_PLEASE_TOKEN` Actions
secret with a personal access token that can write repository contents, issues,
and pull requests. The release workflow uses this token when present, so
generated release PRs trigger the commit check. GitHub does not trigger other
Actions workflows for PRs or tags created with `GITHUB_TOKEN`; using only that
token would leave a required check pending on release PRs. A GitHub App token
can also be used if the workflow generates it before invoking Release Please.

The automation starts from version `1.0.0` at commit
`ab95f991d6ee2a5cf00b03fae8242cc5b0c08a17`. Earlier changes are treated as the
baseline and are excluded from the first generated changelog.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
