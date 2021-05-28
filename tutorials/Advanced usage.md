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


NOTE: currently, all sessions share the same engine (same rules and clauses stored inside `PyDatalog`),
so it's probably a bad idea to use more than one at a time.


Using a session manually enables one to dynamically generate queries, facts, and rules

```python
import rgxlog
session = rgxlog.magic_session
```

```python
result = session.run_query('''
    new uncle(str, str)
    uncle("benjen", "jon")''')
```

```python
for maybe_uncle in ['ned','robb','benjen']:
    result = session.run_query(f'?uncle("{maybe_uncle}",Y)')
```

# TODO@niv: remove this whole section after @dean responds


# Changing the session of the magic cells


In cases where you want to work with a custom session, but still make use of the magic system, you can overide the session used by the magic system

```python
import rgxlog  # default session starts here
from rgxlog import Session

another_session=Session()
```

```python
%%rgxlog
# still using the default session
# TODO@niv: dean, why do the sessions share their execution? is this intentional?
# new uncle(str, str)
uncle("bob", "greg")
?uncle(X,Y)
```

```python
print(rgxlog.magic_session._term_graph)
print(another_session._term_graph)
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
subjects=[
    "chemistry",
    "physics",
    "operation_systems",
    "magic",
]

for subject in subjects:
    rule=f"""
    gpa_of_{subject}_students(Student, Grade) <- gpa(Student, Grade), enrolled(Student, "{subject}")
    """
    session.run_query(rule)
    print(rule) # we print the rule here to show you what strings are sent to the session
```

As you can see, we can use the dynamically defined rules in a magic cell

```python
%%rgxlog
?gpa_of_operation_systems_students(X,Y)
```

And we can also query dynamically

```python
subjects=[
    "chemistry",
    "physics",
    "operation_systems",
    "magic",
]

for subject in subjects:
    query=f"""
    ?gpa_of_{subject}_students(Student, Grade)
    """
    session.run_query(query)
```

# Processing the result of a query in python and using the result in a new query


we can add `format_results=True` to `run_query` to get the output as one of the following:
1. `[]`, if the result is false,
2. `[tuple()]`, if the result if true (the tuple is empty), or
3. `pandas.DataFrame`, otherwise-

```python
results = session.run_query(f'''
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
session.run_query('new buddies(str, str)')

for first, second, _ in filtered:
    session.run_query(f'buddies("{first}", "{second}")')

result = session.run_query("?buddies(First, Second)")
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
