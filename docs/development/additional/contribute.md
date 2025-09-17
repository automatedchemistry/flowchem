# Contribute to flowchem
There are many ways of contributing to flowchem: if you are using it and have suggestions or bugs report them in the
issue tracker on GitHub, if you find the documentation not clear, propose a change and if you want to add support for
new device, that would be awesome as well!
% part of this page is based on the numpy project one
% See also https://rdflib.readthedocs.io/en/stable/developers.html
% And https://diataxis.fr/how-to-guides/

## Repository structure
The repository is structured as follows:
* `docs` - documentation
* `examples` - example of use
* `src` - source code
* `tests` - test files (pytest)
We follow the "src-layout", read [this article](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#src-layout) for more details.

Moreover, the source code in the `flowchem` packages is organized in:
* `components` - the abstract components representing specific device capabilities (e.g. pumping).
* `devices` - containing the code to control the different devices, sorted by manufacturer
* `server` - the modules related to configuration parsing and API server initialization.
* `utils` - various helper functions

% ## Community
% We aim at creating a community around flowchem, by incentive the participation from a diverse group of contributors.
% Please read the [Contributor Covenant](https://www.contributor-covenant.org/) we adopted as Code of Conduct for guidance
% on how to interact with others in a way that makes the community thrive.

## Development process
1. If you are a first-time contributor:

   * Go to [flowchem gitHub repository](https://github.com/cambiegroup/flowchem) and click the “fork” button to create your own copy of the project.

   * Clone the project to your local computer: `git clone https://github.com/your-username/flowchem.git`

   * Change the directory: `cd flowchem`

   * Add the upstream repository: `git remote add upstream https://github.com/cambiegroup/flowchem.git`

   * Now, `git remote -v` will show two remote repositories named:
     * `upstream` which refers to the `flowchem` repository
     * `origin` which refers to your personal fork

2. Develop your contribution:

   * Pull the latest changes from upstream:
     * `git checkout main`
     * `git pull upstream main`

   * Create a branch for the feature you want to work on. Since the branch name will appear in the merge message, use a
     sensible name.
     For example, if you intend to add support for a new device type, called ExtendableEar a good candidate
     could be ‘add-extendable-ear-support’: `git checkout -b add-extendible-ear-support`

   * Commit locally as you progress (`git add` and `git commit`).
     Use a properly formatted commit message, and ideally write tests that fail before your change and pass afterward.
     If possible, include docstrings following [Google docstring standard](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html).

3. To submit your contribution:

   * Push your changes back to your fork on GitHub: `git push origin add-extendible-ear-support`.

   * Go to GitHub. The new branch will show up with a green Pull Request button.
     Make sure the title and message are clear, concise, and self-explanatory. Then click the button to submit it.

4. Review process:

   * Reviewers (the other developers and interested community members) will write inline and/or general comments on your
     Pull Request (PR) to help you improve its implementation, documentation and style.
     The review is meant as friendly conversation from which we all learn and the overall code quality benefits.
     Please do not let the review discourage you from contributing: its only aim is to improve the quality of project, not to criticize: we are very grateful for your contribution!

   * To update your PR, make your changes on your local repository, commit, run tests, and only if they succeed push to your fork.
     As soon as those changes are pushed up (to the same branch as before) the PR will update automatically.
     If you have no idea how to fix the test failures, you may push your changes anyway and ask for help in a PR comment.

   * A Github-action is triggered after each PR update to build the code, run unit tests, measure code coverage and
     check coding style of your branch.
     The CI tests must pass before your PR can be merged.
     If CI fails, you can find out why by clicking on the red cross icon and inspecting the test log.
     (To speed up this cycle you can also test your work locally before committing.)

   * After review, a PR will be merged in the main branch and will be part of the next release.

5. Document changes

   * If your change introduces support for a new device make sure to add the relevant documentation for it.
     As conceptual framework for our documentation we are inspired by [Diátaxis](https://diataxis.fr).

### Guidelines

* All code should be documented with docstrings (in Google format) and comments where appropriate.
* Possibly, all new code should have tests.
* We use [black](https://github.com/psf/black) as code formatter not to waste time discussing code style.
* You can install [pre-commit](https://pre-commit.com/) to run black and other linters as part of the pre-commit hooks.
  See our `.pre-commit-config.yml` for details.
%  The use of linter and import re-ordering is aimed at reducing diff size and merge conflicts in pull request.

### Testing with `pytest`
To run the tests `pytest` and some pytest plugins are needed.
To install them run:
```shell
pip install flowchem[test]
```
If possible, new code should be accompanied by relevant unit tests, see more details in [testing](testing.md).

## Documentation
The documentation is written in [Markdown](https://www.markdownguide.org/) and a new version of it is automatically
build after each commit in the `main` and `docs` branches on
[readthedocs.com](https://readthedocs.org/projects/flowchem/).

It is also possible to build the documentation locally.
Install the packages required (sphynx, myst-parser and more) by running:
```shell
pip install flowchem[docs]
```
Then, from the `./docs` folder:
```shell
make html
```
This will generate html files in the `_build/html` subdirectory.