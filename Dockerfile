FROM jupyter/minimal-notebook:b90cce83f37b
COPY requirements.txt .
RUN pip install -r requirements.txt
