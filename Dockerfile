FROM jupyter/minimal-notebook:notebook-6.4.3

# Reset base image's entrypoint.
USER root
WORKDIR /

# Install basic system utilities.
RUN apt-get update && apt-get install -y \
      build-essential \
      g++ \
      cmake \
      git-all \
      vim \
      default-jre \
      gawk \
      curl

# install rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Python packages listed in 'requirements.txt' using pip.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /spanner_workbench
RUN pip install -e /spanner_workbench/src/rgxlog-interpreter
#RUN python /spanner_workbench/src/rgxlog-interpreter/src/rgxlog/stdlib/nlp.py
#RUN python /spanner_workbench/src/rgxlog-interpreter/src/rgxlog/stdlib/