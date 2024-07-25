# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/covid-nlp/000_covid_pipeline.ipynb.

# %% auto 0
__all__ = ['sess', 'nlp', 'slog_file', 'input_dir', 'data_dir', 'lemma_list', 'lemmatizer', 'pos_annotator', 'file_paths',
           'raw_docs', 'lemma_tags', 'lemma_docs', 'lemma_concept_matches', 'lemma_concepts', 'pos_concept_matches',
           'pos_concept_docs', 'target_matches', 'target_rule_docs', 'section_tags', 'section_delimeter_pattern',
           'doc_tags', 'paths', 'classification', 'split_sentence', 'LemmaFromList', 'PosFromList', 'rewrite',
           'rewrite_docs', 'agg_mention', 'AggDocumentTags']

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 27
# importing dependencies
import re
import csv
import pandas as pd
from pandas import DataFrame
from pathlib import Path
from .. import get_magic_session,Session,Span
sess = get_magic_session()

# ! pip install spacy
# ! python -m spacy download en_core_web_sm
import spacy
nlp = spacy.load("en_core_web_sm")


# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 28
# configurations
slog_file = 'covid_logic.pl'
input_dir = Path('sample_inputs')
data_dir = Path('data')

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 34
def split_sentence(text):
    """
    Splits a text into individual sentences. using spacy's sentence detection.
    
    Returns:
        str: Individual sentences extracted from the input text.
    """

    doc = nlp(str(text))
    start = 0
    for sentence in doc.sents:
        end = start+len(sentence.text)
        # note that we yield a Span object, so we can keep track of the locations of the sentences
        yield Span(text,start,end)
        start = end + 1

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 38
class LemmaFromList():
    def __init__(self,lemma_list):
        self.lemma_list = lemma_list

    def __call__(self,text):
        doc = nlp(str(text))
        for word in doc:
            start = word.idx
            end = start + len(word.text)
            if word.lemma_ in self.lemma_list:
                yield (Span(text,start,end),word.lemma_)
            elif word.like_num:
                yield (Span(text,start,end),'like_num')
            else:
                pass

lemma_list = (data_dir/'lemma_words.txt').read_text().split()
lemmatizer = LemmaFromList(lemma_list)

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 40
class PosFromList():
    def __init__(self,pos_list):
        self.pos_list = pos_list
    def __call__(self,text):
        doc = nlp(str(text))
        for word in doc:
            start = word.idx
            end = start + len(word.text)
            if word.pos_ in self.pos_list:
                yield (Span(text,start,end),word.pos_)

pos_annotator = PosFromList(["NOUN", "PROPN", "PRON", "ADJ"])

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 42
sess.register('split_sentence',split_sentence,[(str,Span)],[Span])
sess.register('pos',pos_annotator,[(Span,str)],[Span,str])
sess.register('lemma',lemmatizer,[(Span,str)],[Span,str])

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 48
def rewrite(text,span_label_pairs):
    """rewrites a string given a dataframe with spans and the string to rewrite them to
    assumes that the spans belong to the text

    Args:
        text (str like): string to rewrite
        span_label_pairs (pd.Dataframe) dataframe with two columns, first is spans in the doc to rewrite
            second is what to rewrite to
    Returns:
        The rewritten string
    """    
    if isinstance(text,Span):
        text = text.as_str()
    span_label_pairs = sorted(list(span_label_pairs.itertuples(index=False,name=None)), key=lambda x: x[0].start)

    rewritten_text = ''
    current_pos = 0
    for span,label in span_label_pairs:
        rewritten_text += text[current_pos:span.start] + label 
        current_pos = span.end

    rewritten_text += text[current_pos:]

    return rewritten_text


# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 52
def rewrite_docs(docs,span_label,new_version):
    """Given a dataframe of documents of the form (path,doc,version) and a dataframe of spans to rewrite
    of the form (path,word,from_span,to_tag), rewrites the documents and returns a new dataframe of the form
    (path,doc,new_version)

    """
    new_tuples =[]
    span_label.columns = ['P','D','W','L']
    for path,doc,_ in docs.itertuples(index=False,name=None):
        span_label_per_doc = span_label[span_label['P'] == path][['W','L']]
        new_text = rewrite(doc,span_label_per_doc)
        new_tuples.append((path,new_text,new_version))
    return pd.DataFrame(new_tuples,columns=['P','D','V'])
    

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 56
sess.import_rel("ConceptTagRules",data_dir/"concept_tags_rules.csv" , delim=",")
sess.import_rel("TargetTagRules",data_dir/"target_rules.csv",delim=",")
sess.import_rel("SectionTags",data_dir/"section_tags.csv",delim=",")
sess.import_rel("PositiveSectionTags",data_dir/"positive_section_tags.csv",delim=",")
sess.import_rel("SentenceContextRules",data_dir/'sentence_context_rules.csv',delim="#")
sess.import_rel("PostprocessPatternRules",data_dir/'postprocess_pattern_rules.csv',delim="#")
sess.import_rel("PostprocessRulesWithAttributes",data_dir/'postprocess_attributes_rules.csv',delim="#")
sess.import_rel("NextSentencePostprocessPatternRules",data_dir/'postprocess_pattern_next_sentence_rules.csv',delim=',')


# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 60
from glob import glob
file_paths = [Path(p) for p in glob(str(input_dir/'*.txt'))]
raw_docs = pd.DataFrame([
    [p.name,p.read_text(),'raw_text'] for p in file_paths
],columns=['Path','Doc','Version']
)
sess.import_rel('Docs',raw_docs)
raw_docs

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 64
lemma_tags = sess.export('?Lemmas(P,D,W,L)')
lemma_docs = rewrite_docs(raw_docs,lemma_tags,'lemma')
sess.import_rel('Docs',lemma_docs)


# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 67
lemma_concept_matches = sess.export('?LemmaConceptMatches(Path,Doc,Span,Label)')
display(lemma_concept_matches.map(repr).head())
lemma_concepts = rewrite_docs(lemma_docs,lemma_concept_matches,'lemma_concept')
sess.import_rel('Docs',lemma_concepts)
lemma_concepts.head()

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 71
pos_concept_matches = sess.export('?PosConceptMatches(P,D,W,L)')
display(pos_concept_matches.map(repr).head())

pos_concept_docs = rewrite_docs(lemma_concepts,pos_concept_matches,'pos_concept')
sess.import_rel('Docs',pos_concept_docs)
sess.export('?Docs("sample8.txt",D,V)')

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 74
target_matches = sess.export('?TargetMatches(P,D,W,L)')
display(target_matches.map(repr))
target_rule_docs = rewrite_docs(pos_concept_docs,target_matches,'target_concept')
sess.import_rel('Docs',target_rule_docs)

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 80
section_tags = pd.read_csv(data_dir/'section_tags.csv',names=['literal','tag'])
section_tags.head()

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 81
# we will programatically build a regex that matches all the section patterns
section_delimeter_pattern = section_tags['literal'].str.cat(sep='|')
sess.import_var('section_delimeter_pattern',section_delimeter_pattern)
section_delimeter_pattern

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 105
def agg_mention(group):
    """
    aggregates attribute groups of covid spans
    """
    if 'IGNORE' in group.values:
        return 'IGNORE'
    elif 'negated' in group.values and not 'no_negated' in group.values:
        return 'negated'
    elif 'future' in group.values and not 'no_future' in group.values:
        return 'negated'
    elif 'other experiencer' in group.values or 'not relevant' in group.values:
        return 'negated'
    elif 'positive' in group.values and not 'uncertain' in group.values and not 'no_positive' in group.values:
        return 'positive'
    else:
        return 'uncertain'

#| export
def AggDocumentTags(group):
    """
    Classifies a document as 'POS', 'UNK', or 'NEG' based on COVID-19 attributes.
    """
    if 'positive' in group.values:
        return 'POS'
    elif 'uncertain' in group.values:
        return 'UNK'
    elif 'negated' in group.values:
        return 'NEG'
    else:
        return 'UNK'


sess.register_agg('agg_mention',agg_mention,[str],[str])
sess.register_agg('agg_doc_tags',AggDocumentTags,[str],[str])

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 107
doc_tags = sess.export('?DocumentTags(P,T)')
doc_tags

# %% ../../nbs/covid-nlp/000_covid_pipeline.ipynb 109
paths = pd.DataFrame(file_paths,columns=['P'])
classification = paths.merge(doc_tags,on='P',how='outer')
classification['T']=classification['T'].fillna('UNK')
classification
