from glob import glob
from os.path import basename
from os.path import splitext
from typing import Dict, no_type_check

import setuptools
from setuptools.command.develop import develop
from setuptools.command.install import install


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    @no_type_check
    def run(self) -> None:
        develop.run(self)


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self) -> None:
        install.run(self)


with open("README.md", "r") as fh:
    long_description = fh.read()

cmdclass_dict: Dict = {
    'develop': PostDevelopCommand,
    'install': PostInstallCommand,
}

setuptools.setup(
    name="rgxlog",
    version="0.0.22",
    author="Example Author",
    author_email="author@example.com",
    description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DeanLight/spanner_workbench",
    packages=setuptools.find_packages('src'),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    package_data={'': ['grammar.lark']},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    cmdclass=cmdclass_dict,
    python_requires='>=3.8',
    install_requires=[
        'lark-parser',
        'networkx',
        'docopt',
        'tabulate',
        'pandas',
        'jsonpath-ng',
        'psutil',
        'install-jdk',
        'spanner-nlp>=0.0.6',
        'Jinja2'
    ],
    dependency_links=[
    ]

)
# python3 setup.py sdist bdist_wheel
# twine upload --repository testpypi dist/*
