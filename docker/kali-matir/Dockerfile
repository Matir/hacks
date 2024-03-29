FROM kalilinux/kali-rolling
MAINTAINER david@systemoverlord.com

# Common CLI-based tools from kali
RUN apt-get update && \
  apt-get install -y \
    apktool \
    binutils \
    binutils-multiarch \
    binwalk \
    dnsrecon \
    exploitdb \
    git \
    hping3 \
    hydra \
    libcapstone4 \
    libffi-dev \
    libssl-dev \
    man-db \
    masscan \
    mitmproxy \
    nasm \
    netcat-traditional \
    nmap \
    p7zip-full \
    proxychains \
    python3-pip \
    python3-capstone \
    radare2 \
    set \
    skipfish \
    sqlmap \
    sslscan \
    sslsniff \
    sslsplit \
    sslstrip \
    stunnel4 \
    tcpdump \
    tmux \
    unrar \
    vim \
    wordlists \
    wpscan \
    zsh && \
  apt-get clean

# Setup the locale to en_US.UTF-8
ENV LC_ALL en_US.UTF-8
RUN sed -i 's/# en_US/en_US/' /etc/locale.gen && \
  locale-gen && \
  update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

RUN pip install pwntools && \
  rm -rf /root/.cache/pip

# Matir's personal preferences
RUN chsh -s /bin/zsh
ADD https://github.com/Matir/skel.git#main /root/.skel

ENV HOME /root
ENV USER root

RUN /root/.skel/install.sh

CMD ["/bin/zsh"]
