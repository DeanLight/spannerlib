# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/callbacks/001_basic_ies.ipynb.

# %% auto 0
__all__ = ['span_arity', 'str_arity', 'object_arity', 'print_ie', 'rgx', 'rgx_split', 'rgx_is_match', 'expr_eval', 'not_ie',
           'as_str', 'span_contained', 'deconstruct_span', 'read', 'read_span']

# %% ../../nbs/callbacks/001_basic_ies.ipynb 3
import re
from typing import Iterable, Sequence,Union
from numbers import Real
from pathlib import Path

from ..span import Span
from ..utils import DefaultIEs,DefaultAGGs,visualize_callback_df

# %% ../../nbs/callbacks/001_basic_ies.ipynb 5
def span_arity(arity):
    """return a schema of Spans with given arity"""
    return [Span]*arity

def str_arity(arity):
    """return a schema of strings with given arity"""
    return [str]*arity

def object_arity(arity):
    """return a schema of objects with given arity"""
    return [object]*arity

# %% ../../nbs/callbacks/001_basic_ies.ipynb 7
def print_ie(
        fstring, # the format string used to print the objects
        *objects, # the objects to be printed
    ):
    """
    prints the objects using the format string fstring to the console
    used for debugging.
    """
    res = fstring.format(*objects)
    print(res)
    return [res]

DefaultIEs().add(
    "print",
    print_ie,
    object_arity,
    [object]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 10
def rgx(pattern: str, # the regex pattern to be matched
    text: Union[str,Span], # the text to be matched on, can be either a string or a span.
    ):
    """
    An IE function which runs regex using python's `re` and 
    yields tuples of spans according to the number of capture groups in the pattern.
    capture groups are ordered by their starting position in the pattern.
    In the case of no capture groups, the function yields a single span of the entire match.
    """
    text = Span(text)
    compiled_rgx = re.compile(pattern)
    num_groups = compiled_rgx.groups
    if num_groups == 0:
        for match in re.finditer(compiled_rgx, str(text)):
            i,j = match.span()
            yield (text[i:j])
    else:
        for match in re.finditer(compiled_rgx, str(text)):
            indices = list((match.span(i) for i in range(1,num_groups+1)))
            yield tuple([text[i:j] for i,j in indices])



DefaultIEs().add(
    'rgx',
    rgx,
    [str, (str,Span)],
    span_arity
)


# %% ../../nbs/callbacks/001_basic_ies.ipynb 17
def rgx_split(delim, # the delimeter pattern to split on
    text, # the text to be split, can be either string or Span
    initial_tag="Start Tag" # the tag to be used incase the first split is not at the start of the text
    ):
    """
    An IE function which given a delimeter rgx pattern and a text, 
    returns tuples of spans of the form (delimeter_match, text_before_next_delimeter).
    Note that rgx pattern should not have any groups.
    """
    delim_iter = rgx(delim,text)
    text = Span(text)
    try:
        first_span = next(delim_iter)
        if first_span.start != 0:
            yield(Span(initial_tag),text[:first_span.start])
    except StopIteration:
        return
    prev_span = first_span
    for next_span in delim_iter:
        yield (prev_span, text[prev_span.end:next_span.start])
        prev_span = next_span

    yield (prev_span, text[prev_span.end:])

DefaultIEs().add(
    'rgx_split',
    rgx_split,
    [str, (str,Span)],
    [Span,Span],
)


# %% ../../nbs/callbacks/001_basic_ies.ipynb 19
def rgx_is_match(delim, # the delimeter pattern to split on
    text, # the text to be split, can be either string or Span
    ):
    """
    An IE function which given a delimeter rgx pattern and a text, 
    returns True if any match is found, False otherwise.
    """
    for _ in rgx(delim,text):
        return [True]
    return [False]

DefaultIEs().add(
    'rgx_is_match',
    rgx_is_match,
    [str, (str,Span)],
    [bool],
)


# %% ../../nbs/callbacks/001_basic_ies.ipynb 22
def expr_eval(template, # The expression template to be evaluated. 
    *inputs, # the inputs to be substituted in the template
    ):
    """
    Evaluate an expression template with the given inputs. 
    The template should contain numerical indices that correspond to the positions of the inputs.

    Returns:
        The result of evaluating the expression template with the given inputs.

    Raises:
        ValueError: If the expression template is invalid or the number of inputs does not match
                    the number of indices in the template.
    """
    try:
        expr = template.format(*[f'arg_{i}' for i in range(len(inputs))])
    except (KeyError, IndexError):
        raise ValueError(f"Invalid expression template {template} for inputs {inputs}\n"
                         f"Make sure the expression template has only numerical indices and the number of inputs match the number of indices")
    yield eval(expr, None, {f'arg_{i}': arg for i, arg in enumerate(inputs)})

DefaultIEs().add(
    'expr_eval',
    expr_eval,
    object_arity,
    [object]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 26
def not_ie(val):
    """
    An IE function which negates the input value.
    """
    return [(not val)]

DefaultIEs().add(
    'not',
    not_ie,
    [bool],
    [bool]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 29
def as_str(obj):
    """casts objects to strings"""
    yield str(obj),

DefaultIEs().add(
    'as_str',
    as_str,
    [object],
    [str]
)


# %% ../../nbs/callbacks/001_basic_ies.ipynb 30
def span_contained(s1, s2):
    """yields True if s1 is contained in s2, otherwise yield False"""
    if s1.doc == s2.doc and s1.start >= s2.start and s1.end <= s2.end:
        yield True
    else:
        yield False

DefaultIEs().add(
    'span_contained',
    span_contained,
    [Span,Span],
    [bool]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 32
def deconstruct_span(span):
    """yields the doc id, start and end of the span"""
    yield span.name, span.start, span.end

DefaultIEs().add(
    'deconstruct_span',
    deconstruct_span,
    [Span],
    [str,int,int]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 34
def read(text_path, # the path to the text file to read from
    ):
    """Reads from file and return it's content as a string"""
    yield Path(text_path).read_text()

# %% ../../nbs/callbacks/001_basic_ies.ipynb 35
def read_span(
    text_path, # the path to the text file to read from
    ):
    """Reads from file and return it's content, as a span with the name of the file as the doc id.
    """
    yield Span(Path(text_path).read_text(),name=text_path)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 36
DefaultIEs().add(
    'read',
    read,
    [str],
    [str]
)

DefaultIEs().add(
    'read_span',
    read_span,
    [str],
    [Span]
)

# %% ../../nbs/callbacks/001_basic_ies.ipynb 40
DefaultAGGs().add('count','count',[object],[int])
DefaultAGGs().add('sum','sum',[Real],[Real])
DefaultAGGs().add('avg','avg',[Real],[Real])
DefaultAGGs().add('max','max',[Real],[Real])
DefaultAGGs().add('min','min',[Real],[Real])
