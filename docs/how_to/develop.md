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

## 2. Extract General Components from Your Custom Schema

If you have developed custom schemas for your own lab or project, consider extracting the generalizable aspects and contributing them to the community plugin. Look for data structures, methods, or components that are not specific to your setup but could benefit the wider community. By sharing these, you help build a richer, more comprehensive plugin that everyone can use.

## 3. Test in Your Own Plugin

Before submitting contributions, it’s important to test your changes in your own NOMAD plugin environment. This ensures that your extracted schema or code functions as expected and aligns with the overall plugin structure. Testing locally also helps identify potential conflicts or improvements before making a broader contribution.

## 4. Open an Issue

If you have suggestions, questions, or encounter any issues while using or developing the plugin, feel free to open an issue on the plugin’s GitHub repository. This helps maintainers and other contributors track potential improvements or areas of concern. Be as detailed as possible, providing relevant context and, if applicable, examples of the issue you're encountering.

## 5. Create a Pull Request

Once you’ve tested your contribution and are confident it benefits the community, create a 
[pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
(PR). 
In your PR, clearly describe what changes you are proposing and why they are necessary. If you’re contributing general components extracted from your custom schema, explain how they can be applied broadly across different use cases. Be sure to follow the repository's contribution guidelines and reference any related issues if applicable.

By contributing to this plugin, you are helping build a more cohesive and interoperable materials science data ecosystem. We appreciate your input and collaboration!

