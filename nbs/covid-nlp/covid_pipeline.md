# Covid-19 NLP Pipeline
### Tutorial Introduction:
In this tutorial, we will guide you through the process of re-writing an existing data pipeline into the rgxlog framework, allowing you to witness a real-world example of the framework's benefits. And to offer further tutorials on advanced applications of the rgxlog framework.
We've chosen to adapt a pipeline from the field of NLP, specifically the Covid-19 NLP pipeline, which was a part of a published [paper](https://aclanthology.org/2020.nlpcovid19-acl.10.pdf) in 2020.

### Understanding The Covid-19 NLP Pipeline:
The pipline repository [link](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/).


The primary objective of the NLP pipeline is to identify individuals who have been positively diagnosed with COVID-19 by extracting pertinent information from unstructured free-text narratives found within the Electronic Health Record (EHR) of the Department of Veterans Affairs (VA). By automating this process, the pipeline streamlines the screening of a substantial volume of clinical text, significantly reducing the time and effort required for identification.
The pipeline is built on medSpacy framework, and defines a new UI to use.

### Pipline Stages:
![image-6.png](covid_pipeline_files/image-6.png)
- preprocessor: Modifies the preprocessed text
- concept tagger: Assigns a semantic tag in a custom attribute to each Token, which helps with concept extraction and normalization.
- target matcher: Extracts spans using rules, based on the concept tagger.
- sectionizer: Identifies note section headers in the text and assigns section titles to entities and tokens contained in that section.
- context: Identifies semantic modifiers of entities and asserts attributes such as positive status, negation, and other experiencier.
- postprocessor: Modifies or removes the entity based on business logic. This handles special cases or complex logic using the results of earlier stages.
- document classifier: Assigns a label of "POS", "UNK", or "NEG" to each file, A document will be classified as positive if it has at least one positive, non-excluded entity
We will explain about each stage in more details later on.

At each stage, we encountered unique challenges. Each stage involved working with different classes and medSpacy framework attributes. Our approach was to first understand the original implementation, seek opportunities to simplify it, and then rewrite it in rgxlog. What was possible we wrote it declaratively using rules, facts, and queries. Additionally, if any essential functionalities were missing in the library, we built IE functions.
As we mentioned the pipline uses medSpacy framework so first we need to import some libraries and install some requirements.

### Tutorial Index:
- [Setting Up the Environment](#setting-up-the-environment)
- [Pipeline Input](#pipeline-input)
- [Concept tagger](#concept-tag-rules)
- [Target matcher](#target-rules)
- [Sectionizer](#section-rules)
- [Context matcher](#context-rules)
- [Postprocessor](#postprocess-rules)
- [Document Classifier](#document_classifier)
- [Bringing It All Together](#bringing-all-together)


## Start Of The Implementation:

<a id='setting-up-the-environment'></a>
### Setting Up The Environment:

We need to install some requirements to work with [medspacy](https://github.com/medspacy/medspacy) framework 


```
#| output: false
!pip install spacy
!python -m spacy download en_core_web_sm
```

    Requirement already satisfied: spacy in /miniconda/lib/python3.8/site-packages (3.7.2)
    Requirement already satisfied: pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4 in /miniconda/lib/python3.8/site-packages (from spacy) (2.5.3)
    Requirement already satisfied: smart-open<7.0.0,>=5.2.1 in /miniconda/lib/python3.8/site-packages (from spacy) (6.4.0)
    Requirement already satisfied: weasel<0.4.0,>=0.1.0 in /miniconda/lib/python3.8/site-packages (from spacy) (0.3.4)
    Requirement already satisfied: jinja2 in /miniconda/lib/python3.8/site-packages (from spacy) (3.1.2)
    Requirement already satisfied: catalogue<2.1.0,>=2.0.6 in /miniconda/lib/python3.8/site-packages (from spacy) (2.0.10)
    Requirement already satisfied: requests<3.0.0,>=2.13.0 in /miniconda/lib/python3.8/site-packages (from spacy) (2.28.1)
    Requirement already satisfied: murmurhash<1.1.0,>=0.28.0 in /miniconda/lib/python3.8/site-packages (from spacy) (1.0.10)
    Requirement already satisfied: srsly<3.0.0,>=2.4.3 in /miniconda/lib/python3.8/site-packages (from spacy) (2.4.8)
    Requirement already satisfied: spacy-loggers<2.0.0,>=1.0.0 in /miniconda/lib/python3.8/site-packages (from spacy) (1.0.5)
    Requirement already satisfied: thinc<8.3.0,>=8.1.8 in /miniconda/lib/python3.8/site-packages (from spacy) (8.2.2)
    Requirement already satisfied: langcodes<4.0.0,>=3.2.0 in /miniconda/lib/python3.8/site-packages (from spacy) (3.3.0)
    Requirement already satisfied: preshed<3.1.0,>=3.0.2 in /miniconda/lib/python3.8/site-packages (from spacy) (3.0.9)
    Requirement already satisfied: spacy-legacy<3.1.0,>=3.0.11 in /miniconda/lib/python3.8/site-packages (from spacy) (3.0.12)
    Requirement already satisfied: cymem<2.1.0,>=2.0.2 in /miniconda/lib/python3.8/site-packages (from spacy) (2.0.8)
    Requirement already satisfied: typer<0.10.0,>=0.3.0 in /miniconda/lib/python3.8/site-packages (from spacy) (0.9.0)
    Requirement already satisfied: setuptools in /miniconda/lib/python3.8/site-packages (from spacy) (65.6.3)
    Requirement already satisfied: numpy>=1.15.0 in /miniconda/lib/python3.8/site-packages (from spacy) (1.24.3)
    Requirement already satisfied: wasabi<1.2.0,>=0.9.1 in /miniconda/lib/python3.8/site-packages (from spacy) (1.1.2)
    Requirement already satisfied: packaging>=20.0 in /miniconda/lib/python3.8/site-packages (from spacy) (22.0)
    Requirement already satisfied: tqdm<5.0.0,>=4.38.0 in /miniconda/lib/python3.8/site-packages (from spacy) (4.64.1)
    Requirement already satisfied: typing-extensions>=4.6.1 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy) (4.6.2)
    Requirement already satisfied: annotated-types>=0.4.0 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy) (0.6.0)
    Requirement already satisfied: pydantic-core==2.14.6 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy) (2.14.6)
    Requirement already satisfied: idna<4,>=2.5 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy) (3.4)
    Requirement already satisfied: certifi>=2017.4.17 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy) (2022.12.7)
    Requirement already satisfied: urllib3<1.27,>=1.21.1 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy) (1.25.8)
    Requirement already satisfied: charset-normalizer<3,>=2 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy) (2.0.4)
    Requirement already satisfied: confection<1.0.0,>=0.0.1 in /miniconda/lib/python3.8/site-packages (from thinc<8.3.0,>=8.1.8->spacy) (0.1.4)
    Requirement already satisfied: blis<0.8.0,>=0.7.8 in /miniconda/lib/python3.8/site-packages (from thinc<8.3.0,>=8.1.8->spacy) (0.7.11)
    Requirement already satisfied: click<9.0.0,>=7.1.1 in /miniconda/lib/python3.8/site-packages (from typer<0.10.0,>=0.3.0->spacy) (8.1.7)
    Requirement already satisfied: cloudpathlib<0.17.0,>=0.7.0 in /miniconda/lib/python3.8/site-packages (from weasel<0.4.0,>=0.1.0->spacy) (0.16.0)
    Requirement already satisfied: MarkupSafe>=2.0 in /miniconda/lib/python3.8/site-packages (from jinja2->spacy) (2.1.2)
    [33mWARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv[0m[33m
    [0mCollecting en-core-web-sm==3.7.1
      Downloading https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl (12.8 MB)
    [2K     [90m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[0m [32m12.8/12.8 MB[0m [31m7.5 MB/s[0m eta [36m0:00:00[0m00:01[0m00:01[0m
    [?25hRequirement already satisfied: spacy<3.8.0,>=3.7.2 in /miniconda/lib/python3.8/site-packages (from en-core-web-sm==3.7.1) (3.7.2)
    Requirement already satisfied: preshed<3.1.0,>=3.0.2 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (3.0.9)
    Requirement already satisfied: requests<3.0.0,>=2.13.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.28.1)
    Requirement already satisfied: pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.5.3)
    Requirement already satisfied: murmurhash<1.1.0,>=0.28.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (1.0.10)
    Requirement already satisfied: cymem<2.1.0,>=2.0.2 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.0.8)
    Requirement already satisfied: spacy-loggers<2.0.0,>=1.0.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (1.0.5)
    Requirement already satisfied: weasel<0.4.0,>=0.1.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.3.4)
    Requirement already satisfied: langcodes<4.0.0,>=3.2.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (3.3.0)
    Requirement already satisfied: numpy>=1.15.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (1.24.3)
    Requirement already satisfied: smart-open<7.0.0,>=5.2.1 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (6.4.0)
    Requirement already satisfied: srsly<3.0.0,>=2.4.3 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.4.8)
    Requirement already satisfied: setuptools in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (65.6.3)
    Requirement already satisfied: spacy-legacy<3.1.0,>=3.0.11 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (3.0.12)
    Requirement already satisfied: thinc<8.3.0,>=8.1.8 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (8.2.2)
    Requirement already satisfied: wasabi<1.2.0,>=0.9.1 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (1.1.2)
    Requirement already satisfied: jinja2 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (3.1.2)
    Requirement already satisfied: typer<0.10.0,>=0.3.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.9.0)
    Requirement already satisfied: packaging>=20.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (22.0)
    Requirement already satisfied: catalogue<2.1.0,>=2.0.6 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.0.10)
    Requirement already satisfied: tqdm<5.0.0,>=4.38.0 in /miniconda/lib/python3.8/site-packages (from spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (4.64.1)
    Requirement already satisfied: annotated-types>=0.4.0 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.6.0)
    Requirement already satisfied: typing-extensions>=4.6.1 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (4.6.2)
    Requirement already satisfied: pydantic-core==2.14.6 in /miniconda/lib/python3.8/site-packages (from pydantic!=1.8,!=1.8.1,<3.0.0,>=1.7.4->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.14.6)
    Requirement already satisfied: idna<4,>=2.5 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (3.4)
    Requirement already satisfied: charset-normalizer<3,>=2 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.0.4)
    Requirement already satisfied: certifi>=2017.4.17 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2022.12.7)
    Requirement already satisfied: urllib3<1.27,>=1.21.1 in /miniconda/lib/python3.8/site-packages (from requests<3.0.0,>=2.13.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (1.25.8)
    Requirement already satisfied: confection<1.0.0,>=0.0.1 in /miniconda/lib/python3.8/site-packages (from thinc<8.3.0,>=8.1.8->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.1.4)
    Requirement already satisfied: blis<0.8.0,>=0.7.8 in /miniconda/lib/python3.8/site-packages (from thinc<8.3.0,>=8.1.8->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.7.11)
    Requirement already satisfied: click<9.0.0,>=7.1.1 in /miniconda/lib/python3.8/site-packages (from typer<0.10.0,>=0.3.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (8.1.7)
    Requirement already satisfied: cloudpathlib<0.17.0,>=0.7.0 in /miniconda/lib/python3.8/site-packages (from weasel<0.4.0,>=0.1.0->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (0.16.0)
    Requirement already satisfied: MarkupSafe>=2.0 in /miniconda/lib/python3.8/site-packages (from jinja2->spacy<3.8.0,>=3.7.2->en-core-web-sm==3.7.1) (2.1.2)
    [33mWARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv[0m[33m
    [0m[38;5;2m✔ Download and installation successful[0m
    You can now load the package via spacy.load('en_core_web_sm')
    


```
import spacy
```

Installing the rgxlog framework and import what we need from the rgxlog framework


```
import sys
from pathlib import Path
current_python=f"{sys.executable}"
package_path=Path("../..")
```


```
#| output: false
! {current_python} -m pip install {package_path}
```

    Processing /spanner_workbench
      Preparing metadata (setup.py) ... [?25ldone
    [?25hRequirement already satisfied: nbdev in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (2.3.13)
    Requirement already satisfied: pandas in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (2.0.1)
    Requirement already satisfied: notebook in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (6.5.4)
    Requirement already satisfied: pyDatalog in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (0.17.4)
    Requirement already satisfied: tabulate in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (0.9.0)
    Requirement already satisfied: lark-parser>=0.9.0 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (0.12.0)
    Requirement already satisfied: ipython>=7.18.1 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (8.12.2)
    Requirement already satisfied: setuptools>=50.2.0 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (65.6.3)
    Requirement already satisfied: networkx>=2.5 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (3.1)
    Requirement already satisfied: docopt>=0.6.2 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (0.6.2)
    Requirement already satisfied: jsonpath-ng in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (1.5.3)
    Requirement already satisfied: psutil in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (5.9.5)
    Requirement already satisfied: install-jdk in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (1.0.4)
    Requirement already satisfied: parse in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (1.19.0)
    Requirement already satisfied: spanner-nlp in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (0.0.6)
    Requirement already satisfied: pytest in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (7.3.1)
    Requirement already satisfied: Jinja2 in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (3.1.2)
    Requirement already satisfied: pycodestyle in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (2.10.0)
    Requirement already satisfied: mypy in /miniconda/lib/python3.8/site-packages (from rgxlog==0.0.1) (1.3.0)
    Requirement already satisfied: matplotlib-inline in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (0.1.6)
    Requirement already satisfied: jedi>=0.16 in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (0.18.2)
    Requirement already satisfied: traitlets>=5 in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (5.9.0)
    Requirement already satisfied: pickleshare in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (0.7.5)
    Requirement already satisfied: typing-extensions in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (4.6.2)
    Requirement already satisfied: decorator in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (5.1.1)
    Requirement already satisfied: prompt-toolkit!=3.0.37,<3.1.0,>=3.0.30 in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (3.0.38)
    Requirement already satisfied: stack-data in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (0.6.2)
    Requirement already satisfied: pygments>=2.4.0 in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (2.15.1)
    Requirement already satisfied: pexpect>4.3 in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (4.8.0)
    Requirement already satisfied: backcall in /miniconda/lib/python3.8/site-packages (from ipython>=7.18.1->rgxlog==0.0.1) (0.2.0)
    Requirement already satisfied: MarkupSafe>=2.0 in /miniconda/lib/python3.8/site-packages (from Jinja2->rgxlog==0.0.1) (2.1.2)
    Requirement already satisfied: ply in /miniconda/lib/python3.8/site-packages (from jsonpath-ng->rgxlog==0.0.1) (3.11)
    Requirement already satisfied: six in /miniconda/lib/python3.8/site-packages (from jsonpath-ng->rgxlog==0.0.1) (1.16.0)
    Requirement already satisfied: mypy-extensions>=1.0.0 in /miniconda/lib/python3.8/site-packages (from mypy->rgxlog==0.0.1) (1.0.0)
    Requirement already satisfied: tomli>=1.1.0 in /miniconda/lib/python3.8/site-packages (from mypy->rgxlog==0.0.1) (2.0.1)
    Requirement already satisfied: watchdog in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (3.0.0)
    Requirement already satisfied: PyYAML in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (6.0)
    Requirement already satisfied: execnb>=0.1.4 in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (0.1.5)
    Requirement already satisfied: ipywidgets<=8.0.4 in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (8.0.4)
    Requirement already satisfied: asttokens in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (2.2.1)
    Requirement already satisfied: ghapi>=1.0.3 in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (1.0.4)
    Requirement already satisfied: fastcore>=1.5.27 in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (1.5.29)
    Requirement already satisfied: astunparse in /miniconda/lib/python3.8/site-packages (from nbdev->rgxlog==0.0.1) (1.6.3)
    Requirement already satisfied: terminado>=0.8.3 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (0.17.1)
    Requirement already satisfied: Send2Trash>=1.8.0 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (1.8.2)
    Requirement already satisfied: jupyter-client>=5.3.4 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (8.2.0)
    Requirement already satisfied: argon2-cffi in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (21.3.0)
    Requirement already satisfied: ipykernel in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (6.23.1)
    Requirement already satisfied: prometheus-client in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (0.17.0)
    Requirement already satisfied: pyzmq>=17 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (25.0.2)
    Requirement already satisfied: tornado>=6.1 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (6.3.2)
    Requirement already satisfied: jupyter-core>=4.6.1 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (5.3.0)
    Requirement already satisfied: nbformat in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (5.8.0)
    Requirement already satisfied: nbconvert>=5 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (7.4.0)
    Requirement already satisfied: nest-asyncio>=1.5 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (1.5.6)
    Requirement already satisfied: nbclassic>=0.4.7 in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (1.0.0)
    Requirement already satisfied: ipython-genutils in /miniconda/lib/python3.8/site-packages (from notebook->rgxlog==0.0.1) (0.2.0)
    Requirement already satisfied: tzdata>=2022.1 in /miniconda/lib/python3.8/site-packages (from pandas->rgxlog==0.0.1) (2023.3)
    Requirement already satisfied: numpy>=1.20.3 in /miniconda/lib/python3.8/site-packages (from pandas->rgxlog==0.0.1) (1.24.3)
    Requirement already satisfied: python-dateutil>=2.8.2 in /miniconda/lib/python3.8/site-packages (from pandas->rgxlog==0.0.1) (2.8.2)
    Requirement already satisfied: pytz>=2020.1 in /miniconda/lib/python3.8/site-packages (from pandas->rgxlog==0.0.1) (2023.3)
    Requirement already satisfied: exceptiongroup>=1.0.0rc8 in /miniconda/lib/python3.8/site-packages (from pytest->rgxlog==0.0.1) (1.1.1)
    Requirement already satisfied: iniconfig in /miniconda/lib/python3.8/site-packages (from pytest->rgxlog==0.0.1) (2.0.0)
    Requirement already satisfied: packaging in /miniconda/lib/python3.8/site-packages (from pytest->rgxlog==0.0.1) (22.0)
    Requirement already satisfied: pluggy<2.0,>=0.12 in /miniconda/lib/python3.8/site-packages (from pytest->rgxlog==0.0.1) (1.0.0)
    Requirement already satisfied: requests in /miniconda/lib/python3.8/site-packages (from spanner-nlp->rgxlog==0.0.1) (2.28.1)
    Requirement already satisfied: pip in /miniconda/lib/python3.8/site-packages (from fastcore>=1.5.27->nbdev->rgxlog==0.0.1) (22.3.1)
    Requirement already satisfied: widgetsnbextension~=4.0 in /miniconda/lib/python3.8/site-packages (from ipywidgets<=8.0.4->nbdev->rgxlog==0.0.1) (4.0.9)
    Requirement already satisfied: jupyterlab-widgets~=3.0 in /miniconda/lib/python3.8/site-packages (from ipywidgets<=8.0.4->nbdev->rgxlog==0.0.1) (3.0.9)
    Requirement already satisfied: debugpy>=1.6.5 in /miniconda/lib/python3.8/site-packages (from ipykernel->notebook->rgxlog==0.0.1) (1.6.7)
    Requirement already satisfied: comm>=0.1.1 in /miniconda/lib/python3.8/site-packages (from ipykernel->notebook->rgxlog==0.0.1) (0.1.3)
    Requirement already satisfied: parso<0.9.0,>=0.8.0 in /miniconda/lib/python3.8/site-packages (from jedi>=0.16->ipython>=7.18.1->rgxlog==0.0.1) (0.8.3)
    Requirement already satisfied: importlib-metadata>=4.8.3 in /miniconda/lib/python3.8/site-packages (from jupyter-client>=5.3.4->notebook->rgxlog==0.0.1) (6.6.0)
    Requirement already satisfied: platformdirs>=2.5 in /miniconda/lib/python3.8/site-packages (from jupyter-core>=4.6.1->notebook->rgxlog==0.0.1) (3.5.1)
    Requirement already satisfied: notebook-shim>=0.2.3 in /miniconda/lib/python3.8/site-packages (from nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (0.2.3)
    Requirement already satisfied: jupyter-server>=1.8 in /miniconda/lib/python3.8/site-packages (from nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (2.6.0)
    Requirement already satisfied: mistune<3,>=2.0.3 in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (2.0.5)
    Requirement already satisfied: defusedxml in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (0.7.1)
    Requirement already satisfied: tinycss2 in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (1.2.1)
    Requirement already satisfied: nbclient>=0.5.0 in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (0.8.0)
    Requirement already satisfied: jupyterlab-pygments in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (0.2.2)
    Requirement already satisfied: bleach in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (6.0.0)
    Requirement already satisfied: beautifulsoup4 in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (4.12.2)
    Requirement already satisfied: pandocfilters>=1.4.1 in /miniconda/lib/python3.8/site-packages (from nbconvert>=5->notebook->rgxlog==0.0.1) (1.5.0)
    Requirement already satisfied: jsonschema>=2.6 in /miniconda/lib/python3.8/site-packages (from nbformat->notebook->rgxlog==0.0.1) (4.17.3)
    Requirement already satisfied: fastjsonschema in /miniconda/lib/python3.8/site-packages (from nbformat->notebook->rgxlog==0.0.1) (2.17.1)
    Requirement already satisfied: ptyprocess>=0.5 in /miniconda/lib/python3.8/site-packages (from pexpect>4.3->ipython>=7.18.1->rgxlog==0.0.1) (0.7.0)
    Requirement already satisfied: wcwidth in /miniconda/lib/python3.8/site-packages (from prompt-toolkit!=3.0.37,<3.1.0,>=3.0.30->ipython>=7.18.1->rgxlog==0.0.1) (0.2.6)
    Requirement already satisfied: argon2-cffi-bindings in /miniconda/lib/python3.8/site-packages (from argon2-cffi->notebook->rgxlog==0.0.1) (21.2.0)
    Requirement already satisfied: wheel<1.0,>=0.23.0 in /miniconda/lib/python3.8/site-packages (from astunparse->nbdev->rgxlog==0.0.1) (0.37.1)
    Requirement already satisfied: idna<4,>=2.5 in /miniconda/lib/python3.8/site-packages (from requests->spanner-nlp->rgxlog==0.0.1) (3.4)
    Requirement already satisfied: certifi>=2017.4.17 in /miniconda/lib/python3.8/site-packages (from requests->spanner-nlp->rgxlog==0.0.1) (2022.12.7)
    Requirement already satisfied: charset-normalizer<3,>=2 in /miniconda/lib/python3.8/site-packages (from requests->spanner-nlp->rgxlog==0.0.1) (2.0.4)
    Requirement already satisfied: urllib3<1.27,>=1.21.1 in /miniconda/lib/python3.8/site-packages (from requests->spanner-nlp->rgxlog==0.0.1) (1.25.8)
    Requirement already satisfied: executing>=1.2.0 in /miniconda/lib/python3.8/site-packages (from stack-data->ipython>=7.18.1->rgxlog==0.0.1) (1.2.0)
    Requirement already satisfied: pure-eval in /miniconda/lib/python3.8/site-packages (from stack-data->ipython>=7.18.1->rgxlog==0.0.1) (0.2.2)
    Requirement already satisfied: zipp>=0.5 in /miniconda/lib/python3.8/site-packages (from importlib-metadata>=4.8.3->jupyter-client>=5.3.4->notebook->rgxlog==0.0.1) (3.15.0)
    Requirement already satisfied: importlib-resources>=1.4.0 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (5.12.0)
    Requirement already satisfied: pkgutil-resolve-name>=1.3.10 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (1.3.10)
    Requirement already satisfied: attrs>=17.4.0 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (23.1.0)
    Requirement already satisfied: pyrsistent!=0.17.0,!=0.17.1,!=0.17.2,>=0.14.0 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (0.19.3)
    Requirement already satisfied: jupyter-server-terminals in /miniconda/lib/python3.8/site-packages (from jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (0.4.4)
    Requirement already satisfied: overrides in /miniconda/lib/python3.8/site-packages (from jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (7.3.1)
    Requirement already satisfied: websocket-client in /miniconda/lib/python3.8/site-packages (from jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (1.5.2)
    Requirement already satisfied: jupyter-events>=0.6.0 in /miniconda/lib/python3.8/site-packages (from jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (0.6.3)
    Requirement already satisfied: anyio>=3.1.0 in /miniconda/lib/python3.8/site-packages (from jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (3.6.2)
    Requirement already satisfied: cffi>=1.0.1 in /miniconda/lib/python3.8/site-packages (from argon2-cffi-bindings->argon2-cffi->notebook->rgxlog==0.0.1) (1.15.1)
    Requirement already satisfied: soupsieve>1.2 in /miniconda/lib/python3.8/site-packages (from beautifulsoup4->nbconvert>=5->notebook->rgxlog==0.0.1) (2.4.1)
    Requirement already satisfied: webencodings in /miniconda/lib/python3.8/site-packages (from bleach->nbconvert>=5->notebook->rgxlog==0.0.1) (0.5.1)
    Requirement already satisfied: sniffio>=1.1 in /miniconda/lib/python3.8/site-packages (from anyio>=3.1.0->jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (1.3.0)
    Requirement already satisfied: pycparser in /miniconda/lib/python3.8/site-packages (from cffi>=1.0.1->argon2-cffi-bindings->argon2-cffi->notebook->rgxlog==0.0.1) (2.21)
    Requirement already satisfied: rfc3986-validator>=0.1.1 in /miniconda/lib/python3.8/site-packages (from jupyter-events>=0.6.0->jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (0.1.1)
    Requirement already satisfied: python-json-logger>=2.0.4 in /miniconda/lib/python3.8/site-packages (from jupyter-events>=0.6.0->jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (2.0.7)
    Requirement already satisfied: rfc3339-validator in /miniconda/lib/python3.8/site-packages (from jupyter-events>=0.6.0->jupyter-server>=1.8->nbclassic>=0.4.7->notebook->rgxlog==0.0.1) (0.1.4)
    Requirement already satisfied: isoduration in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (20.11.0)
    Requirement already satisfied: jsonpointer>1.13 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (2.1)
    Requirement already satisfied: uri-template in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (1.2.0)
    Requirement already satisfied: fqdn in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (1.5.1)
    Requirement already satisfied: webcolors>=1.11 in /miniconda/lib/python3.8/site-packages (from jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (1.13)
    Requirement already satisfied: arrow>=0.15.0 in /miniconda/lib/python3.8/site-packages (from isoduration->jsonschema>=2.6->nbformat->notebook->rgxlog==0.0.1) (1.2.3)
    Building wheels for collected packages: rgxlog
      Building wheel for rgxlog (setup.py) ... [?25ldone
    [?25h  Created wheel for rgxlog: filename=rgxlog-0.0.1-py3-none-any.whl size=89487 sha256=9ead8b269021048b9b4cdb511024e427700155f882646d78334badf344607fea
      Stored in directory: /tmp/pip-ephem-wheel-cache-n0deoiky/wheels/62/da/4d/48e3d3b55711eef8154983104097b04f07d8a68aa8ee1aa6ed
    Successfully built rgxlog
    Installing collected packages: rgxlog
      Attempting uninstall: rgxlog
        Found existing installation: rgxlog 0.0.1
        Uninstalling rgxlog-0.0.1:
          Successfully uninstalled rgxlog-0.0.1
    Successfully installed rgxlog-0.0.1
    [33mWARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv[0m[33m
    [0m


```
import re
import csv
import pandas as pd
from pandas import DataFrame
import rgxlog
from rgxlog.session import Session
from rgxlog.primitive_types import Span, DataTypes
from rgxlog import magic_session
```

Defining some generic ie functions that will be used in every stage of the pipline:


```
def read_from_file(text_path):
    """
    Reads from file and return it's content.

    Parameters:
        text_path (str): The path to the text file to read from.

    Returns:
        str: The content of the file.
    """
    with open(f"{text_path}", 'r') as file:
        content = file.read()
    yield content

magic_session.register(ie_function=read_from_file,
                       ie_function_name = "read_from_file",
                       in_rel=[DataTypes.string],
                       out_rel=[DataTypes.string])
```


```
# usage example
for value in read_from_file("sample1.txt"):
    print(value)
```

    Patient presents to be tested for COVID-19. His wife recently tested positive for novel coronavirus. SARS-COV-2 results came back positive.
    


```
def print_csv_file(file_path):
    """
    Print the contents of a CSV file in a human-readable format.

    Parameters:
        file_path (str): The path to the CSV file.
    """
    with open(file_path, 'r', newline='') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            print(','.join(row))
```


```
# usage example

data_to_write = [
    ['Name', 'Age', 'Occupation'],
    ['John', '25', 'Engineer'],
    ['Jane', '30', 'Doctor'],
    ['Bob', '28', 'Teacher'],
    ['Alice', '22', 'Student']
]

with open('example.csv', 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerows(data_to_write)

print_csv_file('example.csv')
```

    Name,Age,Occupation
    John,25,Engineer
    Jane,30,Doctor
    Bob,28,Teacher
    Alice,22,Student
    


```
def select_containing_span(spans):
    """
    This function takes a list of spans, where each span is represented
    as a list containing a label and a span (interval). It resolves overlaps
    by selecting the containing span, favoring the larger span in case of conflicts.

    Parameters:
    spans (list of lists): A list of spans, where each span is represented
        as a list [label, span].

    Returns:
    list of lists: A list of resolved spans, where each span is a list
        [label, span], with conflicts resolved by selecting the containing span.
    """
    # Sort the replacements by the size of the spans in descending order
    spans.sort(key=lambda x: x[1].span_end - x[1].span_start, reverse=True)

    # Initialize a list to keep track of intervals that have been replaced
    resolved_spans = []
    
    for label, span in spans:
        conflict = False

        for _, existing_span in resolved_spans:
            existing_start = existing_span.span_start
            existing_end = existing_span.span_end

            if not (span.span_end <= existing_start or span.span_start >= existing_end):
                conflict = True
                break

        if not conflict:
            resolved_spans.append([label, span])

    return resolved_spans
```


```
# usage example
spans = [ 
     ['Label1', Span(2, 8)],
     ['Label2', Span(5, 8)]
 ]
resolved_spans = select_containing_span(spans)
for label, span in resolved_spans:
    print(f"Label: {label}, Span: {span.span_start}-{span.span_end}")
```

    Label: Label1, Span: 2-8
    


```
def replace_spans(spans_table, paths_table, session):
    """
    This function takes tables a spans tables and path table for the files paths,
    it generate queries for the tables, executes the queries using the given session, processes the results, 
    and replaces specific spans in a text with the corresponding labels, it first
    resolve spans overlapping conflicts for each giving path.

    Parameters:
    spans_table (str): A string representing the spans table to process, table columns are formated as (Label, Span, Path).
    paths_table (str): A string representing the paths table to process, table columns are formated as (Path)
    session: the session in the rgxlog to run the queries at.

    Returns:
    str: The adjusted text string with the new labels.
    """
    # Get a list of all the paths
    paths = session.run_commands(f"?{paths_table}(Path)", print_results=False, format_results=True)
    paths = paths[0].values.tolist()
    for path_list in paths:
        path = path_list[0]

        # Generate a spans query for each path, the query will be formates as (Label, Span, Path)
        results = magic_session.run_commands(f'?{spans_table}(Label, Span, "{path}")', print_results=True, format_results=True)
        if len(results[0]) == 0:
            continue
        # replacments is list of lists where each list is a [Label, Span]
        replacements = results[0].values.tolist()
        
        with open(f"{path}", 'r') as file:
            adjusted_string = file.read()
    
        # Resolve spans conflicts
        resolved_replacements = select_containing_span(replacements)
    
        # Sort the resolved replacements by the starting index of each span in descending order
        resolved_replacements.sort(key=lambda x: x[1].span_start, reverse=True)
    
        # iterate over the resolved query results and replace the space with the corresponding label
        for i in range(len(resolved_replacements)):
            replace_string, span = resolved_replacements[i]
            replace_length = len(replace_string)
            adjusted_string = adjusted_string[:span.span_start] + replace_string + adjusted_string[span.span_end:]
    
        with open(f"{path}", 'w') as file:
            file.writelines(adjusted_string)
```


```
# usage example
with open('example.txt', 'w') as file:
    file.write('The boy has novel coronavirus')
%rgxlog new samplePaths(str)
%rgxlog samplePaths("example.txt")
%rgxlog new sampleMatches(str, span, str)
%rgxlog sampleMatches("Covid-19", [12,29), "example.txt")
replace_spans('sampleMatches', 'samplePaths', magic_session)
for value in read_from_file("example.txt"):
    print(value)
```

    printing results for query 'sampleMatches(Label, Span, "example.txt")':
      Label   |   Span
    ----------+----------
     Covid-19 | [12, 29)
    
    The boy has Covid-19
    


```
def is_span_contained(span1, span2):
    """
    Checks if one span is contained within the other span and returns the smaller span if yes.

    Parameters:
        span1 (span)
        span2 (span)

    Returns:
        span: span1 if contained within span2 or vice versa, or None if not contained.
    """
    start1, end1 = span1.span_start, span1.span_end
    start2, end2 = span2.span_start, span2.span_end
    
    if start2 <= start1 and end1 <= end2:
        yield span1
        
    elif start1 <= start2 and end2 <= end1:
        yield span2

magic_session.register(is_span_contained, "is_span_contained", in_rel=[DataTypes.span, DataTypes.span], out_rel=[DataTypes.span])
```


```
# usage example
span1 = Span(2, 12)
span2 = Span(8, 9)
for span in is_span_contained(span1, span2):
    print(f" Span: {span.span_start}-{span.span_end}")
```

     Span: 8-9
    


```
def get_relative_span(span1, span2):
    """
    Computes the relative position of the conatined span within the other span.

    Parameters:
        span1 (Span): The first span object.
        span2 (Span): The second span object.

    Returns:
        Span: The new relative span of the contained one.
        None: If there's no span contained within the other.
    """
    start1, end1 = span1.span_start, span1.span_end
    start2, end2 = span2.span_start, span2.span_end
    
    if start2 <= start1 and end1 <= end2:
        yield Span(span1.span_start - span2.span_start, span1.span_end - span2.span_start)
        
    elif start1 <= start2 and end2 <= end1:
        yield Span(span2.span_start - span1.span_start, span2.span_end - span1.span_start)

magic_session.register(get_relative_span, "get_relative_span", in_rel=[DataTypes.span, DataTypes.span], out_rel=[DataTypes.span])
```


```
# usage example 
span1 = Span(2, 12)
span2 = Span(2, 5)
for span in get_relative_span(span1, span2):
    print(f" Span: {span.span_start}-{span.span_end}")
```

     Span: 0-3
    


```
def sent_tokenization(text_path):
    """
    This function reads a text file, processes its content using spaCy's English language model,
    tokenizing it into sentences and returns each individual sentence in the processed text using a generator.
    
    Parameters:
        text_path (str): The path to the text file to be annotated.

    Returns:
        str: Individual sentences extracted from the input text.
    """
    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    for sentence in doc.sents:
        yield sentence.text

magic_session.register(ie_function=sent_tokenization, ie_function_name = "sent_tokenization", in_rel=[DataTypes.string], out_rel=[DataTypes.string])
```


```
# usage example 
for sentence in sent_tokenization("sample1.txt"):
    print(sentence)
```

    Patient presents to be tested for COVID-19.
    His wife recently tested positive for novel coronavirus.
    SARS-COV-2 results came back positive.
    

<a id='pipeline-input'></a>
### Pipeline Input:
The paths of the text files to be classified should be written in "files_paths.csv" file


```
print_csv_file('files_paths.csv')
```

    sample1.txt
    sample2.txt
    sample3.txt
    sample4.txt
    sample5.txt
    sample6.txt
    sample7.txt
    


```
magic_session.import_relation_from_csv("files_paths.csv", relation_name="FilesPaths", delimiter=",")
```

The initial files contents:


```
%%rgxlog
FilesContent(Path, Content) <- FilesPaths(Path), read_from_file(Path) -> (Content)
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                   Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | Patient presents to be tested for COVID-19. His wife recently tested positive for novel coronavirus. SARS-COV-2 results came back positive.
     sample2.txt |                                         The patient was tested for COVID-19. Results are positive.
     sample3.txt |                                            Problem List: 1. Pneumonia 2. Novel Coronavirus 2019
     sample4.txt |                                                           neg COVID-19 education.
     sample5.txt |                                                        positive COVID-19 precaution.
     sample6.txt |                                            The patient have reported positive COVID-19 exposure.
     sample7.txt |                              Elevated cholesterol levels require further assessment and lifestyle adjustments.
    
    

Before we continue we have to do some pre processing to help ease the next stages, we will certain words in each list to it's lemma forms, here a list of the words that we want to lemmatize


```
print_csv_file('lemma_words.txt')
```

    be
    man
    woman
    have
    do
    emergency
    epidemic
    outbreak
    crisis
    breakout
    pandemic
    spread
    confirm
    person
    patient
    veteran
    limit
    reduce
    factor
    contact
    case
    lower
    minimize
    risk
    chance
    possibility
    care
    clean
    desire
    flight
    trip
    plan
    reschedule
    postpone
    barrier
    

We will define a helper method to do that:


```
def lemmatize_text(text_path, lemma_words_path):
    """
    This function reads a text file, lemmatizes its content using spaCy's English language model,
    and replaces certain words with their lemmas the rest will remain the same. The updated text is then written back to the same file.

    Parameters:
        text_path (str): The path to the text file to be lemmatized.
        lemma_words_path(str): The path that contains the list of words to be lemmatized

    Returns:
        str: The lemmatized text.
    """
    # Define a list of words to be lemmatized
    lemma_words = [line.strip() for line in open(f"{lemma_words_path}") if line.strip()]

    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    lemmatized_text = ""
    for token in doc:
        if token.lemma_ in lemma_words:
            lemmatized_text += token.lemma_
        elif token.like_num:
            lemmatized_text += "like_num"
        else:
            lemmatized_text += token.text
        lemmatized_text += " "

    # Write the lemmatized text back to the same file
    with open(text_path, 'w') as file:
        file.writelines(lemmatized_text)

    return lemmatized_text
```


```
# usage example
with open('example.txt', 'w') as file:
    file.write('The boy was sick')
lemmatized_text = lemmatize_text('example.txt', 'lemma_words.txt')
print(lemmatized_text)
```

    The boy be sick 
    

Iterate over the texts to lemmatize them


```
with open('files_paths.csv', 'r') as file:
    # Create a CSV reader object
    csv_reader = csv.reader(file)

    # Iterate through each row in the CSV file
    for row in csv_reader:
        path = row[0]
        lemmatize_text(path, 'lemma_words.txt')
```

As we can see for example in sample2.txt, was has changed to be.


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                     Content
    -------------+--------------------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His wife recently tested positive for novel coronavirus . SARS - COV-2 results came back positive .
     sample2.txt |                                            The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                                    Problem List : like_num . Pneumonia like_num . Novel Coronavirus like_num
     sample4.txt |                                                             neg COVID-19 education .
     sample5.txt |                                                          positive COVID-19 precaution .
     sample6.txt |                                              The patient have reported positive COVID-19 exposure .
     sample7.txt |                                Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    

<a id='concept-tag-rules'></a>
### [Concept Tagger](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/concept_tag_rules.py):
Concept tag rules, also known as pattern-based rules or custom rules, are a way to specify and define patterns that an NLP (Natural Language Processing) system should recognize within text data. These rules are used to identify specific concepts or entities within text documents. In the context of MedSpaCy and medical NLP, concept tag rules are often used to identify medical entities and concepts accurately.

In the orginal project they used the TargetRule class which defines a rule for identifying a specific concept or entity in text.
each concept Target Rule looks like this:

TargetRule(
            literal="coronavirus",
            category="COVID-19",
            pattern=[{"LOWER": {"REGEX": "coronavirus|hcov|ncov$"}}],
          )

**Literal** : This specifies the literal text or word that this rule is targeting.

**Category** : This specifies the category or label associated with the identified entity.

**Pattern** : This defines the pattern or conditions under which the entity should be recognized. It's a list of dictionaries specifying conditions for token matching. These rules some times used lemma attribute or POS of each token. A documentation can be found at : https://spacy.io/usage/rule-based-matching.

Instead what we did is to define regex patterns, we have added these pattern in concept_target_rules.csv file, there are two types of these patterns lemma and pos, that we will implement each later on.
Each rule in the csv file is like this : regexPattern, label, type


```
print_csv_file('concept_tags_rules.csv')
```

    (?i)(?:hcov|covid(?:(?:-)?(?:\s)?19|10)?|2019-cov|cov2|ncov-19|covd 19|no-cov|sars cov),COVID-19,lemma
    (?i)(?:coivid|(?:novel )?corona(?:virus)?(?: (?:20)?19)?|sars(?:\s)?(?:-)?(?:\s)?cov(?:id)?(?:-)?(?:2|19)),COVID-19,lemma
    (?i)(?:\+(?: ve)?|\(\+\)|positive|\bpos\b|active|confirmed),positive,lemma
    (?i)(?:pneum(?:onia)?|pna|hypoxia|septic shoc|ards\(?(?:(?:[12])/2)\)?|(?:hypoxemic|acute|severe)? resp(?:iratory)? failure(?:\(?(?:[12]/2)\)?)?)",associated_diagnosis,lemma
    (?i)(?:(?:diagnos(?:is|ed)|dx(?:\.)?)(?:of|with)?),diagnosis,lemma
    (?i)(?:^screen),screening,lemma
    (?i)(?:in contact with|any one|co-worker|at work|(?:the|a)(?:wo)?man|(?:another|a) (?:pt|patient|pt\.)),other_experiencer,lemma
    (?i)(?:patient|pt(?:\.)?|vt|veteran),patient,lemma
    (?i)(?:like_num (?:days|day|weeks|week|months|month) (?:ago|prior)),timesx,lemma
    (?i)(?:(?:antibody|antibodies|ab) test),antibody test,lemma
    (?i)(?:(?:coronavirus|hcovs?|ncovs?|covs?)(?:\s)?(?:-)?(?:\s)?(?: infection)?(?: strain)?(?:\s)?(?:229(?:e)?|oc(?:-)?(?:43)?|o43|0c43|43|nl(?:16(?:3|5))?|hku(?:t|-)?1|hkui|emc|63)),OTHER_CORONAVIRUS,lemma
    (?i)(?:(?:229(?:e)?|oc(?:-)?(?:43)?|o43|0c43|43|nl(?:16(?:3|5))?|hku(?:t|-)?1|hkui|emc|63) (?:coronavirus|hcovs?|ncovs?|covs?)),OTHER_CORONAVIRUS,lemma
    (?i)(?:non(?:\s)?(?:-)?(?:\s)?(?:novel|covid|ncovid|covid-19)(?: coronavirus)?|other coronavirus),OTHER_CORONAVIRUS,lemma
    (?i)(?:wife|husband|spouse|family|member|girlfriend|boyfriend|mother|father|nephew|niece|grandparent|grandparents|granddaughter|relative|relatives|caregiver),family,pos
    (?i)(?:grandchild|grandson|cousin|grandmother|grandfather|parent|son|daughter|mom|dad|brother|sister|aunt|uncle|child|children|sibling|siblings),family,pos
    (?i)(?:someone|somebody|person|anyone|anybody|people|individual|individuals|teacher|anybody|employees|employer|customer|client|residents),other_experiencer,pos
    (?i)(?:resident|pts|patients|coworker|coworkers|workers|colleague|captain|captains|pilot|pilots|sailor|sailors|meeting),other_experiencer,pos
    (?i)(?:boyfriend|persons|person|church|convention|guest|party|attendee|conference|roommate|friend|friends|coach|player|neighbor|manager|boss),other_experiencer,pos
    (?i)(?:cashier|landlord|worked|works|^mate|nobody|mates|housemate|housemates|hotel|soldier|airport|tsa|lady|ladies|lobby|staffer|staffers),other_experiencer,pos
    


```
magic_session.import_relation_from_csv("concept_tags_rules.csv", relation_name="ConceptTagRules", delimiter=",")
```

#### Lemma Rules:
Lemma rules are rules that used the attribute _lemma of each token in the NLP, we already lemmatized the texts, so now we can create a regex patterns for that.

Example for a lemma rule from the original NLP:

        TargetRule(
            "results positive",
            "positive",
            pattern=[
                {"LOWER": "results"},
                {"LEMMA": "be", "OP": "?"},
                {"LOWER": {"IN": ["pos", "positive"]}},
            ],
        ),
We used the py_rgx_span to capture the patterns, and will use the spans later on in replace_spans that will replace each span with the correct label


```
%%rgxlog
LemmaMatches(Label, Span, Path) <- FilesContent(Path, Content), ConceptTagRules(Pattern, Label, "lemma"), py_rgx_span(Content, Pattern) -> (Span)
```

Before:


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                     Content
    -------------+--------------------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His wife recently tested positive for novel coronavirus . SARS - COV-2 results came back positive .
     sample2.txt |                                            The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                                    Problem List : like_num . Pneumonia like_num . Novel Coronavirus like_num
     sample4.txt |                                                             neg COVID-19 education .
     sample5.txt |                                                          positive COVID-19 precaution .
     sample6.txt |                                              The patient have reported positive COVID-19 exposure .
     sample7.txt |                                Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    


```
# replace the matches with the correct label
replace_spans("LemmaMatches", "FilesPaths", magic_session)
```

    printing results for query 'LemmaMatches(Label, Span, "sample1.txt")':
      Label   |    Span
    ----------+------------
     positive | [134, 142)
     positive |  [70, 78)
     COVID-19 | [103, 115)
     COVID-19 | [83, 100)
     COVID-19 |  [34, 42)
     patient  |   [0, 7)
    
    printing results for query 'LemmaMatches(Label, Span, "sample2.txt")':
      Label   |   Span
    ----------+----------
     positive | [48, 56)
     COVID-19 | [26, 34)
     patient  | [4, 11)
    
    printing results for query 'LemmaMatches(Label, Span, "sample3.txt")':
            Label         |   Span
    ----------------------+----------
           COVID-19       | [47, 64)
     associated_diagnosis | [26, 35)
    
    printing results for query 'LemmaMatches(Label, Span, "sample4.txt")':
      Label   |  Span
    ----------+---------
     COVID-19 | [4, 12)
    
    printing results for query 'LemmaMatches(Label, Span, "sample5.txt")':
      Label   |  Span
    ----------+---------
     positive | [0, 8)
     COVID-19 | [9, 17)
    
    printing results for query 'LemmaMatches(Label, Span, "sample6.txt")':
      Label   |   Span
    ----------+----------
     positive | [26, 34)
     COVID-19 | [35, 43)
     patient  | [4, 11)
    
    printing results for query 'LemmaMatches(Label, Span, "sample7.txt")':
    []
    
    

After:
As we can see for example in the sample1.txt, every other covid-19 name was changed to COVID-19.


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                               Content
    -------------+-------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His wife recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                     The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                             Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                      neg COVID-19 education .
     sample5.txt |                                                   positive COVID-19 precaution .
     sample6.txt |                                       The patient have reported positive COVID-19 exposure .
     sample7.txt |                         Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    

#### POS Rules:
As we mentioned above these rules used the POS attribute of each token, there were a small number of rules so we only used this to the tokens we needed.
Example of the a rule from the original NLP:

        TargetRule(
            "other experiencer",
            category="other_experiencer",
            pattern=[
                {
                    "POS": {"IN": ["NOUN", "PROPN", "PRON", "ADJ"]},
                    "LOWER": {
                        "IN": [
                            "someone",
                            "somebody",
                            "person",
                            "anyone",
                            "anybody",
                        ]
                    },
                }
            ],
        ),

The patterns we've defined will match words listed under "IN", We specifically capture words if their Part-of-Speech (POS) falls into one of the categories: ["NOUN", "PROPN", "PRON", "ADJ"]. To accomplish this, two functions are employed: the first function determines the POS of each token, and the second one, py_rgx_span, captures the predefined patterns. After matching words, We confirm the accurate POS tags of the matched words using spans.


```
def annotate_text_with_pos(text_path):
    """
    This function reads a text file, processes its content using spaCy's English language model,
    and returns a tuple of (POS, Span) for each token if it's one of NOUN|PROPN|PRON|ADJ
    otherwise an empty tuple will be returned
    
    Parameters:
        text_path (str): The path to the text file to be annotated.

    Returns:
        tuple(str, Span): The POS of the token and it's span
    """
    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    for token in doc:
        if token.pos_ in ["NOUN", "PROPN", "PRON", "ADJ"]:
            yield token.pos_, Span(token.idx, token.idx + len(token.text))
        else:
            yield tuple()
magic_session.register(ie_function=annotate_text_with_pos, ie_function_name = "annotate_text_with_pos", in_rel=[DataTypes.string], out_rel=[DataTypes.string, DataTypes.span])
```


```
# usage example
with open('example.txt', 'w') as file:
    file.write('sick boy')

for POS, span in annotate_text_with_pos('example.txt'):
    print(f"{POS}, ({span.span_start},{span.span_end})")
```

    ADJ, (0,4)
    NOUN, (5,8)
    


```
%%rgxlog
POSTable(POS, Span, Path) <- FilesContent(Path, Content), annotate_text_with_pos(Path) -> (POS, Span)
?POSTable(POS, Span, Path)

POSMatches(Label, Span, Path) <- FilesContent(Path, Content), ConceptTagRules(Pattern, Label, "pos"), py_rgx_span(Content, Pattern) -> (Span)
?POSMatches(Label, Span, Path)

POSRuleMatches(Label, Span, Path) <- POSTable(POS, Span, Path), POSMatches(Label, Span, Path)
?POSRuleMatches(Label, Span, Path)
```

    printing results for query 'POSTable(POS, Span, Path)':
      POS  |    Span    |    Path
    -------+------------+-------------
      ADJ  |   [0, 7)   | sample1.txt
      ADJ  | [121, 129) | sample1.txt
      ADJ  |  [70, 78)  | sample1.txt
     NOUN  | [103, 110) | sample1.txt
     NOUN  |  [49, 53)  | sample1.txt
     NOUN  |  [8, 16)   | sample1.txt
     PRON  |  [45, 48)  | sample1.txt
     PROPN |  [34, 42)  | sample1.txt
     PROPN |  [83, 91)  | sample1.txt
     PROPN | [94, 102)  | sample1.txt
      ADJ  |  [48, 56)  | sample2.txt
     NOUN  |  [37, 44)  | sample2.txt
     NOUN  |  [4, 11)   | sample2.txt
     PROPN |  [26, 34)  | sample2.txt
     PROPN |   [0, 7)   | sample3.txt
     PROPN |  [15, 23)  | sample3.txt
     PROPN |  [47, 55)  | sample3.txt
     PROPN |  [58, 66)  | sample3.txt
     PROPN |  [67, 75)  | sample3.txt
     PROPN |  [8, 12)   | sample3.txt
     NOUN  |  [13, 22)  | sample4.txt
     PROPN |   [0, 3)   | sample4.txt
     PROPN |  [4, 12)   | sample4.txt
      ADJ  |   [0, 8)   | sample5.txt
     NOUN  |  [18, 28)  | sample5.txt
     PROPN |  [9, 17)   | sample5.txt
      ADJ  |  [26, 34)  | sample6.txt
     NOUN  |  [4, 11)   | sample6.txt
     NOUN  |  [44, 52)  | sample6.txt
     PROPN |  [35, 43)  | sample6.txt
      ADJ  |   [0, 8)   | sample7.txt
      ADJ  |  [36, 43)  | sample7.txt
     NOUN  |  [21, 27)  | sample7.txt
     NOUN  |  [44, 54)  | sample7.txt
     NOUN  |  [59, 68)  | sample7.txt
     NOUN  |  [69, 80)  | sample7.txt
     NOUN  |  [9, 20)   | sample7.txt
    
    printing results for query 'POSMatches(Label, Span, Path)':
      Label  |   Span   |    Path
    ---------+----------+-------------
     family  | [49, 53) | sample1.txt
    
    printing results for query 'POSRuleMatches(Label, Span, Path)':
      Label  |   Span   |    Path
    ---------+----------+-------------
     family  | [49, 53) | sample1.txt
    
    

Before:


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                               Content
    -------------+-------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His wife recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                     The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                             Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                      neg COVID-19 education .
     sample5.txt |                                                   positive COVID-19 precaution .
     sample6.txt |                                       The patient have reported positive COVID-19 exposure .
     sample7.txt |                         Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    


```
# replace the matches with the correct label
replace_spans("POSRuleMatches", "FilesPaths", magic_session)
```

    printing results for query 'POSRuleMatches(Label, Span, "sample1.txt")':
      Label  |   Span
    ---------+----------
     family  | [49, 53)
    
    printing results for query 'POSRuleMatches(Label, Span, "sample2.txt")':
    []
    
    printing results for query 'POSRuleMatches(Label, Span, "sample3.txt")':
    []
    
    printing results for query 'POSRuleMatches(Label, Span, "sample4.txt")':
    []
    
    printing results for query 'POSRuleMatches(Label, Span, "sample5.txt")':
    []
    
    printing results for query 'POSRuleMatches(Label, Span, "sample6.txt")':
    []
    
    printing results for query 'POSRuleMatches(Label, Span, "sample7.txt")':
    []
    
    

After:
As we can see for example in sample1.txt, wife has changed to family.


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His family recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                      The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                              Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                       neg COVID-19 education .
     sample5.txt |                                                    positive COVID-19 precaution .
     sample6.txt |                                        The patient have reported positive COVID-19 exposure .
     sample7.txt |                          Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    

<a id='target-rules'></a>
### [Target Rules](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/target_rules.py):
These rules used the label that was assigned through the concept tagger, to capture some more complex patterns and assign a label for them inorder to decremnt the cases of false positive.
Each rule look like this:

        TargetRule(
            literal="coronavirus screening",
            category="IGNORE",
            pattern=[
                {"_": {"concept_tag": "COVID-19"}},
                {"LOWER": {"IN": ["screen", "screening", "screenings"]}},
            ],
        ),
Since we replaced the spans we found with the corresponding label we didn't need the concept_tag attribute of the token/span.

**Literal** : This specifies the literal text or word that this rule is targeting.

**Category** : This specifies the category or label associated with the identified entity.

**Pattern** : This defines the pattern or conditions under which the entity should be recognized. It's a list of dictionaries specifying conditions for token matching. These rules some times used lemma attribute or POS of each token. A documentation can be found at : https://spacy.io/usage/rule-based-matching.

Similar to the concept tag apporach we defined regex patterns, we have added these pattern in target_rules.csv file
Each rule in the csv file is like this : regexPattern, label


```
print_csv_file('target_rules.csv')
```

    (?i)(?:COVID-19 positive (?:unit|floor)|positive COVID-19 (?:unit|floor|exposure)),COVID-19
    (?i)(?:known(?: positive)? COVID-19(?: positive)? (?:exposure|contact)),COVID-19
    (?i)(?:COVID-19 positive screening|positive COVID-19 screening|screening COVID-19 positive|screening positive COVID-19),positive coronavirus screening
    (?i)(?:diagnosis : COVID-19 (?:test|screening)),COVID-19
    (?i)(?:COVID-19 screening),coronavirus screening
    (?i)(?:active COVID-19 precaution|droplet isolation precaution|positive for (?:flu|influenza)|(?:the|a) positive case|results are confirm),1 2 3
    (?i)(?:exposed to positive|[ ] COVID-19|age like_num(?: )?\+|(?:return|back) to work|COVID-19 infection rate),1 2 3
    (?i)(?:COVID-19 (?:restriction|emergency|epidemic|outbreak|crisis|breakout|pandemic|spread|screening)|droplet precaution),1 2
    (?i)(?:contact precautions|positive (?:flu|influenza)|positive (?:patient|person)|confirm (?:with|w/(?:/)?|w)|(?:the|positive) case),1 2
    (?i)(?:results confirm|(?:neg|pos)\S+ pressure|positive (?:attitude|feedback|serology)|COVID-19 (guidelines|rate)),1 2
    (?i)(?:has the patient been diagnosed (?:with|w/(?:/)?|w)),1 2 3 4 5 6
    (?i)(?:has patient been diagnosed (?:with|w/(?:/)?|w)),1 2 3 4 5
    (?i)((?:person|patient) with confirm COVID-19),1 2 3 4
    (?i)(?:COVID-19 positive (?:tested )?other_experiencer),COVID-19
    (?i)(?:in order to decrease the spread of the COVID-19 infection),1 2 3 4 5 6 7 8 9 10
    (?i)(?:COVID-19 positive (?:patient|person|people|veteran)),OTHER_PERSON
    (?i)(?:positive COVID-19 (?:tested )?other_experiencer),COVID-19
    (?i)(?:(?:(?:contact|exposure) (?:with|to)? )?positive COVID-19 (?:patient|person|veteran)),OTHER_PERSON
    (?i)(?:(?:patient|person) (?:who|that) test (?:positive|confirm) for COVID-19),OTHER_PERSON
    (?i)(ref : not detected|history of present illness|does not know|but|therefore|flu|metapneumovirus|;),<IGNORE>
    


```
magic_session.import_relation_from_csv("target_rules.csv", relation_name="TargetTagRules", delimiter=",")
```


```
%%rgxlog
TargetTagMatches(Label, Span, Path) <- FilesContent(Path, Content), TargetTagRules(Pattern, Label), py_rgx_span(Content, Pattern) -> (Span)
```

Before:


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His family recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                      The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                              Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                       neg COVID-19 education .
     sample5.txt |                                                    positive COVID-19 precaution .
     sample6.txt |                                        The patient have reported positive COVID-19 exposure .
     sample7.txt |                          Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    


```
replace_spans("TargetTagMatches", "FilesPaths", magic_session)
```

    printing results for query 'TargetTagMatches(Label, Span, "sample1.txt")':
    []
    
    printing results for query 'TargetTagMatches(Label, Span, "sample2.txt")':
    []
    
    printing results for query 'TargetTagMatches(Label, Span, "sample3.txt")':
    []
    
    printing results for query 'TargetTagMatches(Label, Span, "sample4.txt")':
    []
    
    printing results for query 'TargetTagMatches(Label, Span, "sample5.txt")':
    []
    
    printing results for query 'TargetTagMatches(Label, Span, "sample6.txt")':
      Label   |   Span
    ----------+----------
     COVID-19 | [26, 52)
    
    printing results for query 'TargetTagMatches(Label, Span, "sample7.txt")':
    []
    
    

After:
As we can see in sample6.txt, the covid positive exposure has changed to covid, in order to not give false positive.


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His family recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                      The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                              Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                       neg COVID-19 education .
     sample5.txt |                                                    positive COVID-19 precaution .
     sample6.txt |                                                 The patient have reported COVID-19 .
     sample7.txt |                          Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    

<a id='section-rules'></a>
### [Section Rules](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/section_rules.py):
Here, we'll add a section detection component that defines rules for detecting sections titles, which usually appear before a semicolon.
Section rules are utilized to identify specific section names, enabling the separation of text into different parts. Entities occurring in certain sections are considered positive.

In the original project, the SectionRule class was used to define rules for identifying specific section text. Each SectionRule has the following structure

      SectionRule(category="problem_list", literal="Active Problem List:"),
      SectionRule(category="problem_list", literal="Current Problems:"),
    
    
**Literal** : This specifies the literal section text or word that this rule is targeting.

**Category** : This specifies the section category associated with the identified section.




Similar to the approach used in the concept tagger stage, regex patterns were derived from these literals, and these patterns are stored in the 'section_target_rules.csv' file and are used to match section texts and replace them with their appropriate category.

Each rule in the CSV file follows this format: regexPattern, sectionLabel


```
print_csv_file('section_rules.csv')
```

    (?i)(?:Lab results :),labs :
    (?i)(?:Addendum :),addendum :
    (?i)(?:(?:ALLERGIC REACTIONS|ALLERGIES) :),allergies :
    (?i)(?:(?:CC|Chief Complaint) :),chief_complaint :
    (?i)(?:COMMENTS :),comments :
    (?i)(?:(?:(?:ADMISSION )?DIAGNOSES|Diagnosis|Primary Diagnosis|Primary|Secondary(?: (?:Diagnoses|Diagnosis))) :),diagnoses :
    (?i)(?:(?:Brief Hospital Course|CONCISE SUMMARY OF HOSPITAL COURSE BY ISSUE/SYSTEM|HOSPITAL COURSE|SUMMARY OF HOSPITAL COURSE) :),hospital_course :
    (?i)(?:(?:Imaging|MRI|INTERPRETATION|Radiology) :),imaging :
    (?i)(?:(?:ADMISSION LABS|Discharge Labs|ECHO|Findings|INDICATION|Labs|Micro|Microbiology|Studies|Pertinent Results) :),labs_and_studies :
    (?i)(?:(?:ACTIVE MEDICATIONS(?: LIST)|ADMISSION MEDICATIONS|CURRENT MEDICATIONS|DISCHARGE MEDICATIONS|HOME MEDICATIONS|MEDICATIONS) :),medications :
    (?i)(?:(?:MEDICATIONS AT HOME|MEDICATIONS LIST|MEDICATIONS ON ADMISSION|MEDICATIONS ON DISCHARGE|MEDICATIONS ON TRANSFER|MEDICATIONS PRIOR TO ADMISSION) :),medications :
    (?i)(?:Neuro :),neurological :
    (?i)(?:(?:A/P|MEDICATIONS LIST|ASSESSMENT/PLAN|ASSESSMENT|Clinical Impression|DISCHARGE DIAGNOSES|DISCHARGE DIAGNOSIS) :),observation_and_plan :
    (?i)(?:(?:Discharge Condition|Discharge Disposition|FINAL DIAGNOSES|FINAL DIAGNOSIS|IMPRESSION|Impression and Plan|Impression and Recommendation) :),observation_and_plan :
    (?i)(?:(?:Facility|Service) :),other :
    (?i)(?:(?:Current Medical Problems|History of Chronic Illness|MHx|PAST HISTORY|PAST MEDICAL Hx|PAST SURGICAL HISTORY|PMH|PMHx|PAST MEDICAL HISTORY|UNDERLYING MEDICAL CONDITION) :),past_medical_history :
    (?i)(?:(?:Education|Patient Education|DISCHARGE INSTRUCTIONS/FOLLOWUP|DISCHARGE INSTRUCTIONS|Followup Instructions) :),patient_education :
    (?i)(?:(?:PE|PHYSICAL EXAM|PHYSICAL EXAMINATION) :),physical_exam :
    (?i)(?:(?:Active Problem List|Current Problems|Medical Problems|PROBLEM LIST) :),problem_list :
    (?i)(?:REASON FOR THIS EXAMINATION :),reason_for_examination :
    (?i)(?:(?:Electronic Signature|Signed electronically by) :),signature :
    (?i)(?:(?:PMHSx|PSH|SH|Sexual History:|Social History) :),social_history :
    


```
magic_session.import_relation_from_csv("section_rules.csv", relation_name="SectionRules", delimiter=",")
```


```
%%rgxlog
SectionRulesMatches(Label, Span, Path) <- FilesContent(Path, Content), SectionRules(Pattern, Label), py_rgx_span(Content, Pattern) -> (Span)
?SectionRulesMatches(Label, Span, Path)
```

    printing results for query 'SectionRulesMatches(Label, Span, Path)':
         Label      |  Span   |    Path
    ----------------+---------+-------------
     problem_list : | [0, 14) | sample3.txt
    
    

Before:


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His family recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                      The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                              Problem List : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                       neg COVID-19 education .
     sample5.txt |                                                    positive COVID-19 precaution .
     sample6.txt |                                                 The patient have reported COVID-19 .
     sample7.txt |                          Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    


```
replace_spans("SectionRulesMatches", "FilesPaths", magic_session)
```

    printing results for query 'SectionRulesMatches(Label, Span, "sample1.txt")':
    []
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample2.txt")':
    []
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample3.txt")':
         Label      |  Span
    ----------------+---------
     problem_list : | [0, 14)
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample4.txt")':
    []
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample5.txt")':
    []
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample6.txt")':
    []
    
    printing results for query 'SectionRulesMatches(Label, Span, "sample7.txt")':
    []
    
    

After:
As we can see in sample 3, current problems has changed to problems_list.


```
%%rgxlog
?FilesContent(Path, Content)
```

    printing results for query 'FilesContent(Path, Content)':
        Path     |                                                                Content
    -------------+---------------------------------------------------------------------------------------------------------------------------------------
     sample1.txt | patient presents to be tested for COVID-19 . His family recently tested positive for COVID-19 . COVID-19 results came back positive .
     sample2.txt |                                      The patient be tested for COVID-19 . Results be positive .
     sample3.txt |                              problem_list : like_num . associated_diagnosis like_num . COVID-19 like_num
     sample4.txt |                                                       neg COVID-19 education .
     sample5.txt |                                                    positive COVID-19 precaution .
     sample6.txt |                                                 The patient have reported COVID-19 .
     sample7.txt |                          Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    

### Attribute Assertion:

 Next, we will explore how to assert attributes indicating whether a mention of COVID-19 is positive or not. In our project, we have created a table     named 'CovidAttributes' that contains all attributes for each COVID-19 mention. This table will be used for classifying documents.


```
%%rgxlog
#Here, we employ a pattern to identify entities present in specific sections and mark them as positive,
#and adding them to the 'CovidAttributes' table.

pattern = "(?i)(?:diagnoses :|observation_and_plan :|past_medical_history :|problem_list :)(?:(?!labs :|addendum :|allergies :|chief_complaint :|comments :|family_history :|hospital_course :|imaging :|labs_and_studies :|medications :|neurological :|other :|patient_education :|physical_exam :|reason_for_examination :|signature :|social_history :).)*"
new SectionRulesAttribute(str, str)
SectionRulesAttribute(pattern, "positive")

SectionMatches(Path, Span, CovidAttribute) <- FilesContent(Path, Content), SectionRulesAttribute(Pattern, CovidAttribute), py_rgx_span(Content, Pattern) -> (Span)
?SectionMatches(Path, Span, CovidAttribute)

CovidMatches(Path, Span) <- FilesContent(Path, Content), py_rgx_span(Content, "COVID-19") -> (Span)
?CovidMatches(Path, Span)
```

    printing results for query 'SectionMatches(Path, Span, CovidAttribute)':
        Path     |  Span   |  CovidAttribute
    -------------+---------+------------------
     sample3.txt | [0, 76) |     positive
    
    printing results for query 'CovidMatches(Path, Span)':
        Path     |   Span
    -------------+-----------
     sample1.txt | [34, 42)
     sample1.txt | [85, 93)
     sample1.txt | [96, 104)
     sample2.txt | [26, 34)
     sample3.txt | [58, 66)
     sample4.txt |  [4, 12)
     sample5.txt |  [9, 17)
     sample6.txt | [26, 34)
    
    


```
%%rgxlog
SectionCovidAttributes(Path, CovidSpan, CovidAttribute) <- SectionMatches(Path, Span1, CovidAttribute), CovidMatches(Path, Span2), is_span_contained(Span1, Span2) -> (CovidSpan)
?SectionCovidAttributes(Path, CovidSpan, CovidAttribute)
```

    printing results for query 'SectionCovidAttributes(Path, CovidSpan, CovidAttribute)':
        Path     |  CovidSpan  |  CovidAttribute
    -------------+-------------+------------------
     sample3.txt |  [58, 66)   |     positive
    
    

### Tokenizing the Text into Sentences:

In the subsequent stages, where attributes are assigned to COVID-19 mentions, a departure from the previous stages occurs. Here, patterns are no longer applied to the entire text, instead, they are applied at the sentence level, since the attributes of COVID-19 mentions are typically determined by the context of the sentence in which they appear. This means the text is processed and tokenized into sentences using spaCy's English language model. This process is accomplished through the use of  ie functions and relations.


```
%%rgxlog
#Sentences of the text
Sents(Path, Sent) <- FilesPaths(Path), sent_tokenization(Path) -> (Sent)
?Sents(Path, Sent)

#SentSpan is the span of the sentence in the text
SentSpans(Path, Sent, SentSpan) <- FilesContent(Path, Content), Sents(Path, Sent), py_rgx_span(Content, Sent) -> (SentSpan)
?SentSpans(Path, Sent, SentSpan)
```

    printing results for query 'Sents(Path, Sent)':
        Path     |                                        Sent
    -------------+------------------------------------------------------------------------------------
     sample1.txt |                       COVID-19 results came back positive .
     sample1.txt |                 His family recently tested positive for COVID-19 .
     sample1.txt |                    patient presents to be tested for COVID-19 .
     sample2.txt |                               Results be positive .
     sample2.txt |                        The patient be tested for COVID-19 .
     sample3.txt |                                 COVID-19 like_num
     sample3.txt |                                associated_diagnosis
     sample3.txt |                                     like_num .
     sample3.txt |                             problem_list : like_num .
     sample4.txt |                              neg COVID-19 education .
     sample5.txt |                           positive COVID-19 precaution .
     sample6.txt |                        The patient have reported COVID-19 .
     sample7.txt | Elevated cholesterol levels require further assessment and lifestyle adjustments .
    
    printing results for query 'SentSpans(Path, Sent, SentSpan)':
        Path     |                                        Sent                                        |  SentSpan
    -------------+------------------------------------------------------------------------------------+------------
     sample1.txt |                       COVID-19 results came back positive .                        | [96, 133)
     sample1.txt |                 His family recently tested positive for COVID-19 .                 |  [45, 95)
     sample1.txt |                    patient presents to be tested for COVID-19 .                    |  [0, 44)
     sample2.txt |                               Results be positive .                                |  [37, 58)
     sample2.txt |                        The patient be tested for COVID-19 .                        |  [0, 36)
     sample3.txt |                                 COVID-19 like_num                                  |  [58, 75)
     sample3.txt |                                associated_diagnosis                                |  [26, 46)
     sample3.txt |                                     like_num .                                     |  [15, 25)
     sample3.txt |                                     like_num .                                     |  [47, 57)
     sample3.txt |                             problem_list : like_num .                              |  [0, 25)
     sample4.txt |                              neg COVID-19 education .                              |  [0, 24)
     sample5.txt |                           positive COVID-19 precaution .                           |  [0, 30)
     sample6.txt |                        The patient have reported COVID-19 .                        |  [0, 36)
     sample7.txt | Elevated cholesterol levels require further assessment and lifestyle adjustments . |  [0, 82)
    
    


```
%%rgxlog
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- SectionCovidAttributes(Path, AbsCovidSpan, CovidAttribute),\
SentSpans(Path, Sent, SentSpan) ,get_relative_span(AbsCovidSpan, SentSpan) -> (CovidSpan)
?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)
```

    printing results for query 'CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)':
        Path     |  CovidSpan  |  CovidAttribute  |       Sent
    -------------+-------------+------------------+-------------------
     sample3.txt |   [0, 8)    |     positive     | COVID-19 like_num
    
    

<a id='context-rules'></a>
### [Context Rules](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/context_rules.py):
These rules assign an attribute for each COVID-19 label based on the context, these attributes will be used later to classify each text.

Example for this rule is: 

    ConTextRule(
        literal="Not Detected",
        category="NEGATED_EXISTENCE",
        direction="BACKWARD",
        pattern=[
            {"LOWER": {"IN": ["not", "non"]}},
            {"IS_SPACE": True, "OP": "*"},
            {"TEXT": "-", "OP": "?"},
            {"LOWER": {"REGEX": "detecte?d"}},
        ],
        allowed_types={"COVID-19"},
    ),
   **direction** specify if the allowed_types should be before or after the pattern,
   **allowed_types** specify on what labels should this rule be applied on 


```
print_csv_file('context_rules.csv')
```

    (?i)(?:positive COVID-19|COVID-19 (?:\([^)]*\)) (?:positive|detected)|COVID-19(?: positive)? associated_diagnosis)#positive
    (?i)(?:COVID-19 status : positive)#positive
    (?i)(?:associated_diagnosis COVID-19|associated_diagnosis (?:with|w|w//|from) (?:associated_diagnosis )?COVID-19)#positive
    (?i)(?:COVID-19 positive(?: patient| precaution)?|associated_diagnosis (?:due|secondary) to COVID-19)#positive
    (?i)(?:(?:current|recent) COVID-19 diagnosis)#positive
    (?i)(?:COVID-19 (?:- )?related (?:admission|associated_diagnosis)|admitted (?:due to|(?:with|w|w/)) COVID-19)#positive
    (?i)(?:COVID-19 infection|b34(?:\.)?2|b97.29|u07.1)#positive
    (?i)(?:COVID-19 eval(?:uation)?|(?:positive )? COVID-19 symptoms|rule out COVID-19)#uncertain
    (?i)(?:patient (?:do )?have COVID-19)#positive
    (?i)(?:diagnosis : COVID-19(?: (?:test|screen)(?:ing|ed|s)? positive)?(?: positive)?)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:not|non) (?:- )?detecte?d)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} negative screening|negative screening(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} : negative)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:not be|none) detected)#negated
    (?i)(?:free from(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? not (?:be )?tested)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} not indicated)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? NEGATIVE NEG)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,3} negative test)#negated
    (?i)(?:negative test(?: (?!<IGNORE>)\S+){0,3} COVID-19)#negated
    (?i)(?:without any(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:denie(?:s|d)(?: any| travel)?(?: (?!<IGNORE>)\S+){0,9} COVID-19)#negated
    (?i)(?:no (?:evidence(?: of)?|(?:hx|-hx|history) of|diagnosis (?:of)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:no(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:no (?:positive|one|residents|confirm case|contact(?: w/?(?:ith)?$))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? no confirm case)#negated
    (?i)(?:(?:no|n't) (?:be )? confirm(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:(?:no known|not have)(?: (?!<IGNORE>)\S+){0,4} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:answer(?:ed|s|ing)? (?:no|negative|neg)|negative))#negated
    (?i)(?:(?:answer(?:ed|s|ing)? (?:no|negative|neg)|(?:neg|negative)(?: for)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:not positive(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? not positive)#negated
    (?i)(?:excluded(?: (?!<IGNORE>)\S+){0,3} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,3} excluded)#negated
    (?i)(?:no risk factor for(?: (?!<IGNORE>)\S+){0,4} COVID-19)#uncertain
    (?i)(?:negative screening(?: for)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? screening (?:negative|neg))#negated
    (?i)(?:(?:screening (?:negative|neg) for|do (?:not|n't) have (?:any )?(?:signs|symptoms|ss|s/s))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? do not screening positive)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:be negative|not test positive))#negated
    (?i)(?:(?:be negative|not test positive|not? screening(?: for)|no signs of|no (?:sign|symptom|indication(?:of|for)?)|not? test(?:\S+)? for)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:no exposure|(?:without|w/o) (?:signs|symptoms)(?:or (?:signs|symptoms))|do)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} not have)#negated
    (?i)(?:(?:(?:not|n't) have a (?:positive )?diagnosis|do not meet criteria|no concern (?:for|of)|not? (?:at )risk)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:(?:not|n't) have a (?:positive )?diagnosis|do not meet criteria))#negated
    (?i)(?:(?:no suspicion(?: for)|not suspect|ruled out for|no(?: recent) travel|not be in|clear(?:ed|s|ing) (?:of|for|from))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:not(?: (?!<IGNORE>)\S+){0,3} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:be ruled out|be not likely|not have contact with))#negated
    (?i)(?:(?:no (?:hx|history) (?:of )travel|not have contact with|no symptoms of|no risk factors|no (?:confirm case|report))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:no (?:exposure|contact) (?:to|with)|not test(?:\S+)? positive))#negated
    (?i)(?:(?:no (?:exposure|contact) (?:to|with)|do (?:not|n't) meet(?: screening)(?: criteria)(?: for)|not test(?:\S+)? positive(?: for)|not tested(?: or diagnosis))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:no|any)(?: known) contact(?: with)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,3} : no)#negated
    (?i)(?:(?:(?:not|never) diagnosis with|not been tested (?:for )?or diagnosis with)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} confirm)#positive
    (?i)(?:(?:confirm|known)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#positive
    (?i)(?:(?:(?:test(?:\S+)?)?positive(?: for)?|notif(?:y|ied) of positive (?:results?|test(?:\S+)?|status))(?: (?!<IGNORE>)\S+)*? COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:positiv(?:e|ity)|test(?:\S+)? positive|(?:test|pcr) remains positive|notif(?:y|ied) of positive (?:results?|test(?:ing)?|status)))#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:positiv(?:e|ity)|test(?:\S+)? positive|(?:test|pcr) remains positive|notif(?:y|ied) of positive (?:results?|test(?:ing)?|status)))#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} (?:positive status|results be positive))#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} results positive)#positive
    (?i)(?:results positive(?: (?!<IGNORE>)\S+){0,4} COVID-19)#positive
    (?i)(?:notif(?:y|ied) (?:the )? (?:veteran|patient|family) of positive (?:results?|test(?:ing)?|status)(?: (?!<IGNORE>)\S+)*? COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? notif(?:y|ied) (?:the )? (?:veteran|patient|family) of positive (?:results?|test(?:ing)?|status))#positive
    (?i)(?:likely secondary to(?: (?!<IGNORE>)\S+){0,0} COVID-19)#positive
    (?i)(?:(?:problem(?: list)? (?:of|:)|(?:active|current|acute) problems :|admi(?:t|ssion) diagnosis(?: :)?)(?: (?!<IGNORE>)\S+){0,9} COVID-19)#positive
    (?i)(?:(?:reason for admission :|treatment of|(?:admitting )diagnosis(?: :)?)(?: (?!<IGNORE>)\S+){0,3} COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,3} diagnosis like_num)#positive
    (?i)(?:(?:Reason for admission :|inpatient with|discharged from|in m?icu (?:for|with))(?: (?!<IGNORE>)\S+){0,5} COVID-19)#admission
    (?i)(?:(?:admit(?:ted|s|ting) (?:like_num|with|for)|admitted (?:to|on)|Reason for ICU :|admission for)(?: (?!<IGNORE>)\S+)*? COVID-19)#admission
    (?i)(?:Reason for ED visit or Hospital Admission :(?: (?!<IGNORE>)\S+){0,1} COVID-19)#admission
    (?i)(?:(?:(?:in|to) (?:the )(?:hospital|icu|micu) (?:for|due to)|hospitali(?:zed)?(?: timesx)? (?:for|due to))(?: (?!<IGNORE>)\S+){0,4} COVID-19)#admission
    (?i)(?:(?:diagnosis with|found to be positive for)(?: (?!<IGNORE>)\S+){0,5} COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,5} found to be positive)#positive
    (?i)(?:(?:positive test|presum(?:e|ed|es|ing) positive|not(?: yet)? recover(?:s|ing|ed)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:positive test|presum(?:e|ed|es|ing) positive))#positive
    (?i)(?:(?:management of|ards(?: (?:from|with|secondary to))?|acute respiratory distress|post - extubation)(?: (?!<IGNORE>)\S+){0,2} COVID-19)#positive
    (?i)(?:(?:in(?: the)? setting of|in the s / o|found to have|present(?:s|ed|ing)? with)(?: (?!<IGNORE>)\S+){0,5} COVID-19)#positive
    (?i)(?:resp(?:iratory) failure(?:(?: (?:with|due to))?|like_num|\( like_num \))(?: (?!<IGNORE>)\S+){0,3} COVID-19)#positive
    (?i)(?:(?:active(?: for)|recovering from)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} recovering from)#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} (?:detected|value : detected|POSITIVEH))#positive
    (?i)(?:(?:\d+(?: )?-|like_num )year(?:(?: )?-(?: )?old| old) (?:(?:aa|white|black|hispanic|caucasian) )?(?:\b(?!family\b|other_experiencer\b)\S+\b )?(?:with|w|w/|admitted)(?: (?!<IGNORE>)\S+){0,9} COVID-19)#patient_experiencer
    (?i)(?:(?:like_num (?:y[or]|y / o)|[\d]+yo) (?:\b(?!family\b|other_experiencer\b)\S+\b )?(?:patient |veteran )?(?:with|w|w/)(?: (?!<IGNORE>)\S+){0,9} COVID-19)#patient_experiencer
    (?i)(?:the (?:veteran|vet|patient) have(?: (?!<IGNORE>)\S+){0,2} COVID-19)#patient_experiencer
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} precaution)#future
    (?i)(?:(?:(?:precaution|protection|protect) (?:for|against)|concern about|reports of|vaccine|protect yourself|prevent(?:ed|ion|s|ing)|avoid)(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:prevent(?:ed|ion|s|ing)|vaccine|educat\S*|instruction))#future
    (?i)(?:(?:questions (?:about|regarding|re|concerning|on|for)|(?:anxiety|ask(?:ing|ed|es|ed)?) about|educat(?:ion|ed|ing|ed)?|instruction)(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:(?:information(?: )?(?:on|about|regarding|re)?|protocols?)(?: (?!<IGNORE>)\S+){0,2} COVID-19)#future
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} protocols?)#future
    (?i)(?:(?:materials|fact(?: )?sheet|literature|(?:informat(?:ion|ed|ing) )?handouts?|(?:anxious|worr(?:ied|ies|y|ying)) (?:about|re|regarding))(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:materials|fact(?: )?sheet|literature|(?:informat(?:ion|ed|ing) )?handouts?))#future
    (?i)(?:if(?: (?!<IGNORE>)\S+){0,9} COVID-19)#future
    (?i)(?:(?:advisor(?:y|ies)|travel screen(?: :)?|Travel History Questionnaire|prescreen|front gate)(?: (?!<IGNORE>)\S+)*? COVID-19)#screening
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} (?:questionnaire :|questionn?aire|question\S*|prescreen|front gate))#screening
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,9} screen\S*)#screening
    (?i)(?:screen\S*(?: (?!<IGNORE>)\S+){0,9} COVID-19)#screening
    (?i)(?:have you(?: (?!<IGNORE>)\S+)*? COVID-19)#not relevant
    (?i)(?:(?:mers)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:This patient was screened for the following suspected travel related illness(?:es)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? This patient was screened for the following suspected travel related illness(?:es)?)#future
    (?i)(?:(?:will(?: be) travel|travel plans|if you need|plan to travel)(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:(?:(?:limit|reduce|lower|minimize)(?: the)? (?:risk|chance|possibility) of|if you)(?: (?!<IGNORE>)\S+)*? COVID-19)#future
    (?i)(?:(?:(?:(?:-)?hx|history|) of)(?: (?!<IGNORE>)\S+){0,3} COVID-19)#negated
    (?i)(?:(?:^(?:check|test|retest|eval)(?: for)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#test
    (?i)(?:(?:work(?:-|\s)up)(?: (?!<IGNORE>)\S+)*? COVID-19)#test
    (?i)(?:(?:evaluation)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#test
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} (?:evaluation))#test
    (?i)(?:(?:swab|PCR|specimen sent)(?: (?!<IGNORE>)\S+)*? COVID-19)#test
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:swab|PCR|specimen sent))#test
    (?i)(?:(?:awaiting results|at risk for|risk for|currently being ruled out or has tested positive for|to exclude)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:awaiting results|currently being ruled out or has tested positive for|(?:patient|person) of interest))#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,0} (?:risk))#uncertain
    (?i)(?:(?:investigation of)(?: (?!<IGNORE>)\S+){0,0} COVID-19)#uncertain
    (?i)(?:(?:question of|differential diagnosis :|ddx :)(?: (?!<IGNORE>)\S+){0,3} COVID-19)#uncertain
    (?i)(?:(?:awaiting|questionnaire|r(?:/)?o(?:\.)?)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} (?:awaiting|questionnaire|r(?:/)?o(?:\.)?))#uncertain
    (?i)(?:(?:under investigation|(?:may|might) be positive(?: for)?|flew|tarvel(?:ed)?|travelled)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:under investigation|(?:may|might) be positive))#uncertain
    (?i)(?:(?:facility (?:with|has)(?: a)?|known to have|(?:same )?room|patients with)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:(?:area|county|community|city) (?:with|of)|in the building|(?:several|multiple|one)(?:of )?(?:the )? other_experiencer)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:in the building))#negated
    (?i)(?:(?:(?:he|she) thinks (?:he|she) (?:have|had|has)|\S+ would like)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:positive (?:screen|criteria|triage)|(?:^test )?pending|screen positive|unlikely to be)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:positive (?:screen|criteria|triage)|(?:^test )?pending|screen positive|possible positive))#uncertain
    (?i)(?:(?:(?:possible|potential)? exposure|possibly|possible positive)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:(?:risk of|likely|probable|probably)(?: (?!<IGNORE>)\S+){0,3} COVID-19)#uncertain
    (?i)(?:(?:suspicion(?: for)?|^suspect|differential diagnosis|ddx(?: :)?|doubt)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:suspicion|^suspect|differential diagnosis|ddx(?: :)?|may have been exposed))#uncertain
    (?i)(?:(?:(?:positive )?(?:sign|symptom) of)(?: (?!<IGNORE>)\S+){0,3} COVID-19)#uncertain
    (?i)(?:(?:sx|s/s|rule (?:- )out|be ruled out(?: for)?|^(?:vs\.?|versus)$)(?: (?!<IGNORE>)\S+){0,4} COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} (?:sx|s/s|rule (?:- )out|^(?:vs\.?|versus)$))#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:(?:possible|potential)? exposure|may have been exposed))#uncertain
    (?i)(?:(?:concern(:?s)?(?: for| of)?|if (?:negative|positive)|c/f|assess(?:ed)? for|concerning for)(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:(?:unlikely(?: to be positive)?|low (?:suspicion|probability|risk (?:for|in|of)))(?: (?!<IGNORE>)\S+)*? COVID-19)#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:unlikely(?: to be positive)?|low (?:suspicion|probability)|is unlikely))#uncertain
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,2} (?:extremely low))#uncertain
    (?i)(?:(?:low risk of)(?: (?!<IGNORE>)\S+){0,2} COVID-19)#uncertain
    (?i)(?:(?:(?:other_experiencer|family) ^test positive(?: for)?|any one|contact with(?: known))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:other_experiencer|family)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:other_experiencer|any one|contact with(?: known)))#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,0} (?:(?:a|an|another) \S+ tested positive))#negated
    (?i)(?:(?:had contact|same (?:building|floor)|care for|clean)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:had contact|same (?:building|floor)|care for|clean))#negated
    (?i)(?:(?:concern(?:ed)? about)(?: (?!<IGNORE>)\S+){0,2} COVID-19)#negated
    (?i)(?:(?:patient concern (?:for|of)|desire|(?:concerned|prepare) (?:for|about))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:seen in|a (?:positive|confirmed) case of|cases|epidemic|pandemic)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,1} (?:cases|epidemic|pandemic|national emergency|crisis|situation|mandate|\?))#negated
    (?i)(?:(?:national emergency|crisis|situation|mandate)(?: (?!<IGNORE>)\S+){0,1} COVID-19)#negated
    (?i)(?:(?:seen in(?: the)? setting of)(?: (?!<IGNORE>)\S+){0,5} COVID-19)#negated
    (?i)(?:(?:^cancel (?:flight|plan|trip|vacation)|supposed to (?:travel|go|visit)|called off|goals :)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:^cancel (?:flight|plan|trip|vacation)|supposed to (?:travel|go|visit)|called off))#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:in the (?:area|community)|outbreak))#negated
    (?i)(?:(?:in the (?:area|community)|outbreak)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:news|media|tv|television|broadcast|headline(?:s)?|newspaper(?:s)?|clinic cancellation)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:news|media|tv|television|broadcast|headline(?:s)?|newspaper(?:s)?|clinic cancellation))#negated
    (?i)(?:(?:^read about|deploy|(?:come|been) in close contact(?: with)?)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:^read about|deploy|(?:come|been) in close contact(?: with)?|error))#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:have you had close contact|web(?:\s)?site|internet|world(?:\s|-)?wide|countries with cases))#negated
    (?i)(?:(?:have you had close contact|the group|session|(?:nurse(?:s)?|rn) notes)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:web(?:\s)?site|internet|world(?:\s|-)?wide|countries with cases|error)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:(?:(?:person|patients) with(?: confirmed)?(?: or)?(?: suspected)?|cases of)(?: (?!<IGNORE>)\S+){0,2} COVID-19)#negated
    (?i)(?:elective(?: (?!<IGNORE>)\S+){0,4} COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,4} elective)#negated
    (?i)(?:(?:reschedule|barrier to travel|positive (?:individual(?:s)?|contact(?:s)?|patient(?:s)?))(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:reschedule|barrier to travel|positive (?:individual(?:s)?|contact(?:s)?|patient(?:s)?)))#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:(?:someone|person) who (?:has|have) tested positive|contact with))#negated
    (?i)(?:(?:(?:someone|person) who (?:has|have) tested positive|contact with)(?: (?!<IGNORE>)\S+)*? COVID-19)#negated
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+){0,0} (?:\(resolved\)))#positive
    (?i)(?:COVID-19(?: (?!<IGNORE>)\S+)*? (?:social worker|initially negative|likely recovered|not aware|positive (?:case|symptom|sign)|client history|emergency contact|several positive|special instructions :))#IGNORE
    (?i)(?:(?:social worker|initially negative|likely recovered|not aware|positive (?:case|symptom|sign)|client history|emergency contact|several positive|special instructions :)(?: (?!<IGNORE>)\S+)*? COVID-19)#IGNORE
    


```
magic_session.import_relation_from_csv("context_rules.csv", relation_name="ContextRules", delimiter="#")
```


```
%%rgxlog
#covid_attributes: negated, other_experiencer, is_future, not_relevant, uncertain, positive
ContextMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), ContextRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
?ContextMatches(CovidAttribute, Span, Path, Sent)

CovidSpans(Path, Span, Sent) <- Sents(Path, Sent), py_rgx_span(Sent, "COVID-19") -> (Span)
?CovidSpans(Path, Span, Sent)
```

    printing results for query 'ContextMatches(CovidAttribute, Span, Path, Sent)':
       CovidAttribute    |   Span   |    Path     |                        Sent
    ---------------------+----------+-------------+----------------------------------------------------
          positive       | [0, 17)  | sample5.txt |           positive COVID-19 precaution .
           negated       | [0, 12)  | sample4.txt |              neg COVID-19 education .
          positive       | [27, 48) | sample1.txt | His family recently tested positive for COVID-19 .
          positive       | [0, 35)  | sample1.txt |       COVID-19 results came back positive .
     patient_experiencer | [0, 34)  | sample6.txt |        The patient have reported COVID-19 .
           future        | [9, 28)  | sample5.txt |           positive COVID-19 precaution .
           future        | [4, 22)  | sample4.txt |              neg COVID-19 education .
           negated       | [4, 48)  | sample1.txt | His family recently tested positive for COVID-19 .
    
    printing results for query 'CovidSpans(Path, Span, Sent)':
        Path     |   Span   |                        Sent
    -------------+----------+----------------------------------------------------
     sample1.txt |  [0, 8)  |       COVID-19 results came back positive .
     sample1.txt | [40, 48) | His family recently tested positive for COVID-19 .
     sample1.txt | [34, 42) |    patient presents to be tested for COVID-19 .
     sample2.txt | [26, 34) |        The patient be tested for COVID-19 .
     sample3.txt |  [0, 8)  |                 COVID-19 like_num
     sample4.txt | [4, 12)  |              neg COVID-19 education .
     sample5.txt | [9, 17)  |           positive COVID-19 precaution .
     sample6.txt | [26, 34) |        The patient have reported COVID-19 .
    
    


```
%%rgxlog
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- ContextMatches(CovidAttribute, Span1, Path, Sent), CovidSpans(Path, Span2, Sent), is_span_contained(Span1, Span2) -> (CovidSpan)
?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)
```

    printing results for query 'CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)':
        Path     |  CovidSpan  |   CovidAttribute    |                        Sent
    -------------+-------------+---------------------+----------------------------------------------------
     sample1.txt |   [0, 8)    |      positive       |       COVID-19 results came back positive .
     sample1.txt |  [40, 48)   |       negated       | His family recently tested positive for COVID-19 .
     sample1.txt |  [40, 48)   |      positive       | His family recently tested positive for COVID-19 .
     sample3.txt |   [0, 8)    |      positive       |                 COVID-19 like_num
     sample4.txt |   [4, 12)   |       future        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       negated       |              neg COVID-19 education .
     sample5.txt |   [9, 17)   |       future        |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      positive       |           positive COVID-19 precaution .
     sample6.txt |  [26, 34)   | patient_experiencer |        The patient have reported COVID-19 .
    
    

<a id='postprocess-rules'></a>
### [Postprocessor](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/postprocess_rules.py):
The postprocessor is designed to apply extra adjustments to the processed text using custom logic or specific requirements not addressed by the spaCy pipeline. These rules modify, remove, or change attributes for each mention of COVID-19 based on either their existing attributes, the context of the sentences in which they appear, or a combination of both. This flexibility allows us to address data issues and implement targeted improvements. For instance, it proves useful in identifying and rectifying incorrectly labeled positive cases, thereby enhancing the accuracy of our classification.

**How we implemented it:**  
As mentioned earlier, postprocess rules are responsible for modifying, removing, or changing attributes for each mention of COVID-19. In the original project, these attributes are represented as boolean variables stored in an object class for each COVID-19 mention. The rules simply switch the corresponding boolean variable to assign or remove the attribute. However, in rgxlog, we don't have the luxury of creating classes. In our project, when we want to remove a specific attribute, we introduce an additional attribute that acts as its negation. For instance, for the attribute 'positive,' we add 'no_positive,' causing the document classifier to behave as if there is no positive attribute.

Additionally, in some cases, the entire COVID-19 mention is removed by eliminating its object. In our project, we introduce an 'IGNORE' attribute, which results in the exclusion of the mention from consideration in the document classifier stage.
<br>

**In the subsequent cells, we will explore three types of postprocess rules:**
1) Rules based on patterns
2) Rules utilizing existing attributes and patterns
3) Rules applied to the next sentence.

#### 1) Postprocess rules based on patterns:

Example rule in the original project:

```
PostprocessingRule(
        patterns=[
            PostprocessingPattern(lambda ent: ent.label_ == "COVID-19"),
            PostprocessingPattern(
                postprocessing_functions.sentence_contains,
                condition_args=({"deny", "denies", "denied"},),
            ),
            PostprocessingPattern(
                postprocessing_functions.sentence_contains,
                condition_args=({"contact", "contacts", "confirmed"},),
            ),
        \],
        action=postprocessing_functions.remove_ent,
        description="Remove a coronavirus entity if 'denies' and 'contact' are in. This will help get rid of false positives from screening.",
    ),    
```
This rule iterates through each entity and checks a series of conditions which are the "PostprocessingPattern". If all conditions evaluate as True, then some action is taken on the entity, which is 'remove' action in this example.


In our case, we assign "IGNORE" attribute to the COVID-19 mention causing it to be excluded from consideration during the document classification process.

Each rule in the CSV file follows this format: regexPattern, Attribute


```
print_csv_file('postprocess_pattern_rules.csv')
```

    .*education.*#IGNORE
    .* \?#IGNORE
    (?=.*\b(?:deny|denies|denied)\b)(?=.*\b(?:contact|confirm)\b).*#IGNORE
    (?=.*\b(?:setting of|s/o)\b)(?!.*\b(?:COVID-19 infection|COVID-19 ards)\b).*#no_positive
    (?i)(.*benign.*)#uncertain
    admitted to COVID-19 unit#positive
    


```
magic_session.import_relation_from_csv("postprocess_pattern_rules.csv", relation_name="PostprocessRules", delimiter="#")
```


```
%%rgxlog
PostprocessMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), PostprocessRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
?PostprocessMatches(CovidAttribute, Span, Path, Sent)
```

    printing results for query 'PostprocessMatches(CovidAttribute, Span, Path, Sent)':
      CovidAttribute  |  Span   |    Path     |           Sent
    ------------------+---------+-------------+--------------------------
          IGNORE      | [0, 24) | sample4.txt | neg COVID-19 education .
    
    


```
%%rgxlog
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- PostprocessMatches(CovidAttribute, Span1, Path, Sent), CovidSpans(Path, Span2, Sent), is_span_contained(Span1, Span2) -> (CovidSpan)
?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)
```

    printing results for query 'CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)':
        Path     |  CovidSpan  |   CovidAttribute    |                        Sent
    -------------+-------------+---------------------+----------------------------------------------------
     sample1.txt |   [0, 8)    |      positive       |       COVID-19 results came back positive .
     sample1.txt |  [40, 48)   |       negated       | His family recently tested positive for COVID-19 .
     sample1.txt |  [40, 48)   |      positive       | His family recently tested positive for COVID-19 .
     sample3.txt |   [0, 8)    |      positive       |                 COVID-19 like_num
     sample4.txt |   [4, 12)   |       IGNORE        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       future        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       negated       |              neg COVID-19 education .
     sample5.txt |   [9, 17)   |       future        |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      positive       |           positive COVID-19 precaution .
     sample6.txt |  [26, 34)   | patient_experiencer |        The patient have reported COVID-19 .
    
    

#### 2) Postprocess rules utilizing existing attributes and patterns:
```
PostprocessingRule(
        patterns=[
        
            PostprocessingPattern(lambda ent: ent.label_ == "COVID-19"),
            PostprocessingPattern(
                postprocessing_functions.is_modified_by_category,
                condition_args=("DEFINITE_POSITIVE_EXISTENCE",),
            ),
            # PostprocessingPattern(postprocessing_functions.is_modified_by_category, condition_args=("TEST",)),
            PostprocessingPattern(
                postprocessing_functions.sentence_contains,
                condition_args=(
                    {
                        "should",
                        "unless",
                        "either",
                        "if comes back",
                        "if returns",
                        "if s?he tests positive",
                    },
                    True,
                ),
            ),
        ],
        action=set_is_uncertain,
        action_args=(True,),
        description="Subjunctive of test returning positive. 'Will contact patient should his covid-19 test return positive.'",
    ),
```
This rule examines whether a COVID-19 mention possesses a positive attribute and if the sentence containing it includes any of the words specified in 'condition_args' If these conditions are met, the uncertain attribute is set to true.


In our case, we check for each COVID-19 mention in the 'CovidAttributes' table if it's labeled as 'positive', also, we check if any of the specified words in 'condition_args' are present in the same sentence using a regex search. If the conditions are met, then we simply assign it an 'uncertain' attribute.

Each rule in the CSV file follows this format: regexPattern, ExistingAttribute, NewAttribute



```
print_csv_file('postprocess_attributes_rules.csv')
```

    .*pending.*#negated#no_negated
    .*(?:should|unless|either|if comes back|if returns|if s?he tests positive).*#positive#uncertain
    .*precaution.*#positive#no_future
    .*(?:re[ -]?test|second test|repeat).*#negated#no_negated
    .*(?:sign|symptom|s/s).*#positive#uncertain
    


```
magic_session.import_relation_from_csv("postprocess_attributes_rules.csv", relation_name="PostprocessRulesWithAttributes", delimiter="#")
```


```
%%rgxlog
PostprocessWithAttributesMatches(CovidAttribute, NewAttribute, Span, Path, Sent) <- Sents(Path, Sent), PostprocessRulesWithAttributes(Pattern, CovidAttribute, NewAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
?PostprocessWithAttributesMatches(CovidAttribute, NewAttribute, Span, Path, Sent)
```

    printing results for query 'PostprocessWithAttributesMatches(CovidAttribute, NewAttribute, Span, Path, Sent)':
      CovidAttribute  |  NewAttribute  |  Span   |    Path     |              Sent
    ------------------+----------------+---------+-------------+--------------------------------
         positive     |   no_future    | [0, 30) | sample5.txt | positive COVID-19 precaution .
    
    


```
%%rgxlog
CovidAttributes(Path, CovidSpan, NewAttribute, Sent) <- CovidAttributes(Path, CovidSpan, CovidAttribute, Sent), PostprocessWithAttributesMatches(CovidAttribute, NewAttribute, Span, Path, Sent)
?CovidAttributes(Path, CovidSpan, NewAttribute, Sent)
```

    printing results for query 'CovidAttributes(Path, CovidSpan, NewAttribute, Sent)':
        Path     |  CovidSpan  |    NewAttribute     |                        Sent
    -------------+-------------+---------------------+----------------------------------------------------
     sample1.txt |   [0, 8)    |      positive       |       COVID-19 results came back positive .
     sample1.txt |  [40, 48)   |       negated       | His family recently tested positive for COVID-19 .
     sample1.txt |  [40, 48)   |      positive       | His family recently tested positive for COVID-19 .
     sample3.txt |   [0, 8)    |      positive       |                 COVID-19 like_num
     sample4.txt |   [4, 12)   |       IGNORE        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       future        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       negated       |              neg COVID-19 education .
     sample5.txt |   [9, 17)   |       future        |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      no_future      |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      positive       |           positive COVID-19 precaution .
     sample6.txt |  [26, 34)   | patient_experiencer |        The patient have reported COVID-19 .
    
    

#### 3) Postprocess rules applied to the next sentence:
There's a rule that checks if the following sentence contains positive mentions. If it does, the COVID-19 mentions in the current sentence are also
marked as positive. To Implement this rule in our project, we defined a new relation that pairs each sentence with its subsequent sentence.



```
def next_sent(text_path):
    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    # Tokenize sentences
    sentences = list(doc.sents)
    for i in range(len(sentences) - 1):  # Iterate until the second-to-last sentence
        yield(sentences[i].text, sentences[i + 1].text)

magic_session.register(ie_function=next_sent, ie_function_name = "next_sent", in_rel=[DataTypes.string], out_rel=[DataTypes.string,DataTypes.string])
```


```
# usage example
for first_sent, second_sent in next_sent("sample1.txt"):
    print(f"sentence: {first_sent}", f"next sentence: {second_sent}")
```

    sentence: patient presents to be tested for COVID-19 . next sentence: His family recently tested positive for COVID-19 .
    sentence: His family recently tested positive for COVID-19 . next sentence: COVID-19 results came back positive .
    


```
%%rgxlog
NextSent(Path, Sent1, Sent2) <- FilesPaths(Path), next_sent(Path) -> (Sent1, Sent2)
?NextSent(Path, Sent1, Sent2)
```

    printing results for query 'NextSent(Path, Sent1, Sent2)':
        Path     |                       Sent1                        |                       Sent2
    -------------+----------------------------------------------------+----------------------------------------------------
     sample1.txt | His family recently tested positive for COVID-19 . |       COVID-19 results came back positive .
     sample1.txt |    patient presents to be tested for COVID-19 .    | His family recently tested positive for COVID-19 .
     sample2.txt |        The patient be tested for COVID-19 .        |               Results be positive .
     sample3.txt |                associated_diagnosis                |                     like_num .
     sample3.txt |                     like_num .                     |                 COVID-19 like_num
     sample3.txt |             problem_list : like_num .              |                associated_diagnosis
    
    


```
%%rgxlog
new PostProcessWithNextSentenceRules(str, str)
PostProcessWithNextSentenceRules("(?i)(?:^(?:positive|detected)|results?(?: be)? positive)", "positive")
PostProcessWithNextSentenceMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), PostProcessWithNextSentenceRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)

CovidAttributes(Path, CovidSpan, CovidAttribute, Sent1) <- CovidSpans(Path, CovidSpan, Sent1), NextSent(Path, Sent1, Sent2), PostProcessWithNextSentenceMatches(CovidAttribute, Span, Path, Sent2)
?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)
```

    printing results for query 'CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)':
        Path     |  CovidSpan  |   CovidAttribute    |                        Sent
    -------------+-------------+---------------------+----------------------------------------------------
     sample1.txt |   [0, 8)    |      positive       |       COVID-19 results came back positive .
     sample1.txt |  [40, 48)   |       negated       | His family recently tested positive for COVID-19 .
     sample1.txt |  [40, 48)   |      positive       | His family recently tested positive for COVID-19 .
     sample2.txt |  [26, 34)   |      positive       |        The patient be tested for COVID-19 .
     sample3.txt |   [0, 8)    |      positive       |                 COVID-19 like_num
     sample4.txt |   [4, 12)   |       IGNORE        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       future        |              neg COVID-19 education .
     sample4.txt |   [4, 12)   |       negated       |              neg COVID-19 education .
     sample5.txt |   [9, 17)   |       future        |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      no_future      |           positive COVID-19 precaution .
     sample5.txt |   [9, 17)   |      positive       |           positive COVID-19 precaution .
     sample6.txt |  [26, 34)   | patient_experiencer |        The patient have reported COVID-19 .
    
    

<a id='document_classifier'></a>
### [Document Classifier](https://github.com/abchapman93/VA_COVID-19_NLP_BSV/blob/master/cov_bsv/knowledge_base/document_classifier.py):
Now we have the basic pieces in place to make our document classification. Each document is classified as either 'POS', 'UNK', or 'NEG' determined by the attributes of its COVID-19 mentions. The Results are stored in a DataFrame.

Document Classifier stage has 2 parts:
 1) **Attribute filtering**: Our pipeline assigns various attributes to each COVID-19 mention. However, during this stage, each COVID-19 case is refined to possess only one attribute. This filtering process operates based on specific conditions outlined in the 'attribute_filter' function.
 2) **Document classification**: Documents are classified based on distinct conditions, as detailed in the 'classify_doc_helper' function. This step ensures the accurate categorization of each document according to the specified criteria.



```
def attribute_filter(group):
    """
    Filters attributes within each "CovidSpan" of a DataFrame table based on specific conditions.

    Parameters:
        group (pandas.Series): A pandas Series representing attributes for each "CovidSpan" within a DataFrame.

    Returns:
        str: Filtered "CovidSpan" attribute determined by the following rules:
            - If 'IGNORE' is present, returns 'IGNORE'.
            - If 'negated' is present (and 'no_negated' is not present), returns 'negated'.
            - If 'future' is present (and 'no_future' is not present), returns 'negated'.
            - If 'other experiencer' or 'not relevant' is present, returns 'negated'.
            - If 'positive' is present (and 'uncertain' and 'no_positive' are not present), returns 'positive'.
            - Otherwise, returns 'uncertain'.
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
```


```
# usage example
data = {'Path': ["sample1.txt", "sample1.txt", "sample1.txt", "sample2.txt"],
        'Attribute': ['IGNORE', 'negated', 'positive', 'positive']}
df_example = pd.DataFrame(data)
print("Before:")
print(df_example)

df_example['Attribute'] = df_example.groupby(['Path'])['Attribute'].transform(attribute_filter)
df_example = df_example.drop_duplicates().reset_index(drop=True)
print("\nAfter:")
print(df_example)
```

    Before:
              Path Attribute
    0  sample1.txt    IGNORE
    1  sample1.txt   negated
    2  sample1.txt  positive
    3  sample2.txt  positive
    
    After:
              Path Attribute
    0  sample1.txt    IGNORE
    1  sample2.txt  positive
    


```
df = (magic_session.run_commands("?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)", print_results=False, format_results=True))[0]
if len(df) == 0:
    df = DataFrame(columns=["Path","CovidSpan","CovidAttribute"])
df['CovidAttribute'] = df.groupby(['CovidSpan', 'Sent'])['CovidAttribute'].transform(attribute_filter)
df = df.drop_duplicates().reset_index(drop=True)
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
      <th>Path</th>
      <th>CovidSpan</th>
      <th>CovidAttribute</th>
      <th>Sent</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>sample1.txt</td>
      <td>[0, 8)</td>
      <td>positive</td>
      <td>COVID-19 results came back positive .</td>
    </tr>
    <tr>
      <th>1</th>
      <td>sample1.txt</td>
      <td>[40, 48)</td>
      <td>negated</td>
      <td>His family recently tested positive for COVID-...</td>
    </tr>
    <tr>
      <th>2</th>
      <td>sample2.txt</td>
      <td>[26, 34)</td>
      <td>positive</td>
      <td>The patient be tested for COVID-19 .</td>
    </tr>
    <tr>
      <th>3</th>
      <td>sample3.txt</td>
      <td>[0, 8)</td>
      <td>positive</td>
      <td>COVID-19 like_num</td>
    </tr>
    <tr>
      <th>4</th>
      <td>sample4.txt</td>
      <td>[4, 12)</td>
      <td>IGNORE</td>
      <td>neg COVID-19 education .</td>
    </tr>
    <tr>
      <th>5</th>
      <td>sample5.txt</td>
      <td>[9, 17)</td>
      <td>positive</td>
      <td>positive COVID-19 precaution .</td>
    </tr>
    <tr>
      <th>6</th>
      <td>sample6.txt</td>
      <td>[26, 34)</td>
      <td>uncertain</td>
      <td>The patient have reported COVID-19 .</td>
    </tr>
  </tbody>
</table>
</div>




```
def classify_doc_helper(group):
    """
Classifies a document as 'POS', 'UNK', or 'NEG' based on COVID-19 attributes.

Parameters:
    group (pandas.Series): A pandas Series representing COVID-19 attributes for each document within a DataFrame.
    
Returns:
    str: Document classification determined as follows:
         - 'POS': If at least one COVID-19 attribute with "positive" is present in the group.
         - 'UNK': If at least one COVID-19 attribute with "uncertain" is present in the group and no "positive" attributes,
                  or there's at least one COVID-19 attribute with 'IGNORE' and no other COVID-19 attributes exist.
         - 'NEG': Otherwise.
"""
    if 'positive' in group.values:
        return 'POS'
    elif 'uncertain' in group.values:
        return 'UNK'
    elif 'negated' in group.values:
        return 'NEG'
    else:
        return 'UNK'
```


```
# usage example
data = {'Path': ["sample1.txt", "sample1.txt", "sample1.txt", "sample2.txt"],
        'Attribute': ['uncertain', 'negated', 'positive', 'positive']}
df_example = pd.DataFrame(data)
print("Before:")
print(df_example)

df_example['DocResult'] = df_example.groupby(['Path'])['Attribute'].transform(classify_doc_helper)
df_example = df_example[['Path', 'DocResult']]
df_example = df_example.drop_duplicates().reset_index(drop=True)
print("\nAfter:")
print(df_example)
```

    Before:
              Path  Attribute
    0  sample1.txt  uncertain
    1  sample1.txt    negated
    2  sample1.txt   positive
    3  sample2.txt   positive
    
    After:
              Path DocResult
    0  sample1.txt       POS
    1  sample2.txt       POS
    


```
df['DocResult'] = df.groupby('Path')['CovidAttribute'].transform(classify_doc_helper)
df = df[['Path', 'DocResult']]
df = df.drop_duplicates().reset_index(drop=True)
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
      <th>Path</th>
      <th>DocResult</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>sample1.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>1</th>
      <td>sample2.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>2</th>
      <td>sample3.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>3</th>
      <td>sample4.txt</td>
      <td>UNK</td>
    </tr>
    <tr>
      <th>4</th>
      <td>sample5.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>5</th>
      <td>sample6.txt</td>
      <td>UNK</td>
    </tr>
  </tbody>
</table>
</div>



#### Handling unmentioned paths:
At this step, we assign a classification result 'UNK' to paths not identified in the previous DataFrame result. This occurs when our pipeline doesn't detect any mention of COVID-19 or its synonyms in the text of those paths. As a result, these paths are excluded from all types of relations, consistent with our primary focus on COVID-19 entities.


```
df_path = (magic_session.run_commands("?FilesPaths(Path)", print_results=False, format_results=True))[0]
df = (pd.merge(df, df_path, on='Path', how='outer'))
df['DocResult'] = df['DocResult'].fillna("UNK")
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
      <th>Path</th>
      <th>DocResult</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>sample1.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>1</th>
      <td>sample2.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>2</th>
      <td>sample3.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>3</th>
      <td>sample4.txt</td>
      <td>UNK</td>
    </tr>
    <tr>
      <th>4</th>
      <td>sample5.txt</td>
      <td>POS</td>
    </tr>
    <tr>
      <th>5</th>
      <td>sample6.txt</td>
      <td>UNK</td>
    </tr>
    <tr>
      <th>6</th>
      <td>sample7.txt</td>
      <td>UNK</td>
    </tr>
  </tbody>
</table>
</div>



<a id='bringing-all-together'></a>
### Bringing It All Together

In this section, we will directly compare the original Python Spacy pipeline project with its rgxlog counterpart. Our emphasis is on showcasing the overall brevity of the rgxlog implementation in contrast to the Python Spacy pipeline.

#### Code Metrics

Let's commence by providing an estimated count of total lines in each implementation:

- **Total Number of Lines in the original Python implementation:** **4435**
- **Total Number of Lines in our rgxlog implementation:** **596** (7 times smaller!)<br>

And here's a detailed comparison:

![Screenshot%20%2825%29.png](covid_pipeline_files/Screenshot%20%2825%29.png)

Now, we will present the combined rgxlog and python code (excluding "generic ie" functions and excluding queries) to visually illustrate the compactness of the implementation:

#### Concept tagger:
```python
def lemmatize_text(text_path, lemma_words_path):
    # Define a list of words to be lemmatized
    lemma_words = [line.strip() for line in open(f"{lemma_words_path}") if line.strip()]

    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    lemmatized_text = ""
    for token in doc:
        if token.lemma_ in lemma_words:
            lemmatized_text += token.lemma_
        elif token.like_num:
            lemmatized_text += "like_num"
        else:
            lemmatized_text += token.text
        lemmatized_text += " "

    # Write the lemmatized text back to the same file
    with open(text_path, 'w') as file:
        file.writelines(lemmatized_text)

    yield lemmatized_text

def annotate_text_with_pos(text_path):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    for token in doc:
        if token.pos_ in ["NOUN", "PROPN", "PRON", "ADJ"]:
            yield token.pos_, Span(token.idx, token.idx + len(token.text))
        else:
            yield tuple()
```

```python
session.import_relation_from_csv("concept_tags_rules.csv", relation_name="ConceptTagRules", delimiter=",")

%%rgxlog
LemmaMatches(Label, Span, Path) <- FilesContent(Path, Content), ConceptTagRules(Pattern, Label, "lemma"), py_rgx_span(Content, Pattern) -> (Span)
replace_spans("LemmaMatches", "FilesPaths")
POSTable(POS, Span, Path) <- FilesContent(Path, Content), annotate_text_with_pos(Path) -> (POS, Span)
POSMatches(Label, Span, Path) <- FilesContent(Path, Content), ConceptTagRules(Pattern, Label, "pos"), py_rgx_span(Content, Pattern) -> (Span)
POSRuleMatches(Label, Span, Path) <- POSTable(POS, Span, Path), POSMatches(Label, Span, Path)
replace_spans("POSRuleMatches", "FilesPaths")
```

#### Target matcher:
```python
magic_session.import_relation_from_csv("target_rules.csv", relation_name="TargetTagRules", delimiter=",")

%%rgxlog
TargetTagMatches(Label, Span, Path) <- FilesContent(Path, Content), TargetTagRules(Pattern, Label), py_rgx_span(Content,Pattern) -> (Span)
replace_spans("TargetTagMatches", "FilesPaths")
```

#### Sectionizer:
```python

magic_session.import_relation_from_csv("section_rules.csv", relation_name="SectionRules", delimiter=",")

%%rgxlog
SectionRulesMatches(Label, Span, Path) <- FilesContent(Path, Content), SectionRules(Pattern, Label), py_rgx_span(Content,Pattern) -> (Span)
replace_spans("SectionRulesMatches", "FilesPaths")

pattern = "(?i)(?:diagnoses :|observation_and_plan :|past_medical_history :|problem_list :)(?:(?!labs :|addendum :|allergies :|chief_complaint :|comments :|family_history :|hospital_course :|imaging :|labs_and_studies :|medications :|neurological :|other :|patient_education :|physical_exam :|reason_for_examination :|signature :|social_history :).)*"

new SectionRulesAttribute(str, str)
SectionRulesAttribute(pattern, "positive")
SectionMatches(Path, Span, CovidAttribute) <- FilesContent(Path, Content), SectionRulesAttribute(Pattern, CovidAttribute), py_rgx_span(Content, Pattern) -> (Span)
CovidMatches(Path, Span) <- FilesContent(Path, Content), py_rgx_span(Content, "COVID-19") -> (Span)
SectionCovidAttributes(Path, CovidSpan, CovidAttribute) <- SectionMatches(Path, Span1, CovidAttribute), CovidMatches(Path, Span2), is_span_contained(Span1, Span2) -> (CovidSpan)

Sents(Path, Sent) <- FilesPaths(Path), sent_tokenization(Path) -> (Sent)
SentSpans(Path, Sent, SentSpan) <- FilesContent(Path, Content), Sents(Path, Sent), py_rgx_span(Content, Sent) -> (SentSpan)

CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- SectionCovidAttributes(Path, AbsCovidSpan, CovidAttribute),\
SentSpans(Path, Sent, SentSpan) ,get_relative_span(AbsCovidSpan, SentSpan) -> (CovidSpan)
 
```

#### Context matcher:
```python
magic_session.import_relation_from_csv("context_rules.csv", relation_name="ContextRules", delimiter="#")

%%rgxlog
ContextMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), ContextRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
CovidSpans(Path, Span, Sent) <- Sents(Path, Sent), py_rgx_span(Sent, "COVID-19") -> (Span)
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- ContextMatches(CovidAttribute, Span1, Path, Sent), CovidSpans(Path, Span2, Sent), is_span_contained(Span1, Span2) -> (CovidSpan)
```

#### Postprocessor:
```python
def next_sent(text_path):
    with open(text_path, 'r') as file:
        contents = file.read()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(contents)

    # Tokenize sentences
    sentences = list(doc.sents)
    for i in range(len(sentences) - 1):  # Iterate until the second-to-last sentence
        yield(sentences[i].text, sentences[i + 1].text)

magic_session.register(ie_function=next_sent, ie_function_name = "next_sent", in_rel=[DataTypes.string], out_rel=[DataTypes.string,DataTypes.string])
```

```python
magic_session.import_relation_from_csv("postprocess_pattern_rules.csv", relation_name="PostprocessRules", delimiter="#")

%%rgxlog
PostprocessMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), PostprocessRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent) <- PostprocessMatches(CovidAttribute, Span1, Path, Sent), CovidSpans(Path, Span2, Sent), is_span_contained(Span1, Span2) -> (CovidSpan)

NextSent(Path, Sent1, Sent2) <- FilesPaths(Path), next_sent(Path) -> (Sent1, Sent2)
new PostProcessWithNextSentenceRules(str, str)
PostProcessWithNextSentenceRules("(?i)(?:^(?:positive|detected)|results?(?: be)? positive)", "positive")
PostProcessWithNextSentenceMatches(CovidAttribute, Span, Path, Sent) <- Sents(Path, Sent), PostProcessWithNextSentenceRules(Pattern, CovidAttribute),\
py_rgx_span(Sent, Pattern) -> (Span)
CovidAttributes(Path, CovidSpan, CovidAttribute, Sent1) <- CovidSpans(Path, CovidSpan, Sent1), NextSent(Path, Sent1, Sent2), PostProcessWithNextSentenceMatches(CovidAttribute, Span, Path, Sent2)
```

#### Document Classifier:
```python
def attribute_filter(group):
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

df = (magic_session.run_commands("?CovidAttributes(Path, CovidSpan, CovidAttribute, Sent)", print_results=False, format_results=True))[0]
if len(df) == 0:
    df = DataFrame(columns=["Path","CovidSpan","CovidAttribute"])
df['CovidAttribute'] = df.groupby(['CovidSpan', 'Sent'])['CovidAttribute'].transform(attribute_filter)
df = df.drop_duplicates().reset_index(drop=True)

def classify_doc_helper(group):
    if 'positive' in group.values:
        return 'POS'
    elif 'uncertain' in group.values:
        return 'UNK'
    elif 'negated' in group.values:
        return 'NEG'
    else:
        return 'UNK'
        
df['DocResult'] = df.groupby('Path')['CovidAttribute'].transform(classify_doc_helper)
df = df[['Path', 'DocResult']]
df = df.drop_duplicates().reset_index(drop=True)

df_path = (magic_session.run_commands("?FilesPaths(Path)", print_results=False, format_results=True))[0]
df = (pd.merge(df, df_path, on='Path', how='outer'))
df['DocResult'] = df['DocResult'].fillna("UNK")
df
```
