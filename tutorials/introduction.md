
# Spanner Workbench Introduction
In this tutorial you will learn the basics of spanner workbench:
* how to import and use RGXlog
* variable assignment
* reading from a file
* declaring a relation
* adding facts
* adding rules
* queries
* using RGXlog's primitive information extractor: functional regex formulas
* using custom information extractors

At the end of this tutorial there is also an example for a small RGXlog program.

# Using RGXlog
In order to use RGXlog, you must first import it:


```python
import rgxlog
```

Now whenever you want to a cell to use RGXlog, simply type '%%spanner' at the beginning
of that cell. For example:


```python
%%spanner
parent("bob", "greg")
```

# Variable assignment
RGXlog allows you to use two types of variables: strings and spans.
The assignment of a string is intuitive:


```python
%%spanner
b = "bob"
b2 = b # b2's value is "bob"
# you can write multiline strings using brackets
b3 = ("this is a multiline "
"string")
b4 = "this is a multiline string" # b4 holds the same value as b3
```

 A span identifies a substring of a string by specifying its bounding indices. It is constructed from two integers.
 You can assign a span value like this:


```python
%%spanner
span1 = [3,7)
span2 = span1 # span2 value is [1,2)
```

# Reading from a file
You can also perform a string assignment by reading from a file. You will need to provide a path to a file by either using a string literal or a string variable:


```python
%%spanner
a = read("path/to/file")
b = "path/to/file" 
c = read(b) # c holds the same string value as a
```

# Derclaring a relation
RGXlog allows you to define and query relations.
You have to declare a relation before you can use it (TBD if rule heads should be declared). Each term in a relation could be a string or a span. Here are some examples for declaring relations:


```python
%%spanner
# 'brothers' is a relation with two string terms.
new brothers(str, str)
# 'confused' is a relation with one string term.
new confused(str)
# 'verb' is a relation with one string term, and one span term 
new verb(str, spn)
```

# Facts
RGXlog is an extension of Datalog, a declarative logic programming language. In Datalog you can declare "facts", essentially adding tuples to a relation. Here's how to do it in RGXlog:


```python
%%spanner
# first declare the relation that you want to use
new noun(str, spn)
# now you can add facts (tuples) to that relation
# this span indicates that a noun "Life" can be found at indexes 0 to 3
noun("Life finds a way", [0,4)) 
# another example
new sisters(str, str)
sisters("alice", "rin")                          
```

# Rules
Datalog allows you to deduce new tuples for a relation.
RGXlog includes this feature as well:


```python
%%spanner
new parent(str ,str)
parent("bob", "greg")
parent("greg", "alice")
# now add a rule that deduce that bob is a grandparent of alice
grandparent(x,z) <- paren(x,y), parent(y,z) # ',' is similar to the 'and' operator
```

# Queries
Querying is very simple in RGXlog. You can query by using string literals, span literals and capture variables:


```python
%%spanner
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
?grandfather("bob", "alice") # returns ("bob", "alice") as alice is bob's grandchild
?grandfather("edward", "alice") # returns nothing as alice is not edward's grandchild
?grandfather("george", x) # returns [("george", "alice"), ("george", "rin")] as both rin
# and alice are george's grandchildren
?grandfather(x, "rin") # returns [("bob", "rin"), ("george", "rin")] (rin's grandfathers)
```

# Functional regex formulas
RGXlog supports information extraction using a regular expressions and named capture groups (for now in rule bodies only).
You will first need to define a string variable either by using a literal or a load from a file, and then you can use the following syntax in a rule body:

extract RGX<f>(x_1, x_2, ...,x_n) from s

where:
* f is a string (TBD if we add regex to the grammar) that repressents regular expression in .NET syntax
* x_1, x_2, ... x_n are capture groups that will appear in the regular expression.
* s is the string variable where the information will be extracted from.
    
For example:


```python
%%spanner
report = "In 2019 we earned 2000 EUR"
annual_earning(year,amount) <- extract RGX<".*(?<year>\d\d\d\d).*(?<amount>\d+)\sEUR">
(year, amount) from report
?annual_earning(x,y) # returns ("2019", 2000)
```

# Custom information extractors
RGXlog allows you to define and use your own information extractors. You can use them only in rule bodies (TBD). The following is the syntax for custom information extractors:

func\<s>(x_1, x_2, ..., x_n)

where:
* func is a IE function that was previously defined (TBD where it was defined)     
* s is a string, a parameter to the function
* x_1, ... x_n are the return values from the function

For example:


```python
%%spanner
new grandmother(str, str)
grandmother("rin", "alice")
grandmother("denna", "joel")
sentence = "rin is happy, denna is sad."
happy_grandmother(x) <- grandmother(x,z),get_happy<sentence>(x)
?happy_grandmother(x) # assuming get_happy returned "rin", also returns "rin"
# TBD: should it return spans instead?
```

# RGXlog program example


```python
%%spanner
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

enrolled_in_chemistry(x) <- enrolled(x, "chemistry")
?enrolled_in_chemistry("jordan") # returns "jordan"
?enrolled_in_chemistry("gale") # returns nothing
?enrolled_in_chemistry(x) # returns "abigail", "jordan" and "howard"

enrolled_in_physics_and_chemistry(x) <- enrolled(x, "chemistry"), enrolled(x, "physics")
?enrolled_in_physics_and_chemistry(x) # returns "howard"

lecturer_of(x,z) <- lecturer(x, y), enrolled(z, y)
?lecturer_of(x,"abigail") # returns ("walter", "abigail"), ("linus", "abigail")

gpa_str = "\n abigail 100\n jordan 80\n gale 79\n howard 60\n"
gpa_of_chemistry_students(student, grade) <- extract 
RGX<".*[\n](?<student>[a-z]+).*(?<grade>\d+).*[\n]">(student, grade) from gpa_str,
enrolled_in_chemistry(student)
?gpa_of_chemistry_students(x, "100") # returns ("abigail", "100")
```
