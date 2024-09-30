
FROM ubuntu:20.04

ENV conda_env=chatbot_env

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive PATH=/opt/conda/bin:/home/app.local/bin:$PATH LRU_CACHE_CAPACITY=1 CONDA_DIR=/opt/conda PYTHONUNBUFFERED=1 TZ=Asia/Ho_Chi_Minh

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get -qq update \
    && apt-get -qq install --no-install-recommends \
    ca-certificates git wget sudo libjemalloc-dev lsof \
    libenchant-dev aspell-es \
    && rm -rf /var/lib/apt/lists/*

RUN wget "https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh" && \
    /bin/bash ./Mambaforge-Linux-x86_64.sh -b -p /opt/conda && mamba init bash && \
    ln -s $CONDA_DIR/etc/profile.d/conda.sh /etc/profile.d/conda.sh  && \
    rm ./Mambaforge-Linux-x86_64.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc 

COPY ./docker/chatbot/environment.yaml /home/config/environment.yaml
COPY ./source /home/app
WORKDIR /home/app

RUN conda env create -f /home/config/environment.yaml && \
    conda clean --all -f -y && \
    echo "conda activate $conda_env" >> ~/.bashrc

ENV PATH /opt/conda/envs/$conda_env/bin:$PATH

