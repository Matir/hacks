FROM debian:testing

ARG apt_http_proxy

RUN echo "APT Proxy: ${apt_http_proxy}"
RUN http_proxy=${apt_http_proxy} apt-get -yy update && \
    http_proxy=${apt_http_proxy} apt-get -yy install \
        python3-pip \
        python3-venv \
        pipenv \
        procps \
        strace \
        python3-dev \
        python3-mysqldb \
        python3-pandas \
        python3-pwntools \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
        git \
        jupyter \
        jupyter-server \
        python3-jupyterlab-server \
        python3

RUN useradd -m jovian

USER jovian

ENV VENV_DIR=/home/jovian/jupyter

RUN python3 -m venv ${VENV_DIR}

RUN ${VENV_DIR}/bin/pip install \
        jupyterlab \
        jupyterlab-vim \
        jupyterlab-git \
        jupyterlab_theme_solarized_dark \
        pandas \
        mysqlclient \
        pwntools

ENV LAB_DIR=/home/jovian/lab
ENV JUPYTER_PASSWORD=
ENV NOTEBOOK_DIR=${LAB_DIR}/notebooks

RUN mkdir -p ${LAB_DIR}/notebooks
COPY --chown=jovian jupyter.sh /home/jovian/jupyter.sh
RUN chmod 700 /home/jovian/jupyter.sh

VOLUME ${LAB_DIR}

WORKDIR ${LAB_DIR}

EXPOSE 9999/tcp

CMD "/home/jovian/jupyter.sh"
