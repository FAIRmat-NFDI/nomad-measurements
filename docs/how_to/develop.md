# How to Contribute to the NOMAD-measurements Plugin

The **NOMAD-measurements** is a community-driven effort aimed at providing shared data schemas and parsers for measurement data in materials science. We encourage contributions from all users to help enhance and expand the plugin, making it more robust and broadly applicable. If you have any questions or need assistance, feel free to [contact us](../contact.md) — we’re here to help you get involved!

Here’s how you can contribute:

## 1. Setting up a development environment

To make code contributions to this package, you need to setup a local development environment. It starts with 
[cloning](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository)
this repo in a local folder. 
Create a fresh Python environment and install the package in 
[editable](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs)
 mode (with `-e` flag) with its
`dev` dependencies. `pytest` package is installed as a part of the `dev` dependencies.
To run the tests locally, you can simply run `pytest` in the topmost folder of the repo.

```sh
git clone git@github.com:FAIRmat-NFDI/nomad-measurements.git
cd nomad-measurements

python3.11 -m venv .pyenv
source .pyenv/bin/activate
pip install -e .[dev] --index-url https://gitlab.mpcdf.mpg.de/api/v4/projects/2187/packages/pypi/simple
pytest
```

## 2. Branching model

`nomad-measurements` follows the same branching model as pynxtools and the core NOMAD packages.

| Branch | Role |
|---|---|
| `develop` | Default branch. All regular development PRs target this branch. |
| `main` | Released versions only. Only `release/*` branches are merged here, so its history is the release history. |
| `release/vX.Y.Z` | Temporary release branch, created from `develop` and merged into `main`. The version may carry a pre-release suffix, e.g. `release/vX.Y.Z-beta` or `release/vX.Y.Z-rc1`. |

| Activity | Branch |
|---|---|
| Feature development | `develop` |
| PR review and integration | `develop` |
| Selecting changes for a release | `release/vX.Y.Z` |
| Release-specific bug fixes | `release/vX.Y.Z` |
| Published release history | `main` |
| Porting release fixes back to ongoing development | Merge `release/vX.Y.Z` back into `develop` |

The `Check if source is release/*` workflow
([`.github/workflows/check-source-is-release.yml`](https://github.com/FAIRmat-NFDI/nomad-measurements/blob/develop/.github/workflows/check-source-is-release.yml))
allows PRs into `main` only from `release/*` branches. PRs from any other branch, **including `develop`**,
fail this check. It is enforced as a required status check in the branch protection rule for `main`.

### Release workflow

1. Create the release branch from `develop`:

    ```console
    git switch develop && git pull
    git switch -c release/vX.Y.Z
    git push -u origin release/vX.Y.Z
    ```

2. Commit only release-specific changes on this branch (version bumps, changelog, last-minute bug fixes).
   New features keep going into `develop`.
3. Bump `version` in `CITATION.cff` to `X.Y.Z`, including any pre-release suffix (e.g. `1.4.0-rc1` for the tag `v1.4.0-rc1`).
   The publish workflow fails if it differs from the tag.
4. Open a PR from `release/vX.Y.Z` into `main`. Do not merge yet!
5. Create a GitHub release with the tag `vX.Y.Z` and select `release/vX.Y.Z` as its target branch. The publish workflow refuses to upload to PyPI if the release does not target `release/vX.Y.Z`
   or if the tagged commit is not on that branch.
6. Once CI passes and the release is published to PyPI, merge the PR.
7. If you fixed anything directly on the release branch, open a PR from `release/vX.Y.Z` into `develop` so the fixes are not lost in ongoing development.
8. Delete the `release/vX.Y.Z` branch.

## 3. Extract General Components from Your Custom Schema

If you have developed custom schemas for your own lab or project, consider extracting the generalizable aspects and contributing them to the community plugin. Look for data structures, methods, or components that are not specific to your setup but could benefit the wider community. By sharing these, you help build a richer, more comprehensive plugin that everyone can use.

## 4. Test in Your Own Plugin

Before submitting contributions, it’s important to test your changes in your own NOMAD plugin environment. This ensures that your extracted schema or code functions as expected and aligns with the overall plugin structure. Testing locally also helps identify potential conflicts or improvements before making a broader contribution.

## 5. Open an Issue

If you have suggestions, questions, or encounter any issues while using or developing the plugin, feel free to open an issue on the plugin’s GitHub repository. This helps maintainers and other contributors track potential improvements or areas of concern. Be as detailed as possible, providing relevant context and, if applicable, examples of the issue you're encountering.

## 6. Create a Pull Request

Once you’ve tested your contribution and are confident it benefits the community, create a 
[pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
against `develop` — never against `main`, which only accepts `release/*` branches (see
[Branching model](#2-branching-model) above).
In your PR, clearly describe what changes you are proposing and why they are necessary. If you’re contributing general components extracted from your custom schema, explain how they can be applied broadly across different use cases. Be sure to follow the repository's contribution guidelines and reference any related issues if applicable.

By contributing to this plugin, you are helping build a more cohesive and interoperable materials science data ecosystem. We appreciate your input and collaboration!

