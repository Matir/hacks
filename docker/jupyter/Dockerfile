FROM debian:testing

ARG apt_http_proxy

RUN echo "APT Proxy: ${apt_http_proxy}"
RUN http_proxy=${apt_http_proxy} apt-get -yy update && \
    http_proxy=${apt_http_proxy} apt-get -yy install \
        python3-pip \
        pipenv

RUN pip install jupyterlab

RUN useradd -m jovian

USER jovian

ENV LAB_DIR=/home/jovian/lab
ENV JUPYTER_PASSWORD=

RUN mkdir -p ${LAB_DIR}/notebooks
COPY --chown=jovian jupyter.sh /home/jovian/jupyter.sh
RUN chmod 700 /home/jovian/jupyter.sh

VOLUME ${LAB_DIR}

EXPOSE 9999/tcp

CMD "/home/jovian/jupyter.sh"
