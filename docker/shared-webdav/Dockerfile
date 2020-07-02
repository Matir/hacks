FROM debian:buster-slim

RUN apt-get update && \
    apt-get -yyf install nginx-full openssl gettext-base && \
    rm -rf /var/lib/apt/lists/*

RUN openssl dhparam -out /etc/nginx/dhparam.pem 3072

RUN openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/webdav.key -nodes \
    -out /etc/nginx/webdav.crt -days 3650 -subj '/CN=localhost'

RUN echo "webdav:$(echo -n webdav | openssl passwd -apr1 -stdin)" \
    > /etc/nginx/webdav.passwd

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY nginx.sh /opt/nginx.sh

RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

RUN userdel www-data

EXPOSE 80
EXPOSE 443

STOPSIGNAL SIGTERM

ENTRYPOINT ["/bin/sh", "/opt/nginx.sh"]
CMD ["nginx", "-g", "daemon off;"]
