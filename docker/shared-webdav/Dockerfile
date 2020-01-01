FROM nginx:latest

RUN apt-get update && \
    apt-get install openssl && \
    rm -rf /var/lib/apt/lists/*

RUN openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/webdav.key -nodes \
    -out /etc/nginx/webdav.crt -days 3650 -subj '/CN=localhost'

RUN echo "webdav:$(echo -n webdav | openssl passwd -apr1 -stdin)" \
    > /etc/nginx/webdav.passwd

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY nginx.sh /opt/nginx.sh

ENTRYPOINT ["/bin/sh", "/opt/nginx.sh"]
CMD ["nginx", "-g", "daemon off;"]
