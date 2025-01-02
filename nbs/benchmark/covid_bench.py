import time
import os

from glob import glob
import pandas as pd
import spacy
from pandas import DataFrame
from pathlib import Path
from spannerlib import get_magic_session,Session
from spannerlib.ie_func.basic import rgx, rgx_split, rgx_is_match, span_contained, span_arity

VERSION = "SPANNERFLOW"
if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
    from spannerflow.span import Span
else:
    from spannerlib import Span


nlp = spacy.load("en_core_web_sm")

# configurations
if VERSION == "SPANNERFLOW_PYTHON_IE":
    slog_file = Path('covid_bench_logic_python_ie.pl')
else:
    slog_file = Path('covid_bench_logic.pl')
input_dir = Path('covid_data/sample_inputs')
data_dir = Path('covid_data/rules_data')


def is_adjacent(span1,span2):
    yield span1.name==span2.name and span1.end +1 == span2.start


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

def agg_mention(group):
    """
    aggregates attribute groups of covid spans
    """
    if VERSION == "OLD":
        group = group.values
    if 'IGNORE' in group:
        return 'IGNORE'
    elif 'negated' in group and not 'no_negated' in group:
        return 'negated'
    elif 'future' in group and not 'no_future' in group:
        return 'negated'
    elif 'other experiencer' in group or 'not relevant' in group:
        return 'negated'
    elif 'positive' in group and not 'uncertain' in group and not 'no_positive' in group:
        return 'positive'
    else:
        return 'uncertain'

def AggDocumentTags(group):
    """
    Classifies a document as 'POS', 'UNK', or 'NEG' based on COVID-19 attributes.
    """
    if VERSION == "OLD":
        group = group.values
    if 'positive' in group:
        return 'POS'
    elif 'uncertain' in group:
        return 'UNK'
    elif 'negated' in group:
        return 'NEG'
    else:
        return 'UNK'

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

file_paths = []
def main(input_dir,data_dir,logic_file, start=0, end=10, cache=None):
    global file_paths
    sess = Session()
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"] and cache:
        sess.engine.spannerflow_engine.set_cache(cache)
    
    sess.register('py_rgx', rgx, [str, Span], span_arity)
    sess.register('py_rgx_split', rgx_split, [str, Span], [Span,Span])
    sess.register('py_rgx_is_match', rgx_is_match, [str, Span], [bool])
    sess.register('py_span_contained', span_contained, [Span, Span], [bool])
    sess.register('is_adjacent',is_adjacent,[Span,Span],[bool])
    # define callback functions
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.register('split_sentence',split_sentence,[Span],[Span])
        sess.register('pos',pos_annotator,[Span],[Span,str])
        sess.register('lemma',lemmatizer,[Span],[Span,str])
    else:
        sess.register('split_sentence',split_sentence,[str],[Span])
        sess.register('pos',pos_annotator,[str],[Span,str])
        sess.register('lemma',lemmatizer,[str],[Span,str])
    sess.register_agg('agg_mention',agg_mention,[str],[str])
    sess.register_agg('agg_doc_tags',AggDocumentTags,[str],[str])
    
    # bring in code as data
    sess.import_rel("ConceptTagRules",data_dir/"concept_tags_rules.csv" , delim=",")
    sess.import_rel("TargetTagRules",data_dir/"target_rules.csv",delim=",")
    sess.import_rel("SectionTags",data_dir/"section_tags.csv",delim=",")
    sess.import_rel("PositiveSectionTags",data_dir/"positive_section_tags.csv",delim=",")
    sess.import_rel("SentenceContextRules",data_dir/'sentence_context_rules.csv',delim="#")
    sess.import_rel("PostprocessPatternRules",data_dir/'postprocess_pattern_rules.csv',delim="#")
    sess.import_rel("PostprocessRulesWithAttributes",data_dir/'postprocess_attributes_rules.csv',delim="#")
    sess.import_rel("NextSentencePostprocessPatternRules",data_dir/'postprocess_pattern_next_sentence_rules.csv',delim=',')


    # we will programatically build a regex that matches all the section patterns
    section_tags = pd.read_csv(data_dir/'section_tags.csv',names=['literal','tag'])
    section_delimeter_pattern = section_tags['literal'].str.cat(sep='|')
    sess.import_var('section_delimeter_pattern',section_delimeter_pattern)

    # bring in data
    file_paths = [Path(f"{input_dir}/sample{i}.txt") for i in range(start, end)]
    raw_docs = pd.DataFrame([
        [p.name,p.read_text(),'raw_text'] for p in file_paths
    ],columns=['Path','Doc','Version']
    )
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.import_rel('Docs',raw_docs, scheme=[str, Span, str])
    else:
        sess.import_rel('Docs',raw_docs)

    # load logic, note that since we did not define the data relations in the logic file,
    # we need to load the logic after the data has been loaded
    sess.export(logic_file.read_text())

    ## Rewritting the documents
    lemma_tags = sess.export('?Lemmas(P,D,W,L)')
    lemma_docs = rewrite_docs(raw_docs,lemma_tags,'lemma')
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.import_rel('Docs',lemma_docs, scheme=[str, Span, str])
    else:
        sess.import_rel('Docs',lemma_docs)
    

    lemma_concept_matches = sess.export('?LemmaConceptMatches(Path,Doc,Span,Label)')
    lemma_concepts = rewrite_docs(lemma_docs,lemma_concept_matches,'lemma_concept')
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.import_rel('Docs',lemma_concepts, scheme=[str, Span, str])
    else:
        sess.import_rel('Docs',lemma_concepts)

    pos_concept_matches = sess.export('?PosConceptMatches(P,D,W,L)')
    pos_concept_docs = rewrite_docs(lemma_concepts,pos_concept_matches,'pos_concept')
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.import_rel('Docs',pos_concept_docs, scheme=[str, Span, str])
    else:
        sess.import_rel('Docs',pos_concept_docs)

    target_matches = sess.export('?TargetMatches(P,D,W,L)')
    target_rule_docs = rewrite_docs(pos_concept_docs,target_matches,'target_concept')
    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        sess.import_rel('Docs',target_rule_docs, scheme=[str, Span, str])
    else:
        sess.import_rel('Docs',target_rule_docs)

    ## computing the tags based on the target concept documents
    doc_tags = sess.export('?DocumentTags(P,T)')

    # handling files with no mentions
    paths = pd.DataFrame([p.name for p in file_paths],columns=['P'])
    classification = paths.merge(doc_tags,on='P',how='outer')
    classification['T']=classification['T'].fillna('UNK')

    if VERSION in ["SPANNERFLOW", "SPANNERFLOW_PYTHON_IE"]:
        cache = sess.engine.spannerflow_engine.get_cache()
    return cache, classification


def run_benchmark(k, steps, write_to_file=True):
    start_time = time.time()
    round = 1 
    cache = {}
    last_round_end_time = start_time
    print(f"Running benchmark for {k} samples with batch size {steps}")
    round_times = []
    for i in range(1, k+1, steps):
        cache, res = main(input_dir,data_dir,slog_file, start=i, end=i+steps, cache=cache)
        current_time = time.time()
        res.to_csv(f'covid_data/results/{start_time}-{VERSION}.csv', index=False, mode='a')
        round_times.append(current_time-last_round_end_time)
        print(f"Time taken for round {round}: {current_time-last_round_end_time:.2f} seconds")
        round += 1
        last_round_end_time = current_time

    end_time = time.time()
    df = pd.DataFrame(round_times, columns=['RoundTime'])
    if write_to_file:
        file_path = f"covid_data/time-results/{VERSION}-batch-size-{steps}-total-size-{k}.csv"
        df.to_csv(file_path, index=False)
    return df

if __name__ == "__main__":
    os.makedirs("covid_data/results", exist_ok=True)
    os.makedirs("covid_data/time-results", exist_ok=True)
    
    # AVG BATCH Size - Run per implementation
    results = []
    # for batch_size in range(110, 210, 10):
    #     time_result = run_benchmark(10*batch_size, batch_size)
    #     avg_with_first = time_result.mean().values[0]
    #     avg_without_first = time_result[1:].mean().values[0]
    #     results.append((batch_size, avg_with_first, avg_without_first))

    # avg_df = pd.DataFrame(results, columns=['BatchSize', 'AvgWithFirst', 'AvgWithoutFirst'])
    # avg_df.to_csv(f'covid_data/time-results/{VERSION}-avg-batch-time-results.csv', index=False)

    # Total run time for number of total samples for batch size 25
    #run_benchmark(6000, 25)

    # Total run time for number of total samples for batch size 50
    #run_benchmark(6000, 50)

    # Total run time for number of total samples for batch size 100
    run_benchmark(10000, 5000)
