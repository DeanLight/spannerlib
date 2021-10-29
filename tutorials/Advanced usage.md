---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.11.2
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# Advanced Spanner Workbench Introduction


In this tutorial you will learn some advanced features of spanner workbench:
* [rgxlog with native python](#native_python)
* [changing the default magic_session](#changing_session)
* [dymamic rules and queries](#dynmaic_calls)
* [processing query result with python](#query_result_processing)
* [importing relations from dataframes](#import_from_df)
* [ceatring and adding optimization passes](#optimization_passes)


# Using native Python<a class="anchor" id="native_python"></a>


## Default session


When rgxlog is loaded, a default session (`rgxlog.magic_session`) is created behind the scenes. This is the session that %%rgxlog uses.


Using a session manually enables one to dynamically generate queries, facts, and rules

```python
import rgxlog
session = rgxlog.magic_session
```

```python
result = session.run_commands('''
    new uncle(str, str)
    uncle("benjen", "jon")''')
```

```python
for maybe_uncle in ['ned', 'robb', 'benjen']:
    result = session.run_commands(f'?uncle("{maybe_uncle}",Y)')
```

# Changing the session of the magic cells<a class="anchor" id="changing_session"></a>


In cases where you want to work with a custom session, but still make use of the magic system, you can overide the session used by the magic system

```python
import rgxlog  # default session starts here
from rgxlog import Session

another_session=Session()
old_magic_session = rgxlog.magic_session
rgxlog.magic_session = another_session
```

```python
%%rgxlog
# we're now using the new session
new uncle(str, str)
uncle("bob", "greg")
?uncle(X,Y)
```

```python
# back to the old session
rgxlog.magic_session = old_magic_session
%rgxlog uncle("jim", "dwight")
```

```python
print(rgxlog.magic_session._parse_graph)
print(another_session._parse_graph)
```

# Mixing magics with dynamic session calls<a class="anchor" id="dynmaic_calls"></a>


Lets take the GPA example from the introductory tutorial.
What if we want to have multiple rules each looking for GPAs of students in different classes.
We wouldnt want to manually write a rule for every single subject.


We write our data manually. In the future we would be able to import it from csvs/dataframes

```python
%%rgxlog
new lecturer(str, str)
lecturer("walter", "chemistry")
lecturer("linus", "operation_systems")
lecturer("rick", "physics")

new enrolled(str, str)
enrolled("abigail", "chemistry")
enrolled("abigail", "operation_systems")
enrolled("jordan", "chemistry")
enrolled("gale", "operation_systems")
enrolled("howard", "chemistry")
enrolled("howard", "physics")



gpa_str = "abigail 100 jordan 80 gale 79 howard 60"
```

```python
%%rgxlog

gpa(Student,Grade) <- py_rgx_string(gpa_str, "(\w+).*?(\d+)")->(Student, Grade),enrolled(Student,X)

?gpa(X,Y)
```

Now we are going to define the rules using a for loop

```python
subjects = [
    "chemistry",
    "physics",
    "operation_systems",
    "magic",
]

for subject in subjects:
    rule = f"""
    gpa_of_{subject}_students(Student, Grade) <- gpa(Student, Grade), enrolled(Student, "{subject}")
    """
    session.run_commands(rule)
    print(rule)  # we print the rule here to show you what strings are sent to the session
```

As you can see, we can use the dynamically defined rules in a magic cell

```python
%%rgxlog
?gpa_of_operation_systems_students(X,Y)
```

And we can also query dynamically

```python
subjects = [
    "chemistry",
    "physics",
    "operation_systems",
    "magic",
]

for subject in subjects:
    query = f"""
    ?gpa_of_{subject}_students(Student, Grade)
    """
    session.run_commands(query)
```

## Creating Information Extractors Dynamically


sometimes we can save time by creating rgxlog code dynamically:

```python
from rgxlog import magic_session

%rgxlog new sibling(str, str)
%rgxlog new parent(str, str)
%rgxlog parent("jonathan", "george")
%rgxlog parent("george", "joseph")
%rgxlog parent("joseph", "holy")
%rgxlog parent("holy", "jotaro")
%rgxlog sibling("dio", "jonathan")

a = ["parent", "uncle_aunt", "grandparent", "sibling"]
d = {"uncle_aunt": ["sibling", "parent"], "grandparent": ["parent", "parent"], "great_aunt_uncle": ["sibling", "parent", "parent"]}

for key, steps in d.items():
    # add the start of the rule
    result = key + "(A,Z) <- "
    for num, step in enumerate(steps):
        # for every step in the list, add the condition: step(letter, next letter).
        #  the first letter is always `A`, and the last is always `Z`
        curr_letter = chr(num + ord("A"))
        result += step + "(" + curr_letter + ","
        if (num == len(steps) - 1):
            result += "Z)"
        else:
            result += chr(1 + ord(curr_letter)) + "), "
    print("running:", result)
    magic_session.run_commands(result)
    magic_session.run_commands(f"?{key}(X,Y)")
```

# Processing the result of a query in python and using the result in a new query<a class="anchor" id="query_result_processing"></a>


we can add `format_results=True` to `run_statements` to get the output as one of the following:
1. `[]`, if the result is false,
2. `[tuple()]`, if the result if true (the tuple is empty), or
3. `pandas.DataFrame`, otherwise-

```python
results = session.run_commands(f'''
    new friends(str, str, str)
    friends("bob", "greg", "clyde")
    friends("steven", "benny", "horace")
    friends("lenny", "homer", "toby")
    ?friends(X,Y,Z)''', print_results=False, format_results=True)

# now we'll showcase processing the result with native python...
# lets filter our tuples with some predicate:
res = results[0].values.tolist()
filtered = tuple(filter(lambda friends: 'bob' in friends or 'lenny' in friends, res))

# and feed the matching tuples into a new query:
session.run_commands('new buddies(str, str)')

for first, second, _ in filtered:
    session.run_commands(f'buddies("{first}", "{second}")')

result = session.run_commands("?buddies(First, Second)")
```

# Import a relation from a `DataFrame`<a class="anchor" id="import_from_df"></a>


By default, non-boolean query results are saved as a `DataFrame`.
A relation can also be imported from a `DataFrame`, like this:

```python
from pandas import DataFrame

df = DataFrame([["Shrek",42], ["Fiona", 1337]], columns=["name", "number"])
session.import_relation_from_df(df, relation_name="ogres")
%rgxlog ?ogres(X,Y)

```
# Adding Optimization Passes to the Pass Stack<a class="anchor" id="optimization_passes"></a>


## General Passes


Before reading this section, we will briefly explain how passes work.
There are five kinds of passes:
1. **AST transformation passes** - These passes convert the input program into AST.
2. **semantic checks passes** - These passes check the corectness of the program (i.e. one of the passes asserts that all the relations used in the program were registerred before).
3. **AST execution passes** - These passes traverse the AST and covert it to a `parse graph`. In addition they register new relations and handle variables assingments.
4. **term graph passes** - These passes adds rules into the `term graph`.
5. **execution pass** - This pass traverses the `parse graph` and finds queries. Then it computes them using the `term graph`.


## Optimization Passes


There are two kinds of optimization passes:
1. The first one, manipulates rules before they are added to the `term graph`.
2. The second one, manipulates the structure of the `term graph`.

note: It's also possible to optimize the execution function/pass (but we won't discuss it in this tutorial). 
    
In this section, we will implement two simple optimization passes, one of each kind.


## Rule-Manipulation Optimization


Optimizations of  this kind traverse the `parse_graph` and find rules that weren't added to the `term graph`.
Then, they update each rule - by modifying its body relations list.

Here are some examples of possible optimization passes of this kind:
1. An optimization that removes duplicated relations from a rule.
   i.e., the rule `A(X) <- B(X), C(X), B(X)` contains the relation `B(X)` twice.
   The optimization will transform the rule into `A(X) <- B(X), C(X)`.
   
2. An optimization that removes useless relations from a rule.
   i.e., the rule `A(X) <- B(X), C(Y)` contains the useless relation `C(Y)`.
   The optimization will transform the rule into `A(X) <- B(X)`.
   
Below is an implementation of the latter example:


### Optimization Example: Remove Useless Relations


Before jumping into the actual implementation, we will implement it in a psuedo code:
```
1. a. Add the free variables inside the rule head into a relevant_free_variables set.
   b. Mark all relations as useless, except those with no free variables (they are always relevant).
   
2. Find all relations that has at least on free variable inside the relevant_free_variables set.

3. Unmark these relations (since they are relevant).

4. Add all the free variables of the unmarked relations into the relevant_free_variables set.

5. Repet steps 2, 3 and 4 until the set of the marked relations converge.
```
note that this is a fixed point algorithm.

```python
from rgxlog.engine.utils.general_utils import fixed_point
print(fixed_point.__doc__)
```

```python
from rgxlog.engine.utils.general_utils import get_output_free_var_names
print(get_output_free_var_names.__doc__)
```

```python
from rgxlog.engine.utils.general_utils import get_input_free_var_names
print(get_input_free_var_names.__doc__)
```

```python
# first, lets implement the logic that removes useless relations from a rule
def remove_useless_relations(rule):
        """
        Finds redundant relations and removes them from the rule.
        
        @param rule: a rule.
        """
        # step 1.a. Add the free variables inside the rule head into a relevant_free_variables set.
        relevant_free_vars = set(rule.head_relation.get_term_list())  

        # step 1.b. Mark all relations as useless, except those with no free variables (they are always relevant).
        initial_useless_relations_and_types = [(rel, rel_type) for rel, rel_type in zip(rule.body_relation_list, rule.body_relation_type_list)
                                               if len(get_output_free_var_names(rel)) != 0]
        # implement steps 2, 3 and 4
        def step_function(current_useless_relations_and_types):
            """
            Used by fixed pont algorithm.

            @param current_useless_relations_and_types: current useless relations and their types
            @return: useless relations after considering the new relevant free vars.
            """

            next_useless_relations_and_types = []
            
            # step 2 - Find all relations that has at least on free variable inside the relevant_free_variables set.
            for relation, rel_type in current_useless_relations_and_types:
                term_list = get_output_free_var_names(relation)
                if len(relevant_free_vars.intersection(term_list)) == 0:
                    next_useless_relations_and_types.append((relation, rel_type))
                else:
                    # step 3 - Unmark relation. The relations isn't added to the useless list, and thus it's unmarked.
                    # step 4 - Add all the free variables of the unmarked relation into the relevant_free_variables set.
                    relevant_free_vars.update(term_list)
                    relevant_free_vars.update(get_input_free_var_names(relation))

            return next_useless_relations_and_types

        # step 5 - fixed ponint. note that the distance function returns zero if and only if len(x) equals len(y).
        useless_relations_and_types = fixed_point(start=initial_useless_relations_and_types, step=step_function, distance=lambda x, y: int(len(x) != len(y)))
        
        # this part filters the useless relation from the rule
        relevant_relations_and_types = set(zip(rule.body_relation_list, rule.body_relation_type_list)).difference(useless_relations_and_types)
        new_body_relation_list, new_body_relation_type_list = zip(*relevant_relations_and_types)
        rule.body_relation_list = list(new_body_relation_list)
        rule.body_relation_type_list = list(new_body_relation_type_list)
```

```python
from rgxlog.engine.state.graphs import GraphBase, EvalState, STATE, TYPE, VALUE
from rgxlog.engine.utils.passes_utils import ParseNodeType
from rgxlog.engine.passes.lark_passes import GenericPass  # base class of all the passes
    

# finally, the implementation of the optimization pass
class RemoveUselessRelationsFromRule(GenericPass):
    """
    This pass removes duplicated relations from a rule.
    For example, the rule A(X) <- B(X), C(Y) contains a redundant relation (C(Y)).
    After this pass the rule will be A(X) <- B(X).

    @note: in the rule A(X) <- B(X, Y), C(Y); C(Y) is not redundant!
    """
    
    def __init__(self, parse_graph: GraphBase, **kwargs):
        self.parse_graph = parse_graph
            
    def run_pass(self, **kwargs):
        # get the new rules in the parse graph
        rules = self.parse_graph.get_all_nodes_with_attributes(type=ParseNodeType.RULE, state=EvalState.NOT_COMPUTED)
        for rule_node_id in rules:
            rule_node = self.parse_graph[rule_node_id]
            rule = rule_node[VALUE]
            remove_useless_relations(rule)
```

Modifying the pass stack looks like this:

```python
def print_pass_stack(pass_stack):
    """prints pass stack in a nice format"""
    
    for pass_ in pass_stack:
        print("\t" + pass_.__name__)
        
magic_session = Session()  # reset the magic session

original_pass_stack = magic_session.get_pass_stack()  # save the original pass stack

new_pass_stack = original_pass_stack.copy()
term_graph_pass = new_pass_stack.pop()  # remove last pass (this pass adds rules to term graph)
new_pass_stack.extend([RemoveUselessRelationsFromRule, term_graph_pass])

magic_session.set_pass_stack(new_pass_stack)

print(f"Pass stack before:")
print_pass_stack(original_pass_stack)

print("\nPass stack after:")
print_pass_stack(magic_session.get_pass_stack())
```

Now let's look at the effect of this pass on the parse graph:

```python
commands = """
new Good(int)
new Bad(int)

Example(X) <- Good(X), Bad(Y)
"""

def run_commands_and_print_parse_graph(session):
    session.run_commands(commands)
    print(session._parse_graph)
    

print("Parse graph of unmodified pass stack:\n")
run_commands_and_print_parse_graph(Session()) 

print("\nParse graph after adding optimization pass:\n")
run_commands_and_print_parse_graph(magic_session) 
```

Notice the difference in the rule node!


## Term Graph Structure Optimization


Optimizations of this kind traverse the `term_graph` and modify its structure.


## Term Graph Structure
Before reading on, it is important to understand how the `term_graph` looks like in order to understand the terminology used - there is detailed documentation inside the class docstring.

```python
from rgxlog.engine.state.graphs import TermGraphBase, TermGraph, TermNodeType
print(TermGraph.__doc__)
```

## Structure Optimization
Here are some examples of possible optimization passes of this kind:
1. An optimization that removes join nodes which have only one child relation.
   Note: this optimization already exists so there is no need to implement it.
   
2. An optimization that removes project nodes whose input is a single-column relation.
   
Here's the implementation of the second example:


## Optimization Example: Remove Redundant Project Nodes


The follwing optimization will traverse the term graph and find all project nodes that has input relation with arity of one.<br>
In this case, the project node is redundent and therefore, we remove it from the term graph.


Before jumping into the actual implementation, we will implement it in a psuedo code:
```
1. Find all project nodes and their union nodes parents (inside the term graph).

2. For each project node

    2.1. Check if the arity of the project node's input relation is one, using the following steps:
        a. get project's node child - we will denote it as child_node.
        b. if type of child_node is GET_REL or RULE_REL or CALC node child, return true if arity of the relation stored in child_node is one.
        c. if type of child_node is SELECT, return true if there is only one free variable in the relation stored in the child of the child_node. 
        d. if type of child_node is project:
              (i). get input relaations from all of it's children nodes
              (ii). return true if the arity of the join of all the input relations is one.
              
    2.2 if has arity of one, remove the node from the graph by connecting it's child to it's parent.
```

```python
# helper function
def is_relation_has_one_free_var(relation) -> bool:
    """
    Check whether relation is only one free variable.

    @param relation_: a relation or an ie_relation.
    """

    return len(relation.get_term_list()) == 1
```

```python
# this function implements step 2 in the pseudo code
def is_input_relation_of_node_has_arity_of_one(term_graph: TermGraphBase, node_id) -> bool:
    """
    @param node_id: id of the node.
    @note: we expect id of project/join node.
    @return: the arity of the relation that the node gets during the execution.
    """

    # staep 2.1.a: note that this methods suppose to work for both project nodes and join nodes.
    # project nodes always have one child while join nodes always have more than one child.
    # for that reason, we traverse all the children of the node.
    node_ids = term_graph.get_children(node_id)
    
    # used to compute arity of final relation
    free_vars: Set[str] = set()

    for node_id in node_ids:
        node_attrs = term_graph[node_id]
        node_type = node_attrs[TYPE]
        
        # step 2.1.b
        if node_type in (TermNodeType.GET_REL, TermNodeType.RULE_REL, TermNodeType.CALC):
            relation = node_attrs[VALUE]
            # if relation has more than one free var we can't prune the project
            if not is_relation_has_one_free_var(relation):
                return False

            free_vars |= set(relation.get_term_list())
            
        # step 2.1.c
        elif node_type is TermNodeType.SELECT:
            relation_child_id = next(iter(term_graph.get_children(node_id)))
            relation = term_graph[relation_child_id][VALUE]
            if not is_relation_has_one_free_var(relation):
                return False

            relation_free_vars = [var for var, var_type in zip(relation.get_term_list(), relation.get_type_list()) if var_type is DataTypes.free_var_name]
            free_vars |= set(relation_free_vars)
        
        # step 2.1.d
        elif node_type is TermNodeType.JOIN:
            # the input of project node is the same as the input of the join node
            return is_input_relation_of_node_has_arity_of_one(term_graph, node_id)

    return len(free_vars) == 1
```

```python
# finally, lets implement the optimization pass class
class PruneUnnecessaryProjectNodes(GenericPass):
    """
    This class prunes project nodes that gets a relation with one column (therefore, the project is redundant).

    For example, the rule A(X) <- B(X) will yield the following term graph:

        rule_rel node (of A)
            union node
                project node (on X)
                   get_rel node (get B)

        since we project a relation with one column, after this pass the term graph will be:

        rule_rel node (of A)
            union node
                get_rel node (get B)

    """

    def __init__(self, term_graph: TermGraphBase, **kwargs):
        self.term_graph = term_graph

    def run_pass(self, **kwargs):
        self.prune_project_nodes()
        
    def prune_project_nodes(self) -> None:
        """
        Prunes the redundant project nodes.
        """

        project_nodes = self.term_graph.get_all_nodes_with_attributes(type=TermNodeType.PROJECT)
        for project_id in project_nodes:
            if is_input_relation_of_node_has_arity_of_one(self.term_graph, project_id):
                # step 2.2
                self.term_graph.add_edge(self.term_graph.get_parent(project_id), self.term_graph.get_child(project_id))
                self.term_graph.remove_node(project_id)
                
```

The next step is adding this pass to the pass stack:

```python
magic_session = Session()  # reset the magic_session

new_pass_stack = magic_session.get_pass_stack()
new_pass_stack.append(PruneUnnecessaryProjectNodes)
magic_session.set_pass_stack(new_pass_stack)

print("New pass stack:")
print_pass_stack(magic_session.get_pass_stack())
```

Finally, lets see how this pass modifies the term graph:

```python
commands = """
new B(int)
A(X) <- B(X)
"""

def run_commands_and_print_term_graph(session):
    session.run_commands(commands)
    print(session._term_graph)
    

print("Term graph of unmodified pass stack:\n")
run_commands_and_print_term_graph(Session()) 

print("\nTerm graph after adding optimization pass:\n")
run_commands_and_print_term_graph(magic_session) 
```

Notice the changes in the term_graph's structure!


## Optimization Example: Overlapping Rules


Another optimization example, this time without an implementation.
It does the following:
1. Finds overlapping structure of rules.
2. Merges the overlapping structure and adds it to the term graph.


### Detailed Example Explanation


Let's look at the following example:
```
>>> D(X,Y) <- A(X),B(Y),C(X,Y,Z)
>>> E(X,Y) <- A(X),C(X,Y,Z), F(Z)
>>> x = E(X,Y) OR D(X,Y)
>>> x
```
Without merging terms with overlapping structures,
this would naively generate something that abstractly looks like this:
<!--
 digraph G {
   D_and [label="and"]
   E_and [label="and"]
   x->OR [style=dotted]
   E->E_and [style=dotted]
   D->D_and [style=dotted]
   OR -> {D_and,E_and}
   D_and ->{A,B,C}
   E_and -> {A,C,F} 
 }
-->
<img src="../doc/naive_term_graph.svg">

The weakness with this approach is that `A AND C` is computed twice.

A version of the term graph that takes care to merge terms with overlapping structures would look more like this:
<!--
 digraph G {
   D_and [label="and"]
   E_and [label="and"]
   x->OR [style=dotted]
   E->E_and [style=dotted]
   D->D_and [style=dotted]
   OR -> {D_and,E_and}
   D_and ->{and,B}
   E_and -> {and,F} 
   and -> {A,C}
 }
 -->
<img src="../doc/shared_term_graph.svg">

Here, we realized that A,C is a joint component and that we need only compute it once.
This would be the automatic equivalent of a smart programmer, refactoring the query above to look like

```
>>> TEMP(X,Y,Z) <- A(X), C(X,Y,Z)
>>> D(X,Y) <- B(Y),TEMP(X,Y,Z)
>>> E(X,Y) <- TEMP(X,Y,Z), F(Z)
>>> x= E(X,Y) OR D(X,Y)
>>> x
```


Here's a pseudo implementation of this pass: 
```
1. get all the registered rules by using term_graph.get_all_rules).

2. find overlapping structure between rules (this step can be implemented in many different ways).

3. create new rule that consists of the overlapping structure.

4. add this new rule to the term graph by using term_graph.add_rule_to_term_graph.

5. updated the previous rule to use the newly created rule.

6. added the rules to the term graph.

7. delete the previous versions of the rule from the term graph by using term_graph.remove_rule.
```

For example, 
if the following rules were registered:
1. ```D(X,Y) <- A(X),B(Y),C(X,Y,Z)```
2. ```E(X,Y) <- A(X),C(X,Y,Z), F(Z)```

In the second step of the algorithm, we will find that both rules share the structure ```A(X),C(X,Y,Z)```.<br>
In the third step we will create a new relation ```TEMP(X,Y,Z) <- A(X), C(X,Y,Z)```, and add it to the term graph.<br>
In the fifth step we will modify to original rules in the following way:
1. ```D(X,Y) <- B(Y),TEMP(X,Y,Z)```
2. ```E(X,Y) <- TEMP(X,Y,Z), F(Z)```

And then we will add them to the term graph.<br>
The last step will delete the old rules from the term graph.

```python

```
