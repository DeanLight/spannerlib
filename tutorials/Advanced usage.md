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

# Using native Python


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

# Changing the session of the magic cells


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

# Mixing magics with dynamic session calls


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

# Processing the result of a query in python and using the result in a new query


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

# Import a relation from a `DataFrame`


By default, non-boolean query results are saved as a `DataFrame`.
A relation can also be imported from a `DataFrame`, like this:

```python
from pandas import DataFrame

df = DataFrame([["Shrek",42], ["Fiona", 1337]], columns=["name", "number"])
session.import_relation_from_df(df, relation_name="ogres")
%rgxlog ?ogres(X,Y)

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

# Adding Optimization Passes to the Pass Stack


Before reading this section, we recommend to go over [detailed readme file](long_readme.md) in order to undrestand how passes work.

There are three kind of optimization passes:
1. The first one, manipulates rules before they are added to the `term graph`.
2. The second one, manipulates the structure of the `term graph`.
    
In this section, we will implement two simple optimization passes one of each kind.


## Rule-Manipulation Optimization


These kind of optimization travrse the `parse_graph` and rules that weren't added to the `term graph`.
Then, they update each rule - by modyfieng it's body relations list.

Here are some example of possible optimization passes of this kind:
1. optimization that removes duplicated relations from a rule.
   i.e., the rule `A(X) <- B(X), C(X), B(X)` contains the relation `B(X)` twice.
   the optimization will transform the rule into `A(X) <- B(X), C(X)`.
   
2. optimization that removes useless relations from a rule.
   i.e., the rule `A(X) <- B(X), C(Y)` contains the useless relation `C(Y)`.
   the optimization will transform the rule into `A(X) <- B(X)`.
   
We will demonsrate how to implement the second example.

```python
from rgxlog.engine.utils.general_utils import fixed_point  # gets intial value, step function and distance function; computes a fixed point.
from rgxlog.engine.utils.general_utils import get_output_free_var_names # returns the free vars of the realtion (if it's ie relation it returns the output free vars)
from rgxlog.engine.utils.general_utils import get_input_free_var_names # returns input free vars of ie relation (if it's regulare relation returns empty set)



# first, lets implement the logic that removes useless relations from a rule
def remove_useless_relations(rule):
        """
        Finds redundant relations and removes them from the rule.
        
        @param rule: a rule.
        """
        # holds free vars that are essential to compute to rule
        relevant_free_vars = set(rule.head_relation.get_term_list())  

        # relation without free vars are always relevant (we use them as predicates)
        initial_useless_relations_and_types = [(rel, rel_type) for rel, rel_type in zip(rule.body_relation_list, rule.body_relation_type_list)
                                               if len(get_output_free_var_names(rel)) != 0]

        def step_function(current_useless_relations_and_types):
            """
            Used by fixed pont algorithm.

            @param current_useless_relations_and_types: current useless relations and their types
            @return: useless relations after considering the new relevant free vars.
            """

            next_useless_relations_and_types = []
            for relation, rel_type in current_useless_relations_and_types:
                term_list = get_output_free_var_names(relation)
                if len(relevant_free_vars.intersection(term_list)) == 0:
                    next_useless_relations_and_types.append((relation, rel_type))
                else:
                    # if relation contains essential free var than all it's free vars are essential
                    relevant_free_vars.update(term_list)
                    relevant_free_vars.update(get_input_free_var_names(relation))

            return next_useless_relations_and_types

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

# now we'll implement a function that traverses the parse graph and finds rule that weren't added to the term graph yet
# note: this function is already implemented in the passes_utils file, we re-implement it here in order to show how to traverse the parse grpah.
def get_new_rule_nodes(parse_graph: GraphBase):
    """
    Finds all rules that weren't added to the term graph yet.
    """

    node_ids = parse_graph.post_order_dfs()  # get all nodes inside the parse graph
    rule_nodes: List = list()

    for node_id in node_ids:
        term_attrs = parse_graph.get_node_attributes(node_id)

        # the term is not computed, get its type and compute it accordingly
        term_type = term_attrs[TYPE]

        # make sure that the rule wasn't adde to term graph before
        if term_type == ParseNodeType.RULE and term_attrs[STATE] == EvalState.NOT_COMPUTED:
            rule_nodes.append(node_id)

    return rule_nodes
```

```python
from rgxlog.engine.passes.lark_passes import GenericPass
    

# finally, the implemntation of the optimization pass
class RemoveUselessRelationsFromRule(GenericPass):
    """
    This pass removes duplicated relations from a rule.
    For example, the rule A(X) <- B(X), C(Y) contains a redundant relation (C(Y)).
    After this pass the rule will be A(X) <- B(X).

    @note: in the rule A(X) <- B(X, Y), C(Y); C(Y) is not redundant!
    """
    
    def __init__(self, **kwargs):
        self.parse_graph: GraphBase = kwargs["parse_graph"]
            
    def run_pass(self, **kwargs):
        rules = get_new_rule_nodes(self.parse_graph)
        for rule_node_id in rules:
            rule_node = self.parse_graph[rule_node_id]
            rule = rule_node[VALUE]
            remove_useless_relations(rule)
```

In order to add this optimization into the pass stack you shold do the follwing:

```python
def print_pass_stack(pass_stack):
    """prints pass stack in a nice format"""
    
    for pass_ in pass_stack:
        print("\t" + pass_.__name__)
        
magic_session = Session()  # reset the magic session

original_pass_stack = magic_session.get_pass_stack()  # save the original pass stack

new_pass_stack = original_pass_stack.copy()
term_graph_pass = new_pass_stack.pop()  # remove last pass - adds rules to term graph
new_pass_stack.extend([RemoveUselessRelationsFromRule, term_graph_pass])

magic_session.set_pass_stack(new_pass_stack)

print(f"Pass stack before:")
print_pass_stack(original_pass_stack)

print("\nPass stack after:")
print_pass_stack(magic_session.get_pass_stack())
```

Now lets look at the affat of this pass on the pars graph

```python
commands = """
new Good(int)
new Bad(int)

Example(X) <- Good(X), Bad(Y)
"""

def run_first_experiment(session):
    """runs the command and print the parse graph"""
    session.run_commands(commands)
    print(session._parse_graph)
    

print("Parse graph of unmodified pass stack:\n")
run_first_experiment(Session()) 
print()

print("Parse graph of pass stack with the optimizaion pass:\n")
run_first_experiment(magic_session) 
```

Notice the difference in the rule node!


## Term-Graph-Structure Optimization


These kind of optimization travrse the `term_graph` and modify it's structure.
Before you keep reading, make sure you understand how the `term graph` looks like (there is detailed documentation insidee the class docstring) and in order to understand the our terminology.

Here are some example of possible optimization passes of this kind:
1. optimization that removes join nodes that has only one child relation
   note: this optimization already exists so there is no need to implement it.
   
2. optimization that removes project nodes that get relation with one column.
   
We will demonsrate how to implement the second example.

```python
from rgxlog.engine.state.graphs import TermGraphBase, TermNodeType


# first, we will implement a function that finds all the union node and their project children (inside the term graph)
def get_all_union_and_project_nodes(term_graph: TermGraphBase):
    """
    @return: a mapping between union nodes ids to their project children nodes id.
    """

    union_to_project_children = {}
    nodes_ids = term_graph.post_order_dfs()  # get all the nodes in the term graph

    for node_id in nodes_ids:
        node_attrs = term_graph[node_id]
        node_type = node_attrs[TYPE]

        if node_type is TermNodeType.UNION:
            children = term_graph.get_children(node_id)
            # get all project children
            project_children = [node for node in children if term_graph[node][TYPE] is TermNodeType.PROJECT]
            union_to_project_children[node_id] = project_children

    return union_to_project_children
```

```python
# now we will implement a function that get a union node and one of it's project children, it will prune the project node
def remove_project_node(term_graph: TermGraphBase, union_node, project_node) -> None:
    """
    Removes the project node from the term graph and connects it's child to the union node that was his parent.

    @param union_node: id of the union node.
    @param project_node: id of the project node.
    """

    # project node has exactly one child
    project_child = next(iter(term_graph.get_children(project_node)))

    # connect project's child to it's union node parent
    term_graph.add_edge(union_node, project_child)

    # delete project node from the term graph
    term_graph.remove_node(project_node)
```

```python

def is_relation_has_one_free_var(relation) -> bool:
    """
    Check whether relation is only one free variable.

    @param relation_: a relation or an ie_relation.
    """

    return len(relation.get_term_list()) == 1


# the final helper function, will get id of a node and will compute the number of free vars in the input relation of this node
def find_arity_of_node(term_graph: TermGraphBase, node_id) -> int:
    """
    @param node_id: id of the node.
    @note: we expect id of project/join node.
    @return: the arity of the relation that the node gets during the execution.
    """

    # this methods suppose to work for both project nodes and join nodes.
    # project nodes always have one child while join nodes always have more than one child.
    # for that reason, we traverse all the children of the node.
    node_ids = term_graph.get_children(node_id)
    free_vars: Set[str] = set()

    for node_id in node_ids:
        node_attrs = term_graph[node_id]
        node_type = node_attrs[TYPE]
        
        # in the follwing cases the input relation is the relation stored in the value attribute of the node
        if node_type in (TermNodeType.GET_REL, TermNodeType.RULE_REL, TermNodeType.GET_REL.CALC):
            relation = node_attrs[VALUE]
            # if relation has more than one free var we can't prune the project
            if not is_relation_has_one_free_var(relation):
                return 0

            free_vars |= set(relation.get_term_list())

        elif node_type is TermNodeType.JOIN:
            # the input of project node is the same as the input of the join node
            return find_arity_of_node(term_graph, node_id)

        # in this case, we extratc the free vars of the relation (since not all the terms ore free vars)
        elif node_type is TermNodeType.SELECT:
            relation_child_id = next(iter(term_graph.get_children(node_id)))
            relation = term_graph[relation_child_id][VALUE]
            if not is_relation_has_one_free_var(relation):
                return 0

            relation_free_vars = [var for var, var_type in zip(relation.get_term_list(), relation.get_type_list()) if var_type is DataTypes.free_var_name]
            free_vars |= set(relation_free_vars)

    return len(free_vars)
```

```python
# finally, lets implement the optimization pass
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

    def __init__(self, **kwargs):
        self.term_graph: TermGraphBase = kwargs["term_graph"]

    def run_pass(self, **kwargs):
        self.prune_project_nodes()
        
    def prune_project_nodes(self) -> None:
        """
        Prunes the redundant project nodes.
        """

        union_to_project_children = get_all_union_and_project_nodes(self.term_graph)
        for union_id, project_ids in union_to_project_children.items():
            for project_id in project_ids:
                arity = find_arity_of_node(self.term_graph, project_id)
                if arity == 1:
                    # in this case the input relations of the project node has arity of one so we can prune the node
                    remove_project_node(self.term_graph, union_id, project_id)
        return
```

Next step is adding this pass to the pass stack:

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

def run_second_experiment(session):
    """runs the command and print the term graph"""
    session.run_commands(commands)
    print(session._term_graph)
    

print("Term graph of unmodified pass stack:\n")
run_second_experiment(Session()) 
print()

print("Term graph of pass stack with the optimizaion pass:\n")
run_second_experiment(magic_session) 
```

Notice the changes in the term_graph's structure!


#### Now we will show a more advanced optimization pass, but this time we won't implement it.

The optimization will do the following:
1. find overlapping structure of rules.
2. than it will merge the overlapping structure and add it to the term graph.

this example is described in detail in the [readme file](long_readme.md).
    
We will show a pseudo implementation of this pass: 

- get all the registered rules by using ```term_graph.get_all_rules```.
- find overlapping strucre between rules  (this step can be implemented in many different ways).
- cretae new rule that consists of the overlapping structute.
- add this new rule to the term graph by using ```term_graph.add_rule_to_term_graph```.
- updated the previous rule to use the newly created rule.
- added the rules to the term graph.
- delete the previous versions of the rule from the term graph by using ```term_graph.remove_rule```

For example, 
if the following rule were registerd:
1. ```D(X,Y) <- A(X),B(Y),C(X,Y,Z)```
2. ```E(X,Y) <- A(X),C(X,Y,Z), F(Z)```

in the second step of the algorithm we will find that both rules share the structure ```A(X),C(X,Y,Z)```.<br>
in the third step we will create a new relation ```TEMP(X,Y,Z) <- A(X), C(X,Y,Z)```, and add it to the term grah.<br>
in the fifth step we will modify to original rules in the following way:
1. ```D(X,Y) <- B(Y),TEMP(X,Y,Z)```
2. ```E(X,Y) <- TEMP(X,Y,Z), F(Z)```

and then we will add them to the term graph.<br>
the last step will delete the old rules from the term graph.

```python

```
