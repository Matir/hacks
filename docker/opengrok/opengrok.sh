#!/bin/bash

VOL=/src

if [ \! -d ${VOL} ] ; then
  echo 'Mount source code as a volume on /src.'
  exit 1
fi

if [ su -s /bin/sh -c "find ${VOL} ! -readable 2>/dev/null" tomcat8 | wc -l -gt 0 ] ; then
  echo "tomcat8 can't read all the files, making a copy"
  O_VOL="${VOL}"
  VOL=/src_readable
  mkdir -p ${VOL}
  cp -r ${O_VOL} ${VOL}
  chown -R tomcat8:tomcat8 ${VOL}
fi

service tomcat8 start
${OPENGROK_INSTANCE_BASE}/bin/OpenGrok index /src

# kludge
while true ; do
  sleep 3600
done
