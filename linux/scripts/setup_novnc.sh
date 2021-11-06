#!/bin/bash

# Setup a VNC + NoVNC Server
# Done for debian-derivatives with systemd
# Uses a self-signed cert for TLS
# TODO: Let's encrypt support
# Will use desktop :5 to avoid collisions

set -ue

if [[ $(id -u) != "0" ]] ; then
  echo "This must be run as root!" >/dev/stderr
  exit 1
fi

VNCUSER=${1:-}
if test -z "${VNCUSER}" ; then
  read -p "user to run vnc as: " VNCUSER
fi
GEOMETRY=${GEOMETRY:-1440x900}
NOVNCPORT=${NOVNCPORT:-5959}
NOVNCHOST=${NOVNCHOST:-0.0.0.0}
NOVNCWEB=${NOVNCWEB:-/usr/share/novnc/}
VNCHOME=$(eval echo "~${VNCUSER}/.vnc/")
NOSSL=${NOSSL:-0}
SSLCERTFILE=${SSLCERTFILE:-${VNCHOME}/novnc.pem}

# Check username
if ! $(id ${VNCUSER} >/dev/null 2>&1) ; then
  echo "User ${VNCUSER} could not be found!" >/dev/stderr
  exit 1
fi

# Install the VNC server and novnc
apt-get install -yy tightvncserver novnc dbus-x11

# Setup the VNC password
if ! test -f ${VNCHOME}/passwd ; then
  su -c vncpasswd - ${VNCUSER}
fi

# Generate key if needed
if test ${NOSSL} -ne "1" ; then
  openssl req \
    -newkey rsa:2049 \
    -keyout "${SSLCERTFILE}" \
    -out "${SSLCERTFILE}" \
    -sha256 \
    -days 3650 \
    -x509 \
    -nodes \
    -subj "/CN=novnc"
  chown "${VNCUSER}" "${SSLCERTFILE}"
  chmod 400 "${SSLCERTFILE}"
else
  SSLCERTFILE=""
fi

# Write a systemd unit file for tightvncserver
cat <<EOF >/etc/systemd/system/vncserver@:5.service
[Unit]
Description=VNC Server
After=syslog.target network.target

[Service]
Type=forking
User=${VNCUSER}

ExecStart=/usr/bin/vncserver %i -geometry ${GEOMETRY} -localhost
ExecStop=/usr/bin/vncserver -kill %i

[Install]
WantedBy=multi-user.target
EOF

# Write a systemd unit file for novnc
cat <<EOF >/etc/systemd/system/novnc@${NOVNCPORT}.service
[Unit]
Description=NoVNC Server
After=syslog.target network.target

[Service]
Type=exec
User=${VNCUSER}

ExecStart=/usr/bin/websockify --web ${NOVNCWEB} \
    ${SSLCERTFILE:+--cert ${SSLCERTFILE}} \
    ${NOVNCHOST}:${NOVNCPORT} 127.0.0.1:5905
EOF

# Reload files
systemctl daemon-reload

# Enable services
systemctl enable "novnc@${NOVNCPORT}.service" "vncserver@:5.service"

# Start service
systemctl start "novnc@${NOVNCPORT}.service" "vncserver@:5.service"
