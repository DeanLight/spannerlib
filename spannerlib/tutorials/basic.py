# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/tutorials/001_basic_tasks.ipynb.

# %% auto 0
__all__ = ['memory', 'string_schema', 'split', 'eq_content_spans', 'span_lt', 'llm', 'format_ie']

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 4
# importing dependencies
import re
import pandas as pd
from pandas import DataFrame
from pathlib import Path
from ..utils import load_env
from .. import get_magic_session,Session,Span

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 16
# this implementation is naive
# the standard library has a rgx_split ie function that does this in a more efficient way
def split(text):
    split_indices = [ pos for pos,char in enumerate(text) if char == '.' ]
    start = 0
    for pos,char in enumerate(text):
        if char == '.':
            yield Span(text, start, pos)
            start = pos+1

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 17
def eq_content_spans(span1, span2):
    # notice that we are yielding a boolean value
    yield span1 != span2 and str(span1).strip() == str(span2).strip()

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 29
def span_lt(span1, span2):
    yield span1 < span2


# %% ../../nbs/tutorials/001_basic_tasks.ipynb 50
from ..ie_func.basic import rgx_split
from functools import cache
import openai
from joblib import Memory
memory = Memory("cachedir", verbose=0)

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 51
@cache
def _get_client():
    return openai.Client()

# we use the rgx_split function to split the string into messages
def _str_to_messages (string_prompt):
    return [
        {
            'role': str(role).replace(': ',''),
            'content': str(content)
        } for role,content in rgx_split('system:\s|assistant:\s|user:\s', string_prompt.strip())
    ]
def _messages_to_string(msgs):
    return ''.join([f"{msg['content']}" for msg in msgs])

# the specific API we are going to call using the messages interface
def _openai_chat(model, messages):
    client = _get_client()
    respone = client.chat.completions.create(
        model=model,
        messages=messages,
        seed=42
    )
    return [dict(respone.choices[0].message)]

# we disk cache our function to spare my openAI credits
@memory.cache
def llm(model, question):
    q_msgs = _str_to_messages(question)
    a_msgs = _openai_chat(model, q_msgs)
    answer = _messages_to_string(a_msgs)
    # avoid bad fromatting of the answer in the notebook due to nested code blocks
    answer = answer.replace('```','')
    return [answer]

# %% ../../nbs/tutorials/001_basic_tasks.ipynb 56
def format_ie(f_string,*params):
    yield f_string.format(*params)

# note that since the schema is dynamic we need to define a function that returns the schema based on the arity
string_schema = lambda x: ([str]*x)
