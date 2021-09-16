"""
this module supports nlp methods. for documentation:
https://stanfordnlp.github.io/CoreNLP/index.html

we are aware that starting the engine inside each method affects efficiency.
still, don't set `core_nlp_engine` as a global variable,
because that way, the java processes will not be killed.
"""
import json
import logging
from io import BytesIO
from os import popen
from pathlib import Path
from zipfile import ZipFile

import jdk
from spanner_nlp.StanfordCoreNLP import StanfordCoreNLP

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.stdlib.utils import download_file_from_google_drive

MIN_VERSION = 1.8

# TODO@niv: we need a server with a copy of this file, their server is not very stable
NLP_URL = "https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl"

NLP_DIR_NAME = 'stanford-corenlp-4.1.0'
CURR_DIR = Path(__file__).parent
NLP_DIR_PATH = str(Path(CURR_DIR) / NLP_DIR_NAME)

JAVA_DOWNLOADER = "install-jdk"
_USER_DIR = Path.home()
INSTALLATION_PATH = _USER_DIR / ".jre"

# @dean: why is enum_spanner_regex and stanford-corenlp in the git tree, did you forget to add them to gitignore?
# TODO@niv: @dean, no - i use enum_spanner_regex for the installation (convenient because we don't have to mess with
#  temporary folders and stuff like that), and stanford-corenlp isn't in the tree

STANFORD_ZIP_GOOGLE_DRIVE_ID = "1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl"
STANFORD_ZIP_NAME = "stanford-corenlp-4.1.0.zip"
STANFORD_ZIP_PATH = CURR_DIR / STANFORD_ZIP_NAME


def _is_installed_nlp():
    return Path(NLP_DIR_PATH).is_dir()


def _install_nlp():
    logging.info(f"Installing {NLP_DIR_NAME} into {CURR_DIR}.")

    if not STANFORD_ZIP_PATH.is_file():
        download_file_from_google_drive(STANFORD_ZIP_GOOGLE_DRIVE_ID, STANFORD_ZIP_PATH)

    with open(STANFORD_ZIP_PATH, "rb") as zipresp:
        with ZipFile(BytesIO(zipresp.read())) as zfile:
            logging.info(f"Extracting files from the zip folder...")
            zfile.extractall(CURR_DIR)

    logging.info("installation completed.")


def _is_installed_java():
    version = popen(
        "java -version 2>&1 | grep 'version' 2>&1 | awk -F\\\" '{ split($2,a,\".\"); print a[1]\".\"a[2]}'").read()

    if len(version) != 0 and float(version) >= MIN_VERSION:
        return True

    return Path(INSTALLATION_PATH).is_dir()


def _run_installation():
    if not _is_installed_nlp():
        _install_nlp()
        assert _is_installed_nlp()
    if not _is_installed_java():
        logging.info(f"Installing JRE into {INSTALLATION_PATH}.")
        jdk.install('8', jre=True)
        if _is_installed_java():
            logging.info("installation completed.")
        else:
            raise IOError("installation failed")


_run_installation()
CoreNLPEngine = StanfordCoreNLP(NLP_DIR_PATH)


# ********************************************************************************************************************

def tokenize_wrapper(sentence: str):
    for token in CoreNLPEngine.tokenize(sentence):
        yield token["token"], token["span"]


Tokenize = dict(ie_function=tokenize_wrapper,
                ie_function_name='Tokenize',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span])


# ********************************************************************************************************************


def ssplit_wrapper(sentence):
    for s in CoreNLPEngine.ssplit(sentence):
        yield s,


SSplit = dict(ie_function=ssplit_wrapper,
              ie_function_name='SSplit',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string])


# ********************************************************************************************************************


def pos_wrapper(sentence):
    for res in CoreNLPEngine.pos(sentence):
        yield res["token"], res["pos"], res["span"]


POS = dict(ie_function=pos_wrapper,
           ie_function_name='POS',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])


# ********************************************************************************************************************


def lemma_wrapper(sentence):
    for res in CoreNLPEngine.lemma(sentence):
        yield res["token"], res["lemma"], res["span"]


Lemma = dict(ie_function=lemma_wrapper,
             ie_function_name='Lemma',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])


# ********************************************************************************************************************


def ner_wrapper(sentence):
    for res in CoreNLPEngine.ner(sentence):
        if res["ner"] != 'O':
            yield res["token"], res["ner"], res["span"]


NER = dict(ie_function=ner_wrapper,
           ie_function_name='NER',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])


# ********************************************************************************************************************


def entitymentions_wrapper(sentence):
    for res in CoreNLPEngine.entitymentions(sentence):
        confidence = json.dumps(res["nerConfidences"]).replace("\"", "'")
        yield (res["docTokenBegin"], res["docTokenEnd"], res["tokenBegin"], res["tokenEnd"], res["text"],
               res["characterOffsetBegin"], res["characterOffsetEnd"], res["ner"], confidence)


EntityMentions = dict(ie_function=entitymentions_wrapper,
                      ie_function_name='EntityMentions',
                      in_rel=[DataTypes.string],
                      out_rel=[DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                               DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.string,
                               DataTypes.string])


# ********************************************************************************************************************


# TODO@tom: I can't find how pattern should look like
def regexner_wrapper(sentence, pattern):
    # for res in CoreNLPEngine.regexner(sentence, pattern):
    raise NotImplementedError()


RGXNer = dict(ie_function=regexner_wrapper,
              ie_function_name='RGXNer',
              in_rel=[DataTypes.string, DataTypes.string],
              out_rel=None)


# ********************************************************************************************************************


# TODO@tom: I can't find how pattern should look like, ADD LINK TO STANFORD NLP
def tokensregex_wrapper(sentence, pattern):
    # for res in CoreNLPEngine.tokensregex(sentence, pattern):
    raise NotImplementedError()


TokensRegex = dict(ie_function=tokensregex_wrapper,
                   ie_function_name='TokensRegex',
                   in_rel=[DataTypes.string, DataTypes.string],
                   out_rel=None)


# ********************************************************************************************************************


def cleanxml_wrapper(sentence):
    for res in CoreNLPEngine.cleanxml(sentence)["tokens"]:
        yield res['index'], res['word'], res['originalText'], res['characterOffsetBegin'], res['characterOffsetEnd']


CleanXML = dict(ie_function=cleanxml_wrapper,
                ie_function_name='CleanXML',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.integer, DataTypes.integer])


# ********************************************************************************************************************


def parse_wrapper(sentence):
    for res in CoreNLPEngine.parse(sentence):
        # note #1: this yields a tuple
        # note #2: we replace the newlines with `<nl> because it is difficult to tell the results apart otherwise
        yield res.replace("\n", "<nl>").replace("\r", ""),


Parse = dict(ie_function=parse_wrapper,
             ie_function_name='Parse',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string])


# ********************************************************************************************************************


def dependency_parse_wrapper(sentence):
    for res in CoreNLPEngine.dependency_parse(sentence):
        yield res['dep'], res['governor'], res['governorGloss'], res['dependent'], res['dependentGloss']


DepParse = dict(ie_function=dependency_parse_wrapper,
                ie_function_name='DepParse',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.string])


# ********************************************************************************************************************


def coref_wrapper(sentence):
    for res in CoreNLPEngine.coref(sentence):
        yield (res['id'], res['text'], res['type'], res['number'], res['gender'], res['animacy'], res['startIndex'],
               res['endIndex'], res['headIndex'], res['sentNum'],
               tuple(res['position']), str(res['isRepresentativeMention']))


Coref = dict(ie_function=coref_wrapper,
             ie_function_name='Coref',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.string, DataTypes.string,
                      DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.span, DataTypes.string])


# ********************************************************************************************************************


def openie_wrapper(sentence):
    for lst in CoreNLPEngine.openie(sentence):
        for res in lst:
            yield (res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']),
                   res['object'], tuple(res['objectSpan']))


OpenIE = dict(ie_function=openie_wrapper,
              ie_function_name='OpenIE',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                       DataTypes.span])


# ********************************************************************************************************************


def kbp_wrapper(sentence):
    for lst in CoreNLPEngine.kbp(sentence):
        for res in lst:
            yield (res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']),
                   res['object'], tuple(res['objectSpan']))


KBP = dict(ie_function=kbp_wrapper,
           ie_function_name='KBP',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                    DataTypes.span])


# ********************************************************************************************************************


def quote_wrapper(sentence):
    for res in CoreNLPEngine.quote(sentence):
        yield (res['id'], res['text'], res['beginIndex'], res['endIndex'], res['beginToken'], res['endToken'],
               res['beginSentence'], res['endSentence'], res['speaker'], res['canonicalSpeaker'])


Quote = dict(ie_function=quote_wrapper,
             ie_function_name='Quote',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.string, DataTypes.string])


# ********************************************************************************************************************


# currently ignoring sentimentTree
def sentiment_wrapper(sentence):
    for res in CoreNLPEngine.sentiment(sentence):
        yield int(res['sentimentValue']), res['sentiment'], json.dumps(res['sentimentDistribution'])


Sentiment = dict(ie_function=sentiment_wrapper,
                 ie_function_name='Sentiment',
                 in_rel=[DataTypes.string],
                 out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string])


# ********************************************************************************************************************


def truecase_wrapper(sentence):
    for res in CoreNLPEngine.truecase(sentence):
        yield res['token'], res['span'], res['truecase'], res['truecaseText']


TrueCase = dict(ie_function=truecase_wrapper,
                ie_function_name='TrueCase',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.string])


# ********************************************************************************************************************

# TODO: a present for future generations
def udfeats_wrapper(sentence: str):
    # for token in CoreNLPEngine.udfeats(sentence):
    raise NotImplementedError()


UDFeats = dict(ie_function=udfeats_wrapper,
               ie_function_name='UDFeats',
               in_rel=[DataTypes.string],
               out_rel=None)
