
#### Python version
3.9.10

#### Build Dependencies
- [Python Version Management](https://github.com/pyenv/pyenv) (pyenv)
- The [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_install)
- The [Poetry](https://python-poetry.org/docs/) build tool
- Python [Pre-commit](https://pre-commit.com/).  

#### Initialize
- Install Pyenv (either option):
  - `brew update && brew install pyenv`
  - `git clone https://github.com/pyenv/pyenv.git ~/.pyenv`
- Install Python version: `pyenv install 3.9.10`
- Clone Repository: `git clone git@github.com:aquia-inc/cyclonedx-python.git`
- Cd into repo: `cd cyclonedx-python`
- Install Pre-Commit: `pip install pre-commit`
- Python Dependencies: `poetry install`
- pre-commit hooks: `pre-commit install`

#### Build and Deploy
##### `poetry run build`
Uses Poetry to build the python project into a single artifact

##### `poetry run package`
Re-Packages the project and all dependencies into a zip file compatible with AWS Lambda

##### `poetry run deploy`
Deploys the zip file to AWS Lambda using AWS CDK.