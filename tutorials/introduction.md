# Spanner Workbench Introduction
In this tutorial you will learn the basics of spanner workbench:
* [how to install, import and use RGXLog](#use_rgxlog)
* [local and free variables](#local_and_free_vars)
* [local variable assignment](#local_var_assignment)
* [reading from a file](#read_a_file)
* [declaring a relation](#declare_relations)
* [adding facts](#facts)
* [adding rules](#rules)
* [queries](#queries)
* [using RGXLog's primitive information extractor: functional regex formulas](#RGX_ie)
* [using custom information extractors](#custom_ie)
* [additional small features](#small_features)

At the end of this tutorial there is also an [example for a small RGXLog program.](#example_program)

# Using RGXLog<a class="anchor" id="use_rgxlog"></a>

### Installation

prerequisites:

* Have [Python](https://www.python.org/downloads/) version 3.8 or above installed

To download and install RGXLog run the following command in your terminal:

```bash
git clone https://github.com/DeanLight/spanner_workbench
cd spanner_workbench

pip install src/rgxlog-interpreter 

```
Make sure you are calling the pip version of your current python environment.
To install with another python interpreter, run

```bash

<path_to_python_interpreter> -m pip install  src/rgxlog-interpreter

```
You can also install RGXLog in the current Jupyter kernel:

```python
import sys
from pathlib import Path
current_python=f"{sys.executable}"
package_path=Path("../src/rgxlog-interpreter")
```

```
! {current_python} -m pip install {package_path}
```

In order to use RGXLog in jupyter notebooks, you must first load it:



```python
import rgxlog  # or `load_ext rgxlog`
```

Importing the RGXLog library automatically loads the `%rgxlog` and `%%rgxlog` cell magics which accepts RGXLog queries as shown below.<br>
use %rgxlog to run a single line, and %%rgxlog to run a block of code:


```python
%rgxlog new relation(str)
print("this is python code")
```

    this is python code



```python
%%rgxlog
new uncle(str, str)
uncle("bob", "greg")
?uncle(X,Y)
```

    printing results for query 'uncle(X, Y)':
      X  |  Y
    -----+------
     bob | greg
    


# Local and free variables<a class="anchor" id="local_and_free_vars"></a>

RGXLog distinguishes two kinds of variables.

The first kind are local variables. These are variables that store a single value (e.g. string). They work similarly to variables in python. A local variable must be defined via assignment before being used.

A local variable name must begin with a lowercase letter or with an underscore (_), and can be continued with letters, digits and underscores

Here are some examples for legal local variable names:
* `a`
* `a_name123`
* `_Some_STRING`

And here are some illegal local variable names:
* `A`
* `A_name`
* `1_a`


The second kind of variables are free variables. Free variables do not hold any value and are used to define relations inside [queries](#queries) and [rules](#rules). Free variables do not need to be declared or defined before being used.

A free variable name must begin with an uppercase letter and can be continued with letters, digits and underscores

Here are some examples for legal free variable names:
* `A`
* `A_name`

And here are some illegal free variable names:
* `a`
* `a_name`
* `_Some_STRING`
* `1A`


# Local variable assignment<a class="anchor" id="local_var_assignment"></a>
RGXLog allows you to use three types of variables: strings, integers and spans.
The assignment of a string is intuitive:


```python
%%rgxlog
b = "bob"
b2 = b # b2's value is "bob"
# you can write multiline strings using a line overflow escape like in python
b3 = "this is a multiline  \
string"
b4 = "this is a multiline string" # b4 holds the same value as b3
```

The assignment of integers is also very simple:


```python
%%rgxlog
n = 4
n2 = n # n2 = 4
```

 A span identifies a substring of a string by specifying its bounding indices. It is constructed from two integers.
 You can assign a span value like this:


```python
%%rgxlog
span1 = [3,7)
span2 = span1 # span2 value is [3,7)
```

# Reading from a file<a class="anchor" id="read_a_file"></a>
You can also perform a string assignment by reading from a file. You will need to provide a path to a file by either using a string literal or a string variable:


```python
%%rgxlog
a = read("introduction.ipynb")
b = "introduction.ipynb" 
c = read(b) # c holds the same string value as a
```

# Declaring a relation<a class="anchor" id="declare_relations"></a>
RGXLog allows you to define and query relations.
You have to declare a relation before you can use it (unless you define it with a rule as we'll see in the "rules" chapter). Each term in a relation could be a string, an integer or a span. Here are some examples for declaring relations:


```python
%%rgxlog
# 'brothers' is a relation with two string terms.
new brothers(str, str)
# 'confused' is a relation with one string term.
new confused(str)
# 'animal' is a relation with one string term and one span term 
new animal(str, span)
# 'scores' is a relation with one string term and one int term
new scores(str, int)
```

# Facts<a class="anchor" id="facts"></a>
RGXLog is an extension of Datalog, a declarative logic programming language. In Datalog you can declare "facts", essentially adding tuples to a relation. To do it you use the following syntax:

```
relation_name(term_1,term_2,...term_3)
```

or

```
relation_name(term_1,term_2,...term_3) <- True
```

where each `term` is either a constant or a local variable that is from the same variable type that was declared for `relation_name` at the same location.

For example:


```python
%%rgxlog
# first declare the relation that you want to use
new noun(str, span)
# now you can add facts (tuples) to that relation
# this span indicates that a noun "Life" can be found at indexes 0 to 3
noun("Life finds a way", [0,4)) 
# another example
new sisters(str, str)
sisters("alice", "rin") <- True
# sisters([0,4), "rin") # illegal as [0,4) is not a string
```

You could also remove a fact using a similar syntax:

```relation_name(term_1,term_2,...term_3) <- False```

if a fact that you try to remove does not exist, the remove fact statement will be silently ignored


```python
%%rgxlog
new goals(str, int)
goals("kronovi", 10)
goals("kronovi", 10) <- False  # 'goals' relation is now empty
goals("kronovi", 10) <- False  # this statement does nothing
```

# Rules<a class="anchor" id="rules"></a>
Datalog allows you to deduce new tuples for a relation.
RGXLog includes this feature as well:


```python
%%rgxlog
new parent(str ,str)
parent("bob", "greg")
parent("greg", "alice")
# now add a rule that deduces that bob is a grandparent of alice
grandparent(X,Z) <- parent(X,Y), parent(Y,Z) # ',' is a short hand to the 'and' operator
```

RGXLog also supports recursive rules:


```python
%%rgxlog
parent("Liam", "Noah")
parent("Noah", "Oliver")
parent("James", "Lucas")
parent("Noah", "Benjamin")
parent("Benjamin", "Mason")
ancestor(X,Y) <- parent(X,Y)
# This is a recursive rule
ancestor(X,Y) <- parent(X,Z), ancestor(Z,Y)

# Queries are explained in the next section
?ancestor("Liam", X)
?ancestor(X, "Mason")
?ancestor("Mason", X)
```

    printing results for query 'ancestor("Liam", X)':
        X
    ----------
      Mason
      Oliver
     Benjamin
       Noah
    
    printing results for query 'ancestor(X, "Mason")':
        X
    ----------
       Noah
       Liam
     Benjamin
    
    printing results for query 'ancestor("Mason", X)':
    []
    


You could also remove a rule via the session:

```magic_session.remove_rule(rule_to_delete)```

note: the rule must be written exactly as it appears in the output of `print_all_rules`


```python
%%rgxlog
confused("Josh")
brothers("Drake", "Josh")

# oops! this rule was added by mistake!
ancestor(X, Y) <- brothers(X, Y), confused(Y)

?ancestor(X,Y)
```

    printing results for query 'ancestor(X, Y)':
        X     |    Y
    ----------+----------
      Drake   |   Josh
       Noah   |  Mason
       Liam   |  Mason
       Liam   |  Oliver
       Liam   | Benjamin
       bob    |  alice
       bob    |   greg
       greg   |  alice
       Liam   |   Noah
       Noah   |  Oliver
      James   |  Lucas
       Noah   | Benjamin
     Benjamin |  Mason
    



```python
from rgxlog import magic_session
# remove the rule from the current session
print ("before:")
magic_session.print_all_rules()

magic_session.remove_rule("ancestor(X, Y) <- brothers(X, Y), confused(Y)")

print ("after:")
magic_session.print_all_rules()
```

    before:
    Printing all rules:
    grandparent(X, Z) <- parent(X, Y), parent(Y, Z)
    ancestor(X, Y) <- parent(X, Y)
    ancestor(X, Y) <- parent(X, Z), ancestor(Z, Y)
    ancestor(X, Y) <- brothers(X, Y), confused(Y)
    
    after:
    Printing all rules:
    grandparent(X, Z) <- parent(X, Y), parent(Y, Z)
    ancestor(X, Y) <- parent(X, Y)
    ancestor(X, Y) <- parent(X, Z), ancestor(Z, Y)
    



```python
%%rgxlog
?ancestor(X,Y)
```

    printing results for query 'ancestor(X, Y)':
        X     |    Y
    ----------+----------
       Noah   |  Mason
       Liam   |  Mason
       Liam   |  Oliver
       Liam   | Benjamin
       bob    |  alice
       bob    |   greg
       greg   |  alice
       Liam   |   Noah
       Noah   |  Oliver
      James   |  Lucas
       Noah   | Benjamin
     Benjamin |  Mason
    


success! the rule was deleted - Drake and Josh are no longer part of the `?ancestor` query result

Note that during this examples we used ```print_all_rules```.<br>
This function prints all the registered rules.<br>
If you wan't to print only rules that relevant to spesific rule head, you can pass the rule head as a parameter.


```python
magic_session.print_all_rules("ancestor")
```

    Printing all rules with head ancestor:
    ancestor(X, Y) <- parent(X, Y)
    ancestor(X, Y) <- parent(X, Z), ancestor(Z, Y)
    


In addition you can use ```remove_all_rules``` to remove all the rules (it won't affect the facts).<br>
You can pass rule head paraemetr to remove all the rules related to it.


```python
magic_session.remove_all_rules("ancestor")
magic_session.print_all_rules()

magic_session.remove_all_rules()
magic_session.print_all_rules()

# facts are not affected...
%rgxlog ?parent(X, Y)
```

    Printing all rules:
    grandparent(X, Z) <- parent(X, Y), parent(Y, Z)
    
    Printing all rules:
    
    printing results for query 'parent(X, Y)':
        X     |    Y
    ----------+----------
     Benjamin |  Mason
       Noah   | Benjamin
      James   |  Lucas
       Noah   |  Oliver
       Liam   |   Noah
       greg   |  alice
       bob    |   greg
    


# Queries<a class="anchor" id="queries"></a>
Querying is very simple in RGXLog. You can query by using constant values, local variables and free variables:


```python
%%rgxlog
# first create a relation with some facts for the example
new grandfather(str, str)
# bob and george are the grandfathers of alice and rin
grandfather("bob", "alice")
grandfather("bob", "rin")
grandfather("george", "alice")
grandfather("george", "rin")
# edward is the grandfather of john
grandfather("edward", "john")

# now for the queries
?grandfather("bob", "alice") # returns an empty tuple () as alice is bob's grandchild
?grandfather("edward", "alice") # returns nothing as alice is not edward's grandchild
?grandfather("george", X) # returns "rin" and "alice" as both rin
# and alice are george's grandchildren
?grandfather(X, "rin") # returns "bob" and "george" (rin's grandfathers)
?grandfather(X, Y) # returns all the tuples in the 'grandfather' relation

new verb(str, span)
verb("Ron eats quickly.", [4,8))
verb("You write neatly.", [4,9))
?verb("Ron eats quickly.", X) # returns [4,8)
?verb(X,[4,9)) # returns "You write neatly."
         
new orders(str, int)
orders("pie", 4)
orders("pizza", 4)
orders("cake", 0)
?orders(X, 4) # retutns "pie" and "pizza"         
```

    printing results for query 'grandfather("bob", "alice")':
    [()]
    
    printing results for query 'grandfather("edward", "alice")':
    []
    
    printing results for query 'grandfather("george", X)':
       X
    -------
      rin
     alice
    
    printing results for query 'grandfather(X, "rin")':
       X
    --------
      bob
     george
    
    printing results for query 'grandfather(X, Y)':
       X    |   Y
    --------+-------
     edward | john
     george |  rin
     george | alice
      bob   |  rin
      bob   | alice
    
    printing results for query 'verb("Ron eats quickly.", X)':
       X
    --------
     [4, 8)
    
    printing results for query 'verb(X, [4, 9))':
             X
    -------------------
     You write neatly.
    
    printing results for query 'orders(X, 4)':
       X
    -------
     pizza
      pie
    


You may have noticed that the query

```
?grandfather("bob", "alice")
```

returns an empty tuple. This is because of the fact that bob is alice's grandfather is true,
but we did not use any free variables to construct the tuple of the query's relation, that is why we get a single empty tuple as a result

A good example for using free variables to construct a relation is the query:

```
?grandfather("george", X)
```

which finds all of george's grandchildren (`X`) and constructs a tuple for each one.

# Functional regex formulas<a class="anchor" id="RGX_ie"></a>
RGXLog supports information extraction using a regular expressions and named capture groups (for now in rule bodies only).
You will first need to define a string variable either by using a literal or a load from a file, and then you can use the following syntax in a rule body:

```
rgx_span(regex_input ,regex_formula)->(x_1, x_2, ...,x_n)
```

or

```
rgx_string(regex_input ,regex_formula)->(x_1, x_2, ...,x_n)
```

where:
* `regex_input` is the string that the regex operation will be performed on
* `regex_formula` is either a string literal or a string variable that represents your regular expression.
* `x_1`, `x_2`, ... `x_n` can be either constant terms or free variable terms. They're used to construct the tuples of the resulting relation. the number of terms has to be the same as the number of capture groups used in `regex_formula`. If not capture groups are used, then each returned tuple includes a single, whole regex match, so only one term should be used.

The only difference between the 'rgx_span' and 'rgx_string' ie functions, is that RGX returns spans while RGXString returns strings. This also means that if you want to use constant terms as return values, they have to be spans if you use 'RGX', or strings if you use 'RGXString'

For example:


```python
%%rgxlog
report = "In 2019 we earned 2000 EUR"
annual_earning(Year, Amount) <- py_rgx_string(report,"(\d\d\d\d).*?(?P<a>\d+)")->(Amount, Year)
?annual_earning(X, Y) # TODO@niv: dean, if we use regex with repetitions here, this becomes is ugly - is this intentional?

```

    printing results for query 'annual_earning(X, Y)':
        X |    Y
    ------+------
     2000 | 2019
    


# Creating and Registering a New IE Function

Using regex is nice, but what if we want to define our own IE function? <br>
RGXLog allows us to do that:

### IE function `get_happy`


```python
import re
from rgxlog.engine.datatypes.primitive_types import DataTypes

# the function itself, which should yield an iterable of primitive types
def get_happy(text):
    """
    get the names of people who are happy in `text`
    """
    compiled_rgx = re.compile("(\w+) is happy")
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings

# the input types, a list of primitive types
get_happy_in_types = [DataTypes.string]

# the output types, either a list of primitive types or a method which expects an arity
get_happy_out_types = lambda arity : arity * [DataTypes.string]
# or: `get_happy_out_types = [DataTypes.string]`

# finally, register the function
magic_session.register(ie_function=get_happy,
                       ie_function_name = "get_happy",
                       in_rel=get_happy_in_types,
                       out_rel=get_happy_out_types)
```

### #TODO@niv: @dean, maybe rename information extractors to tell them apart from IE functions?

# Custom information extractors<a class="anchor" id="custom_ie"></a>
RGXLog allows you to define and use your own information extractors. You can use them only in rule bodies in the current version. The following is the syntax for custom information extractors:

```
func(term_1,term_2,...term_n)->(x_1, x_2, ..., x_n)
```

where:
* `func` is a IE function that was previously defined and registered (see the 'advanced_usage' tutorial)
* `term_1`,`term_2`,...,`term_n` are the parameters for func
* `x_1`, ... `x_n` could be any type of terms, and are used to construct tuples of the resulting relation

For example:

### custom IE using `get_happy`


```python
%%rgxlog
new grandmother(str, str)
grandmother("rin", "alice")
grandmother("denna", "joel")
sentence = "rin is happy, denna is sad."
# note that this statement will fail as 'get_happy' is not registered as an ie_function
test_happy(X) <- get_happy(sentence) -> (X)
happy_grandmother(X) <- grandmother(X,Z),get_happy(sentence)->(X)
?happy_grandmother(X) # assuming get_happy returned "rin", also returns "rin"
```

    printing results for query 'happy_grandmother(X)':
      X
    -----
     rin
    


## More information about IE functions
* You can remove an IE function via the session:

```magic_session.remove_ie_function(ie_function_name)```

* If you want to remove all the registered ie functions:

```magic_session.remove_all_ie_functions()```

* If you register an IE function with a name that was already registered before, the old IE function will be overwitten by the new one. 
<br><br>
* You can inspect all the registered IE functions using the following command:

```magic_session.print_registered_ie_functions()```


```python
# first, let's print all functions:
magic_session.print_registered_ie_functions()
```

    py_rgx_span
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9b50>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9b50>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of spans that represents the results
        
    
    
    py_rgx_string
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9bb0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9bb0>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of strings that represents the results
        
    
    
    rgx_span
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9fa0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9fa0>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of spans that represents the results
        
    
    
    rgx_string
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5070>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5070>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of strings that represents the results
        
    
    
    JsonPath
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc50a0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc50a0>
    
        @param json_document: The document on which we will run the path expression
        @param path_expression: The query to execute.
    
        @return: json documents
        
    
    
    JsonPathFull
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5250>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5250>
    
        @param json_document: The document on which we will run the path expression
        @param path_expression: The query to execute.
    
        @return: json documents with the full results paths.
        
    
    
    Tokenize
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc52b0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc52b0>
    None
    
    
    SSplit
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5310>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5310>
    None
    
    
    POS
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5370>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5370>
    None
    
    
    Lemma
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc53d0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc53d0>
    None
    
    
    NER
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5430>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5430>
    None
    
    
    EntityMentions
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5490>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5490>
    None
    
    
    CleanXML
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc54f0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc54f0>
    None
    
    
    Parse
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5580>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5580>
    None
    
    
    DepParse
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc55e0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc55e0>
    None
    
    
    Coref
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5640>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5640>
    None
    
    
    OpenIE
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc56a0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc56a0>
    None
    
    
    KBP
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5700>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5700>
    None
    
    
    Quote
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5760>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5760>
    None
    
    
    Sentiment
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc57c0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc57c0>
    None
    
    
    TrueCase
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5820>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5820>
    None
    
    
    get_happy
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87d5921940>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87d5921940>
    
        get the names of people who are happy in `text`
        
    
    



```python
magic_session.remove_ie_function("Coref")
magic_session.print_registered_ie_functions()
```

    py_rgx_span
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9b50>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9b50>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of spans that represents the results
        
    
    
    py_rgx_string
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9bb0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9bb0>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of strings that represents the results
        
    
    
    rgx_span
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9fa0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6db9fa0>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of spans that represents the results
        
    
    
    rgx_string
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5070>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5070>
    
        @param text: The input text for the regex operation
        @param regex_pattern: the pattern of the regex operation
    
        @return: tuples of strings that represents the results
        
    
    
    JsonPath
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc50a0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc50a0>
    
        @param json_document: The document on which we will run the path expression
        @param path_expression: The query to execute.
    
        @return: json documents
        
    
    
    JsonPathFull
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5250>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5250>
    
        @param json_document: The document on which we will run the path expression
        @param path_expression: The query to execute.
    
        @return: json documents with the full results paths.
        
    
    
    Tokenize
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc52b0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc52b0>
    None
    
    
    SSplit
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5310>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5310>
    None
    
    
    POS
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5370>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5370>
    None
    
    
    Lemma
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc53d0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc53d0>
    None
    
    
    NER
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5430>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5430>
    None
    
    
    EntityMentions
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5490>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5490>
    None
    
    
    CleanXML
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc54f0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc54f0>
    None
    
    
    Parse
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5580>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5580>
    None
    
    
    DepParse
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc55e0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc55e0>
    None
    
    
    OpenIE
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc56a0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc56a0>
    None
    
    
    KBP
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5700>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5700>
    None
    
    
    Quote
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5760>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5760>
    None
    
    
    Sentiment
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc57c0>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc57c0>
    None
    
    
    TrueCase
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5820>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87b6dc5820>
    None
    
    
    get_happy
    <bound method IEFunction.get_meta_data of <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87d5921940>>
    <rgxlog.engine.ie_functions.ie_function_base.IEFunction object at 0x7f87d5921940>
    
        get the names of people who are happy in `text`
        
    
    


another tremendous triumph! Coref was deleted from the registered functions

# Additional small features<a class="anchor" id="small_features"></a>
You can use line overflow escapes if you want to split your statements into multiple lines

```python pycharm={"name": "#%%\n"}
%%rgxlog
k \
= "some \
string"
```

# Full RGXLog program example<a class="anchor" id="example_program"></a>


```python
%%rgxlog
new lecturer(str, str)
lecturer("walter", "chemistry")
lecturer("linus", "operation systems")
lecturer("rick", "physics")

new enrolled(str, str)
enrolled("abigail", "chemistry")
enrolled("abigail", "operation systems")
enrolled("jordan", "chemistry")
enrolled("gale", "operation systems")
enrolled("howard", "chemistry")
enrolled("howard", "physics")

enrolled_in_chemistry(X) <- enrolled(X, "chemistry")
?enrolled_in_chemistry("jordan") # returns empty tuple ()
?enrolled_in_chemistry("gale") # returns nothing
?enrolled_in_chemistry(X) # returns "abigail", "jordan" and "howard"

enrolled_in_physics_and_chemistry(X) <- enrolled(X, "chemistry"), enrolled(X, "physics")
?enrolled_in_physics_and_chemistry(X) # returns "howard"

lecturer_of(X,Z) <- lecturer(X,Y), enrolled(Z,Y)
?lecturer_of(X,"abigail") # returns "walter" and "linus"

grade_str = "abigail 100 jordan 80 gale 79 howard 60"
grade_of_chemistry_students(Student, Grade) <- \
py_rgx_string(grade_str, "(\w+).*?(\d+)")->(Student, Grade), enrolled_in_chemistry(Student)
?grade_of_chemistry_students(X, "100") # returns "abigail"
```

    printing results for query 'enrolled_in_chemistry("jordan")':
    [()]
    
    printing results for query 'enrolled_in_chemistry("gale")':
    []
    
    printing results for query 'enrolled_in_chemistry(X)':
        X
    ---------
     abigail
     jordan
     howard
    
    printing results for query 'enrolled_in_physics_and_chemistry(X)':
       X
    --------
     howard
    
    printing results for query 'lecturer_of(X, "abigail")':
       X
    --------
     linus
     walter
    
    printing results for query 'grade_of_chemistry_students(X, "100")':
        X
    ---------
     abigail
    


# Useful tricks<a class="anchor" id="Usefull tricks"></a>
## Using input variables of ie functions:
Lets write a rgxlog program that gets a table in which each row is a strings - string(str).
<br>
The program will create a new table in which each row is a string and it's length.
### First try:


```python
# Step 1: implement an IE function
def length(string):
    yield len(string), 
    
# Step 2: register the function
magic_session.register(length, "Length", [DataTypes.string], [DataTypes.integer])
```


```python
%%rgxlog
# Let's test this solution:
new string(str)
string("a")
string("ab")
string("abc")
string("abcd")

string_length(Str, Len) <- string(Str), Length(Str) -> (Len)
?string_length(Str, Len)
```

    printing results for query 'string_length(Str, Len)':
      Str  |   Len
    -------+-------
     abcd  |     1
     abcd  |     2
     abcd  |     3
     abcd  |     4
      abc  |     4
      abc  |     3
      abc  |     2
      abc  |     1
      ab   |     4
      ab   |     3
      ab   |     2
      ab   |     1
       a   |     4
       a   |     3
       a   |     2
       a   |     1
    


### Looks like something went wrong!
Our goal was to append to each string in the table its length.
What we actually got is the length of each string appended to **all** the strings.
<br>
This happens becuase RGXLog stores all the inputs of each IE function in an input table and all the outputs in an output table. 
Then it's joining the input table with the output table.
<br><br>
Therefore, if we want to associate inputs of an ie function with their output, we need our ie function to do so.
### Second try:


```python
def length2(string):
    #here we append the input to the output inside the ie function!
    yield len(string), string
    
magic_session.register(length2, "Length2", [DataTypes.string], [DataTypes.integer, DataTypes.string])
```


```python
%%rgxlog
string_length_2(Str, Len) <- string(Tmp), Length2(Tmp) -> (Len, Str)
?string_length_2(Str, Len)
```

    printing results for query 'string_length_2(Str, Len)':
      Str  |   Len
    -------+-------
       a   |     1
      ab   |     2
      abc  |     3
     abcd  |     4
    


## Logical Operators:
Suppose we have a table in which each row contains two strings - pair(str, str).
Our goal is to filter all the rows that contain the same value twice.
<br>
In other words, we want to implement the relation **not equals (NEQ)**.

We would like to have a rule such as:
<br>
```unique_pair(X, Y) <- pair(X, Y), X != Y```
<br><br>
Unfortunately RGXLog doesn't support True/False values. Therefore, we can't use ```X != Y```.
<br>
Our solution to this problem is to create an ie function that implements NEQ relation:


```python
magic_session.remove_all_rules()
```


```python
def NEQ(x, y):
    if x != y:
        #return tuples only if they are not equal
        yield x, y
    
    #Other wise nothing is returned
        

in_out_types = [DataTypes.string, DataTypes.string]
magic_session.register(NEQ, "NEQ", in_out_types, in_out_types)
```


```python
%%rgxlog
#Lets test this solution
# new pair(str, str)
pair("Dan", "Tom")
pair("Cat", "Dog")
pair("Apple", "Apple")
pair("Cow", "Cow")
pair("123", "321")

unique_pair(X, Y) <- pair(X, Y), NEQ(X, Y) -> (X, Y)
?unique_pair(X, Y)
```

    printing results for query 'unique_pair(X, Y)':
      X  |  Y
    -----+-----
     123 | 321
     Cat | Dog
     Dan | Tom
    


# Comparing Python and RgxLog in implementing complex control flow

let's try to compare coding in python and coding in rgxlog.
we are given two long strings of enrolled pairs, grades pairs.
our goal is to find all student that are enrolled in biology and chemistry, and have a GPA > 80.

## python 


```python
import re
enrolled = "subaru chemistry subaru biology rem biology ram biology emilia physics roswaal chemistry roswaal biology roswaal physics"
grades = "subaru 80 rem 66 ram 66 roswaal 100 emilia 88"

enrolled_pairs = re.findall(r"(\w+).*?(\w+)", enrolled)
grade_pairs = re.findall(r"(\w+).*?(\d+)", grades)
for student1, course1 in enrolled_pairs:
    for student2, course2 in enrolled_pairs:
        for student3, grade in grade_pairs:
            if (student1 == student2 == student3):
                if (course1 == "biology" and course2 == "chemistry" and int(grade) == 80):
                    print(student1)
```

    subaru


## rgxlog


```python
%%rgxlog
enrolled = "subaru chemistry subaru biology rem biology ram biology emilia physics roswaal chemistry roswaal biology roswaal physics"
grades = "subaru 80 rem 66 ram 66 roswaal 100 emilia 88"

enrolled_in(Student, Course) <- py_rgx_string(enrolled, "(\w+).*?(\w+)")->(Student, Course)
student_grade(Student, Grade) <- py_rgx_string(grades, "(\w+).*?(\d+)") -> (Student, Grade)
interesting_student(X) <- enrolled_in(X, "biology"), enrolled_in(X, "chemistry"), student_grade(X, "80")
?interesting_student(X)
```

    printing results for query 'interesting_student(X)':
       X
    --------
     subaru
    


in this case, the python implementation was long and unnatural. on the other hand, the rgxlog implementation was cleaner and allowed us to express our intentions directly, rather than dealing with annoying nesting and control flow.

# Parsing JSON document using RgxLog

Rgxlog's JsonPath/JsonFullPath ie funciton allows us to easily parse json documents using path expressions.<br>
We will demonstrate how to use this function.
<br>
<br>
Suppose we have a json document of the following format {student: {subject: grade, ...} ,...}
We want to create a rglox relation containg tuples of (student, subject, grade).


```python
%%rgxlog
# we use string as RgxLog doesn't support dicts.
json_string = "{ \
                'abigail': {'chemistry': 80, 'operation systems': 99}, \
                'jordan':  {'chemistry': 65, 'physics': 70}, \
                'gale':    {'operation systems': 100}, \
                'howard':  {'chemistry': 90, 'physics':91, 'biology':92} \
                }"

# path expression is the path to the key of each grade (in our simple case it's *.*)
# than JsonPathFull appends the full path to the value
json_table(Student, Subject, Grade) <- JsonPathFull(json_string, "*.*") -> (Student, Subject, Grade)
?json_table(Student, Subject, Grade)
```

    printing results for query 'json_table(Student, Subject, Grade)':
      Student  |      Subject      |   Grade
    -----------+-------------------+---------
      howard   |      biology      |      92
      howard   |      physics      |      91
      howard   |     chemistry     |      90
       gale    | operation systems |     100
      jordan   |      physics      |      70
      jordan   |     chemistry     |      65
      abigail  | operation systems |      99
      abigail  |     chemistry     |      80
    

