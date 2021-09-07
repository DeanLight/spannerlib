The spanner workbench is an interpreter and a REPL system for spanner-like languages. Our goal in developing the spanner workbench is twofold:

* First and foremost, to allow students learning about spanner languages an easy to use system to play around with the languages.
* A later goal is to provide an easily modifiable framework that allows researchers to easily test and deploy new algorithms and optimizations to spanner languages.

## Installation
To download and install RGXLog run the following commands in your terminal:

```bash
git clone https://github.com/DeanLight/spanner_workbench
cd spanner_workbench

pip install src/rgxlog-interpreter 

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

session.run_statements(commands)
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
