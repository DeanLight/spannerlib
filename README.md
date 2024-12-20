Welcome to Spannerlib
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

Welcome to the spannerlib project.

The spannerlib is a framework for building programming languages that
are a combination of imperative and declarative languages. This
combination is based off of derivations of the document spanner model.

Currently, we implement a language called spannerlog over python.
spannerlog is an extension of statically types datalog which allows
users to define their own ie functions which can be used to derive new
structured information from relations.

The spannerlog repl, shown below is served using the [jupyter magic
commands](https://opensarlab-docs.asf.alaska.edu/user-guides/jupyter_magic/)

Below, we will show you how to install and use spannerlog through
Spannerlib.

For more comprehensive walkthroughs, see our tutorials section.

## Installation

### Unix

To download and install RGXLog run the following commands in your
terminal:

``` bash
git clone https://github.com/DeanLight/spannerlib
cd spannerlib

pip install -e .
```

download corenlp to `spannerlib/rgxlog/`

from [this
link](https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl)

``` bash
# verify everything worked
# first time might take a couple of minutes since run time assets are being configured
python nbdev_test.py
```

### docker

``` bash
git clone https://github.com/DeanLight/spannerlib
cd spannerlib
```

download corenlp to `spannerlib/rgxlog/`

from [this
link](https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl)

``` bash
docker build . -t spannerlib_image

# on windows, change `pwd to current working directory`
# to get a bash terminal to the container
docker run --name swc --rm -it \
  -v `pwd`:/spannerlib:Z \
  spannerlib_image bash

# to run an interactive notebook on host port 8891
docker run --name swc --rm -it \
  -v `pwd`:/spannerlib:Z \
  -p8891:8888 \
  spannerlib_image jupyter notebook --no-browser --allow-root

#Verify tests inside the container
python /spannerlib/nbdev_test.py
```

## Getting started - TLDR

Here is a TLDR intro, for a more comprehensive tutorial, please see the
introduction section of the tutorials.

``` python
import spannerlib
import pandas as pd
# get dynamic access to the session running through the jupyter magic system
from spannerlib import get_magic_session
session = get_magic_session()
```

Get a dataframe

``` python
lecturer_df = pd.DataFrame(
    [["walter","chemistry"],
     ["linus", "operating_systems"],
     ['rick', 'physics']
    ],columns=["name","course"])
lecturer_df
```

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>name</th>
      <th>course</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>walter</td>
      <td>chemistry</td>
    </tr>
    <tr>
      <th>1</th>
      <td>linus</td>
      <td>operating_systems</td>
    </tr>
    <tr>
      <th>2</th>
      <td>rick</td>
      <td>physics</td>
    </tr>
  </tbody>
</table>
</div>

Or a CSV

``` python
pd.read_csv('sample_data/example_students.csv',names=["name","course"])
```

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>name</th>
      <th>course</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>abigail</td>
      <td>chemistry</td>
    </tr>
    <tr>
      <th>1</th>
      <td>abigail</td>
      <td>operation systems</td>
    </tr>
    <tr>
      <th>2</th>
      <td>jordan</td>
      <td>chemistry</td>
    </tr>
    <tr>
      <th>3</th>
      <td>gale</td>
      <td>operation systems</td>
    </tr>
    <tr>
      <th>4</th>
      <td>howard</td>
      <td>chemistry</td>
    </tr>
    <tr>
      <th>5</th>
      <td>howard</td>
      <td>physics</td>
    </tr>
  </tbody>
</table>
</div>

Import them to the session

``` python
session.import_rel("lecturer",lecturer_df)
session.import_rel("enrolled","sample_data/enrolled.csv",delim=",")
```

They can even be documents

``` python
documents = pd.DataFrame([
    ["abigail is happy, but walter did not approve"],
    ["howard is happy, gale is happy, but jordan is sad"]
])
session.import_rel("documents",documents)
```

``` python
%%spannerlog
?documents(X)
```

    '?documents(X)'

<style type="text/css">
#T_dec8a_row0_col0, #T_dec8a_row1_col0 {
  overflow-wrap: break-word;
  max-width: 800px;
  text-align: left;
}
</style>
<table id="T_dec8a" class="display nowrap"style="table-layout:auto;width:auto;margin:auto;caption-side:bottom">
  <thead>
    <tr>
      <th id="T_dec8a_level0_col0" class="col_heading level0 col0" >X</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td id="T_dec8a_row0_col0" class="data row0 col0" >abigail is happy, but walter did not approve</td>
    </tr>
    <tr>
      <td id="T_dec8a_row1_col0" class="data row1 col0" >howard is happy, gale is happy, but jordan is sad</td>
    </tr>
  </tbody>
</table>

<link href="https://www.unpkg.com/dt_for_itables@2.0.11/dt_bundle.css" rel="stylesheet">
<script type="module">
    import {DataTable, jQuery as $} from 'https://www.unpkg.com/dt_for_itables@2.0.11/dt_bundle.js';

    document.querySelectorAll("#T_dec8a:not(.dataTable)").forEach(table => {
        // Define the table data
        

        // Define the dt_args
        let dt_args = {"columnDefs": [{"targets": ["X"], "render": function(data, type, row) {
                    return '<div style="white-space: normal; word-wrap: break-word;">' + data + '</div>';
                }, "width": "300px"}], "escape": true, "layout": {"topStart": null, "topEnd": null, "bottomStart": null, "bottomEnd": null}, "display_logo_when_loading": true, "order": []};
        

        
        new DataTable(table, dt_args);
    });
</script>

Define your own IE functions to extract information from relations

``` python
# the function itself, writing it as a python generator makes your data processing lazy
def get_happy(text):
    """
    get the names of people who are happy in `text`
    """
    import re

    compiled_rgx = re.compile("(\w+) is happy")
    num_groups = compiled_rgx.groups
    for match in re.finditer(compiled_rgx, text):
        if num_groups == 0:
            matched_strings = [match.group()]
        else:
            matched_strings = [group for group in match.groups()]
        yield matched_strings

# register the ie function with the session
session.register(
    "get_happy", # name of the function
    get_happy, # the function itself
    [str], # input types
    [str] # output types
)
```

rgxlog supports relations over the following primitive types \* strings
\* spans \* integers

Write a rgxlog program (like datalog but you can use your own ie
functions)

``` python
session.remove_all_rules()
```

``` python
%%spannerlog
# you can also define data inline via a statically typed variant of datalog syntax
new sad_lecturers(str)
sad_lecturers("walter")
sad_lecturers("linus")

# and include primitive variable
gpa_doc = "abigail 100 jordan 80 gale 79 howard 60"

# define datalog rules
enrolled_in_chemistry(X) <- enrolled(X, "chemistry").
enrolled_in_physics_and_chemistry(X) <- enrolled_in_chemistry(X), enrolled(X, "physics").

# and query them inline (to print to screen)
# ?enrolled_in_chemistry("jordan") # returns empty tuple ()
# ?enrolled_in_chemistry("gale") # returns nothing
# ?enrolled_in_chemistry(X) # returns "abigail", "jordan" and "howard"
# ?enrolled_in_physics_and_chemistry(X) # returns "howard"

lecturer_of(X,Z) <- lecturer(X,Y), enrolled(Z,Y).

# use ie functions in body clauses to extract structured data from unstructured data

# standard ie functions like regex are already registered
student_gpas(Student, Grade) <- 
    rgx("(\w+).*?(\d+)",$gpa_doc)->(StudentSpan, GradeSpan),
    as_str(StudentSpan)->(Student), as_str(GradeSpan)->(Grade).

# and you can use your defined functions as well
happy_students_with_sad_lecturers_and_their_gpas(Student, Grade, Lecturer) <-
    documents(Doc),
    get_happy(Doc)->(Student),
    sad_lecturers(Lecturer),
    lecturer_of(Lecturer,Student),
    student_gpas(Student, Grade).
```

And query it

``` python
%%spannerlog
?happy_students_with_sad_lecturers_and_their_gpas(Stu,Gpa,Lec)
```

    '?happy_students_with_sad_lecturers_and_their_gpas(Stu,Gpa,Lec)'

<style type="text/css">
#T_d313a_row0_col0, #T_d313a_row0_col1, #T_d313a_row0_col2, #T_d313a_row1_col0, #T_d313a_row1_col1, #T_d313a_row1_col2, #T_d313a_row2_col0, #T_d313a_row2_col1, #T_d313a_row2_col2 {
  overflow-wrap: break-word;
  max-width: 800px;
  text-align: left;
}
</style>
<table id="T_d313a" class="display nowrap"style="table-layout:auto;width:auto;margin:auto;caption-side:bottom">
  <thead>
    <tr>
      <th id="T_d313a_level0_col0" class="col_heading level0 col0" >Stu</th>
      <th id="T_d313a_level0_col1" class="col_heading level0 col1" >Gpa</th>
      <th id="T_d313a_level0_col2" class="col_heading level0 col2" >Lec</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td id="T_d313a_row0_col0" class="data row0 col0" >abigail</td>
      <td id="T_d313a_row0_col1" class="data row0 col1" >100</td>
      <td id="T_d313a_row0_col2" class="data row0 col2" >linus</td>
    </tr>
    <tr>
      <td id="T_d313a_row1_col0" class="data row1 col0" >gale</td>
      <td id="T_d313a_row1_col1" class="data row1 col1" >79</td>
      <td id="T_d313a_row1_col2" class="data row1 col2" >linus</td>
    </tr>
    <tr>
      <td id="T_d313a_row2_col0" class="data row2 col0" >howard</td>
      <td id="T_d313a_row2_col1" class="data row2 col1" >60</td>
      <td id="T_d313a_row2_col2" class="data row2 col2" >walter</td>
    </tr>
  </tbody>
</table>

<link href="https://www.unpkg.com/dt_for_itables@2.0.11/dt_bundle.css" rel="stylesheet">
<script type="module">
    import {DataTable, jQuery as $} from 'https://www.unpkg.com/dt_for_itables@2.0.11/dt_bundle.js';

    document.querySelectorAll("#T_d313a:not(.dataTable)").forEach(table => {
        // Define the table data
        

        // Define the dt_args
        let dt_args = {"columnDefs": [{"targets": ["Stu", "Gpa", "Lec"], "render": function(data, type, row) {
                    return '<div style="white-space: normal; word-wrap: break-word;">' + data + '</div>';
                }, "width": "300px"}], "escape": true, "layout": {"topStart": null, "topEnd": null, "bottomStart": null, "bottomEnd": null}, "display_logo_when_loading": true, "order": []};
        

        
        new DataTable(table, dt_args);
    });
</script>

You can also get query results as Dataframes for downstream processing

``` python
df = session.export(
    "?happy_students_with_sad_lecturers_and_their_gpas(Stu,Gpa,Lec)")
df
```

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Stu</th>
      <th>Gpa</th>
      <th>Lec</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>abigail</td>
      <td>100</td>
      <td>linus</td>
    </tr>
    <tr>
      <th>1</th>
      <td>gale</td>
      <td>79</td>
      <td>linus</td>
    </tr>
    <tr>
      <th>2</th>
      <td>howard</td>
      <td>60</td>
      <td>walter</td>
    </tr>
  </tbody>
</table>
</div>

## Additional Resources

### Relevant papers

- [spannerlog](https://dl.acm.org/doi/10.1145/2932194.2932200)
- [Recursive
  RGXLog](https://drops.dagstuhl.de/opus/volltexte/2019/10315/pdf/LIPIcs-ICDT-2019-13.pdf)
