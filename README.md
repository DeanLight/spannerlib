![Tests](https://github.com/DeanLight/spanner_workbench/actions/workflows/regression_testing.yml/badge.svg)

The spanner workbench is an interpreter and a REPL system for spanner-like languages. Our goal in developing the spanner workbench is twofold:

* First and foremost, to allow students learning about spanner languages an easy to use system to play around with the languages.
* A later goal is to provide an easily modifiable framework that allows researchers to easily test and deploy new algorithms and optimizations to spanner languages.

## Installation

### Unix
To download and install RGXLog run the following commands in your terminal:

```bash
TODO update
git clone https://github.com/DeanLight/spanner_workbench
cd spanner_workbench

pip install -r requirements.txt
pip install -e src/rgxlog-interpreter 
```

download corenlp to
`spanner_workbench/src/rgxlog-interpreter/src/rgxlog/stdlib`

from [this link](https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl)

```bash
# verify everything worked
# first time might take a couple of minutes since run time assets are being configured
pytest ./src/rgxlog-interpreter/tests -s

```

### docker

```bash
git clone https://github.com/DeanLight/spanner_workbench
cd spanner_workbench
```

download corenlp to
`spanner_workbench/src/rgxlog-interpreter/src/rgxlog/stdlib`

from [this link](https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl)

```bash
docker build . -t spanner_workbench_image

# on windows, change `pwd to current working directory`
# to get a bash terminal to the container
docker run --name swc --rm -it \
  -v `pwd`:/spanner_workbench:Z \
  spanner_workbench_image bash

# to run an interactive notebook on host port 8891
docker run --name swc --rm -it \
  -v `pwd`:/spanner_workbench:Z \
  -p8891:8888 \
  spanner_workbench_image jupyter notebook --no-browser --allow-root

#Verify tests inside the container
pytest /spanner_workbench/src/rgxlog-interpreter/tests -s

```

## Example

```python
session = Session()

commands = '''
        new parent(str, str)
        parent("Liam", "Noah")
        parent("Noah", "Oliver")
        
        ancestor(X,Y) <- parent(X,Y)
        ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

        ?ancestor(Ancestor, Descendant)
        '''

session.run_commands(commands)
```

```text
printing results for query 'ancestor(Ancestor, Descendant)':
  Ancestor  |  Descendant
------------+--------------
    Liam    |     Noah
    Liam    |    Oliver
    Noah    |    Oliver
```

## Getting Started
[Introduction](https://github.com/DeanLight/spanner_workbench/blob/a7c61f015361c836952740dd0b6500401a9cccaf/tutorials/introduction.md)

[Advanced usage](https://github.com/DeanLight/spanner_workbench/blob/a7c61f015361c836952740dd0b6500401a9cccaf/tutorials/Advanced%20usage.md)

## Resources

### Sources of inspiration

* [Logicblox repl](https://developer.logicblox.com/content/docs4/tutorial/repl/section/split.html)

* [Logicblox manual](https://developer.logicblox.com/content/docs4/core-reference/html/index.html)

* LogiQL is the language implemented in logicblox and is a Dialect of [Datalog](https://en.wikipedia.org/wiki/Datalog)

* Datalog in turn is derived by [Prolog](https://en.wikipedia.org/wiki/Prolog)

* Here is a [python implementation of a Datalog library](https://github.com/pcarbonn/pyDatalog)

### Resources about building interpreters

* [A 5 minute look at building your own language](https://www.freecodecamp.org/news/the-programming-language-pipeline-91d3f449c919/)

* [Introduction to grammars and Automata](https://www.tutorialspoint.com/automata_theory/introduction_to_grammars.htm)

* [Compiler design tutorials](https://www.geeksforgeeks.org/compiler-design-tutorials/)

### Relevant papers

* [spannerlog](papers/spanner_log_Y_nachshon.pdf)
* [Recursive RGXLog](papers/Recures_programs_for_document_spanners.pdf)
