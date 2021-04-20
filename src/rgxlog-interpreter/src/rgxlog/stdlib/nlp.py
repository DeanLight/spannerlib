from StanfordCoreNLP import StanfordCoreNLP
from rgxlog.engine.datatypes.primitive_types import DataTypes
import json
import spacy

sp = spacy.load('en_core_web_sm')

MY_FILE_PATH = 'C:/Users/tomfe/OneDrive/Desktop/Project/stanford-corenlp-4.1.0'
SERVER_URL = 'http://corenlp.run'
PORT = 80

" ******************************************************************************************************************** "


def tokenize_wrapper(sentence: str):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for token in nlp.tokenize(sentence):
            yield token["token"], token["span"]


Tokenize = dict(ie_function=tokenize_wrapper,
                ie_function_name='Tokenize',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span],
                )

" ******************************************************************************************************************** "


def ssplit_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for s in nlp.ssplit(sentence):
            yield s,


SSplit = dict(ie_function=ssplit_wrapper,
              ie_function_name='SSplit',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string],
              )

" ******************************************************************************************************************** "


def pos_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.pos(sentence):
            yield res["token"], res["pos"], res["span"]


POS = dict(ie_function=pos_wrapper,
           ie_function_name='POS',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
           )

" ******************************************************************************************************************** "


def lemma_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.lemma(sentence):
            yield res["token"], res["lemma"], res["span"]


Lemma = dict(ie_function=lemma_wrapper,
             ie_function_name='Lemma',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
             )

" ******************************************************************************************************************** "


def ner_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.ner(sentence):
            if res["ner"] != 'O':
                yield res["token"], res["ner"], res["span"]


NER = dict(ie_function=ner_wrapper,
           ie_function_name='NER',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
           )

" ******************************************************************************************************************** "


def entitymentions_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.entitymentions(sentence):
            confidence = json.dumps(res["nerConfidences"]).replace("\"", "'")
            yield res["docTokenBegin"], res["docTokenEnd"], res["tokenBegin"], res["tokenEnd"], res["text"], \
                  res["characterOffsetBegin"], res["characterOffsetEnd"], res["ner"], confidence


EntityMentions = dict(ie_function=entitymentions_wrapper,
                      ie_function_name='EntityMentions',
                      in_rel=[DataTypes.string],
                      out_rel=[DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                               DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.string,
                               DataTypes.string]
                      )

" ******************************************************************************************************************** "


# TODO: I can't find how pattern should look like
def regexner_wrapper(sentence, pattern):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.regexner(sentence, pattern):
            raise NotImplementedError()


RGXNer = dict(ie_function=regexner_wrapper,
              ie_function_name='RGXNer',
              in_rel=[DataTypes.string, DataTypes.string],
              out_rel=None
              )

" ******************************************************************************************************************** "


# TODO: I can't find how pattern should look like
def tokensregex_wrapper(sentence, pattern):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.tokensregex(sentence, pattern):
            raise NotImplementedError()


TokensRegex = dict(ie_function=tokensregex_wrapper,
                   ie_function_name='TokensRegex',
                   in_rel=[DataTypes.string, DataTypes.string],
                   out_rel=None
                   )

" ******************************************************************************************************************** "


def cleanxml_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.cleanxml(sentence)["tokens"]:
            yield res['index'], res['word'], res['originalText'], res['characterOffsetBegin'], res['characterOffsetEnd']


CleanXML = dict(ie_function=cleanxml_wrapper,
                ie_function_name='CleanXML',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.integer, DataTypes.integer]
                )

" ******************************************************************************************************************** "


def parse_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.parse(sentence):
            yield res.replace("\n", "<nl>)"),  # pyDatalog doesn't allow '\n' inside a string, <nl> represents new-line


Parse = dict(ie_function=parse_wrapper,
             ie_function_name='Parse',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string]
             )

" ******************************************************************************************************************** "


def dependency_parse_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.dependency_parse(sentence):
            yield res['dep'], res['governor'], res['governorGloss'], res['dependent'], res['dependentGloss']


DepParse = dict(ie_function=dependency_parse_wrapper,
                ie_function_name='DepParse',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.string]
                )

" ******************************************************************************************************************** "


def coref_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.coref(sentence):
            yield res['id'], res['text'], res['type'], res['number'], res['gender'], res['animacy'], res['startIndex'], \
                  res['endIndex'], res['headIndex'], res['sentNum'], \
                  tuple(res['position']), str(res['isRepresentativeMention'])


Coref = dict(ie_function=coref_wrapper,
             ie_function_name='Coref',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.string, DataTypes.string,
                      DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.span, DataTypes.string]
             )

" ******************************************************************************************************************** "


def openie_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for lst in nlp.openie(sentence):
            for res in lst:
                yield res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']), \
                      res['object'], tuple(res['objectSpan'])


OpenIE = dict(ie_function=openie_wrapper,
              ie_function_name='OpenIE',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                       DataTypes.span]
              )

" ******************************************************************************************************************** "


def kbp_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for lst in nlp.kbp(sentence):
            for res in lst:
                yield res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']), \
                      res['object'], tuple(res['objectSpan'])


KBP = dict(ie_function=kbp_wrapper,
           ie_function_name='KBP',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                    DataTypes.span]
           )

" ******************************************************************************************************************** "


# doesn't works because regexlog parser doesn't support strings such as "\"hello\"" (with escapes)
def quote_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.quote(sentence):
            yield res['id'], res['text'], res['beginIndex'], res['endIndex'], res['beginToken'], res['endToken'],
            res['beginSentence'], res['endSentence'], res['speaker'], res['canonicalSpeaker']


Quote = dict(ie_function=quote_wrapper,
             ie_function_name='Quote',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.string, DataTypes.string]
             )

" ******************************************************************************************************************** "


# currently ignoring sentimentTree
def sentiment_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.sentiment(sentence):
            yield int(res['sentimentValue']), res['sentiment'], json.dumps(res['sentimentDistribution'])


Sentiment = dict(ie_function=sentiment_wrapper,
                 ie_function_name='Sentiment',
                 in_rel=[DataTypes.string],
                 out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string]
                 )

" ******************************************************************************************************************** "


def truecase_wrapper(sentence):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for res in nlp.truecase(sentence):
            yield res['token'], res['span'], res['truecase'], res['truecaseText']


TrueCase = dict(ie_function=truecase_wrapper,
                ie_function_name='TrueCase',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.string]
                )

" ******************************************************************************************************************** "


# I don't understand the schema (list of dicts with values of list)
def udfeats_wrapper(sentence: str):
    with StanfordCoreNLP(SERVER_URL, port=PORT) as nlp:
        for token in nlp.udfeats(sentence):
            raise NotImplementedError()


UDFeats = dict(ie_function=udfeats_wrapper,
               ie_function_name='UDFeats',
               in_rel=[DataTypes.string],
               out_rel=None,
               )

" ******************************************************************************************************************** "


def entities(text):
    ent = sp(text).ents
    return ((entity.text, spacy.explain(entity.label_)) for entity in ent)


Entities = dict(ie_function=entities,
                ie_function_name='Entities',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.string]
                )

" ******************************************************************************************************************** "