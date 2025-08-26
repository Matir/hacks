FROM kalilinux/kali-rolling:latest

# Install necessary tools
RUN apt-get update && \
  DEBIAN_FRONTEND=noninteractive \
  apt-get install -y --no-install-recommends --no-install-suggests \
  python3-venv git build-essential python3-dev pipx \
  chromium chromium-driver \
  nmap masscan subfinder nuclei amass fierce dnsenum \
  autorecon theharvester responder netexec enum4linux-ng \
  gobuster feroxbuster dirsearch ffuf dirb httpx-toolkit \
  nikto sqlmap wpscan arjun paramspider wafw00f \
  hydra john hashcat medusa patator crackmapexec \
  evil-winrm hash-identifier ophcrack-cli \
  gdb-multiarch radare2 binwalk ghidra checksec binutils \
  foremost steghide exiftool \
  tcpdump exploitdb tshark wfuzz xxd python3-pwntools hashcat-utils \
  metasploit-framework python3-ropgadget ropper patchelf \
  aircrack-ng arp-scan autopsy bulk-extractor dotdotpwn hakrawler \
  httpie kismet maltego outguess recon-ng \
  scalpel sherlock sleuthkit spiderfoot testdisk trivy xsser zaproxy


# Create a virtualenv
RUN python3 -m venv /opt/hexstrike-venv
ENV PATH="/opt/hexstrike-venv/bin:$PATH"

# Clone the repository and install requirements
RUN git clone https://github.com/0x4m4/hexstrike-ai.git /opt/hexstrike-ai
WORKDIR /opt/hexstrike-ai
RUN pip install -r requirements.txt

# Add some additional tools
RUN curl -o /usr/local/bin/pwninit \
  https://github.com/io12/pwninit/releases/download/3.3.1/pwninit && \
  chmod 555 /usr/local/bin/pwninit

# Add a volume for data
VOLUME /data

# Expose the port
EXPOSE 8888

# Set the default command
CMD ["python3", "hexstrike_server.py"]
