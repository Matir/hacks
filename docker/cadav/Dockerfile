FROM caddy:2.6.2-builder-alpine AS builder

RUN xcaddy build \
  --with github.com/mholt/caddy-webdav@75a603bc69789413e4213ac746906d4357883929

FROM caddy:2.6.2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

RUN mkdir -p /webdav /srv

COPY Caddyfile /etc/caddy/Caddyfile
# Should be replaced at runtime
COPY Caddyfile.auth /etc/caddy/Caddyfile.auth
COPY index.html /srv/index.html
COPY webdav-style-min.css /srv/webdav-style-min.css
COPY webdav-min.js /srv/webdav-min.js
COPY entrypoint.sh /entrypoint.sh

WORKDIR /srv

# Webdav storage
VOLUME /webdav
# data cache
VOLUME /data
# Config cache
VOLUME /config

# intended to sit behind a TLS-terminating proxy
EXPOSE 9999/tcp

CMD ["/bin/sh", "/entrypoint.sh"]
