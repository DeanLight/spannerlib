ARG UBUNTU_VER=18.04
FROM ubuntu:${UBUNTU_VER}
ENV DEBIAN_FRONTEND=noninteractive

# Install basic system utilities.
RUN apt-get update -y && apt-get install -y \
      build-essential \
      g++ \
      cmake \
      git-all \
      vim \
      default-jre \
      gawk \
      curl \
      wget \
      jq

### python

ARG CONDA_VER=latest
ARG OS_TYPE=x86_64
ARG PY_VER=3.8.11
# Install miniconda to /miniconda
RUN curl -LO "http://repo.continuum.io/miniconda/Miniconda3-${CONDA_VER}-Linux-${OS_TYPE}.sh"
RUN bash Miniconda3-${CONDA_VER}-Linux-${OS_TYPE}.sh -p /miniconda -b
RUN rm Miniconda3-${CONDA_VER}-Linux-${OS_TYPE}.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

#  downgrade py (optional).
RUN conda install -c anaconda -y python=${PY_VER}

### install rust
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# install spannerlog
COPY . spannerlib
RUN pip install -e spannerlib