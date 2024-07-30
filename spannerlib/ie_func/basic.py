# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/ie_func/001_basic_ies.ipynb.

# %% auto 0
__all__ = ['print_ie', 'rgx', 'rgx_split', 'expr_eval', 'as_str', 'span_contained', 'deconstruct_span', 'read', 'read_span']

# %% ../../nbs/ie_func/001_basic_ies.ipynb 3
import re
from typing import Iterable, Sequence
from numbers import Real
from pathlib import Path

from ..span import Span
from ..utils import DefaultIEs,DefaultAGGs

# %% ../../nbs/ie_func/001_basic_ies.ipynb 5
def print_ie(fstring,*objects):
    res = fstring.format(*objects)
    print(res)
    yield res

DefaultIEs().add(
    "print",
    print_ie,
    lambda len: [object]*len,
    [object]
)

# %% ../../nbs/ie_func/001_basic_ies.ipynb 7
DefaultAGGs().add('count','count',[object],[int])
DefaultAGGs().add('sum','sum',[Real],[Real])
DefaultAGGs().add('avg','avg',[Real],[Real])
DefaultAGGs().add('max','max',[Real],[Real])
DefaultAGGs().add('min','min',[Real],[Real])

# %% ../../nbs/ie_func/001_basic_ies.ipynb 9
def rgx(pattern: str, text: str) -> Iterable[Sequence]:
    """
    An IE function which runs regex using python's `re` and yields tuples of strings.

    @param text: The input text for the regex operation.
    @param regex_pattern: the pattern of the regex operation.
    @return: tuples of strings that represents the results.
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
            print(indices)
            yield tuple([text[i:j] for i,j in indices])

DefaultIEs().add(
    'rgx',
    rgx,
    [str, (str,Span)],
    lambda arity: [Span]*arity
)


# %% ../../nbs/ie_func/001_basic_ies.ipynb 17
def rgx_split(delim,text,initial_tag="Start Tag"):
    """
    An IE function which given a delimeter rgx pattern and a text, 
    returns tuples of spans of the form (delimeter_match, text_before_next_delimeter).
    Note that rgx pattern should not have any groups.

    @param delim: the delimeter pattern to use.
    @param text: the text to split
    @return: tuples of strings that represents splitting the text according to delim, 
        yields tuples of the form (delimeter_match, text_before_next_delimeter).
    """
    delim_iter = rgx(delim,text)
    text = Span(text)
    try:
        first_span = next(delim_iter)
        if first_span.start != 0:
            yield(initial_tag,text[:first_span.start])
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


# %% ../../nbs/ie_func/001_basic_ies.ipynb 20
def expr_eval(template,*inputs):
    try:
        expr = template.format(*[f'arg_{i}' for i in range(len(inputs))])
    except (KeyError,IndexError):
        raise ValueError(f"Invalid expression template {template} for inputs {inputs}\n"
                f"make sure the expression template has only numerical indices and the number of inputs match the number of indices")
    yield eval(expr,None,{f'arg_{i}':arg for i,arg in enumerate(inputs)})

DefaultIEs().add(
    'expr_eval',
    expr_eval,
    lambda arity: [object]*arity,
    [object]
)

# %% ../../nbs/ie_func/001_basic_ies.ipynb 25
def as_str(obj):
    yield str(obj),

DefaultIEs().add(
    'as_str',
    as_str,
    [object],
    [str]
)


# %% ../../nbs/ie_func/001_basic_ies.ipynb 26
def span_contained(s1, s2):
    """
    yield True if s1 is contained in s2, otherwise yield False

    Parameters:
        span1 (span)
        span2 (span)

    Returns:
        (s1,s2) if s1 is contained in s2, otherwise returns nothing
    """
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

# %% ../../nbs/ie_func/001_basic_ies.ipynb 28
def deconstruct_span(span):
    """
    yields the doc id, start and end of the span
    """
    yield span.name, span.start, span.end

DefaultIEs().add(
    'deconstruct_span',
    deconstruct_span,
    [Span],
    [str,int,int]
)

# %% ../../nbs/ie_func/001_basic_ies.ipynb 30
def read(text_path):
    """
    Reads from file and return it's content.

    Parameters:
        text_path (str): The path to the text file to read from.

    Returns:
        str: The content of the file.
    """
    yield Path(text_path).read_text()


def read_span(text_path):
    """
    Reads from file and return it's content.

    Parameters:
        text_path (str): The path to the text file to read from.

    Returns:
        str: The content of the file.
    """
    yield Span(Path(text_path).read_text(),name=text_path)

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
