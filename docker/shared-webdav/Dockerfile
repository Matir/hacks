FROM debian:buster-slim

RUN apt-get update && \
    apt-get -yyf install nginx-full libnginx-mod-http-fancyindex openssl gettext-base unzip && \
    rm -rf /var/lib/apt/lists/*

RUN openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/webdav.key -nodes \
    -out /etc/nginx/webdav.crt -days 3650 -subj '/CN=localhost'

RUN echo "webdav:$(echo -n webdav | openssl passwd -apr1 -stdin)" \
    > /etc/nginx/webdav.passwd

ADD https://github.com/dom111/webdav-js/archive/refs/heads/master.zip /tmp/webdav-js.zip

RUN sh -c "TD=$(mktemp -d);unzip -d \"\${TD}\" /tmp/webdav-js.zip && mv \"\${TD}/webdav-js-master\" /srv/webdav-js && chmod -R ugo=rX /srv/webdav-js"

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY nginx.sh /opt/nginx.sh
COPY header.html /srv/header.html

RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

RUN chmod 444 /srv/header.html

RUN userdel www-data
RUN groupadd nginx && \
  useradd -g nginx -M -r -s /bin/false nginx

EXPOSE 80
EXPOSE 443

STOPSIGNAL SIGTERM

ENTRYPOINT ["/bin/sh", "/opt/nginx.sh"]
CMD ["nginx", "-g", "daemon off;"]
