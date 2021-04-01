import setuptools
from setuptools.command.develop import develop
from setuptools.command.install import install

from glob import glob
from os.path import basename
from os.path import splitext

import sys
from subprocess import check_output


class PostDevelopCommand(develop):
    """Post-installation for development mode."""

    def run(self):
        develop.run(self)
        check_output(f"{sys.executable} -m spacy download en_core_web_sm", shell=True)


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)
        check_output(f"{sys.executable} -m spacy download en_core_web_sm", shell=True)


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="test-rgxlog-interpreter",
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
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    },
    python_requires='==3.8.*',
    install_requires=[

        'lark-parser',
        'networkx',
        'docopt',
        'tabulate',
        'pyDatalog',
        'spacy'
    ],
    dependency_links=[
    ]

)
# python3 setup.py sdist bdist_wheel
# twine upload --repository testpypi dist/*
