import setuptools
from glob import glob
from os.path import basename
from os.path import splitext

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="my-pkg-coldfear-rgxlog-interpreter",
    version="0.0.11",
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
    python_requires='>=3.8*',
    install_requires=[
        'lark-parser',
        'networkx',
        'docopt',
        'tabulate',
    ]
)

# python3 -m twine upload --repository testpypi dist/*
# twine upload --repository testpypi dist/*
