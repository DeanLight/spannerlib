# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Tutorials/001_basic_tasks.ipynb.

# %% auto 0
__all__ = ['memory', 'string_schema', 'split', 'eq_content_spans', 'span_lt', 'get_client', 'str_to_messages',
           'messages_to_string', 'openai_chat', 'llm', 'llm_ie', 'format_ie']

# %% ../../nbs/Tutorials/001_basic_tasks.ipynb 4
# importing dependencies
import re
import pandas as pd
from pandas import DataFrame
from pathlib import Path
from ..utils import load_env
from .. import get_magic_session,Session,Span

# %% ../../nbs/Tutorials/001_basic_tasks.ipynb 13
# this implementation is naive
# the standard library has a rgx_split ie function that does this in a more efficient way
def split(text):
    split_indices = [ pos for pos,char in enumerate(text) if char == '.' ]
    start = 0
    for pos,char in enumerate(text):
        if char == '.':
            yield Span(text, start, pos)
            start = pos+1


def eq_content_spans(span1, span2):
    # notice that we are yielding a boolean value
    yield span1 != span2 and str(span1).strip() == str(span2).strip()

# %% ../../nbs/Tutorials/001_basic_tasks.ipynb 25
def span_lt(span1, span2):
    yield span1 < span2


# %% ../../nbs/Tutorials/001_basic_tasks.ipynb 39
from ..ie_func.basic import rgx_split
from functools import cache
import openai
from joblib import Memory
memory = Memory("cachedir", verbose=0)

@cache
def get_client():
    return openai.Client()

# we use the rgx_split function to split the string into messages
def str_to_messages (string_prompt):
    return [
        {
            'role': str(role).replace(': ',''),
            'content': str(content)
        } for role,content in rgx_split('system:\s|assistant:\s|user:\s', string_prompt.strip())
    ]
def messages_to_string(msgs):
    return ''.join([f"{msg['content']}" for msg in msgs])

# the specific API we are going to call using the messages interface
def openai_chat(model, messages):
    client = get_client()
    respone = client.chat.completions.create(
        model=model,
        messages=messages,
        seed=42
    )
    return [dict(respone.choices[0].message)]

# we disk cache our function to spare my openAI credits
@memory.cache
def llm(model, question):
    q_msgs = str_to_messages(question)
    a_msgs = openai_chat(model, q_msgs)
    answer = messages_to_string(a_msgs)
    return answer

def llm_ie(model, question):
    return [llm(model, question)]




# %% ../../nbs/Tutorials/001_basic_tasks.ipynb 44
def format_ie(f_string,*params):
    yield f_string.format(*params),

# note that since the schema is dynamic we need to define a function that returns the schema based on the arity
string_schema = lambda x: ([str]*x)
