FROM debian:bullseye

RUN apt update && \
  apt -yy install nodejs npm yarnpkg

RUN yarnpkg global add wetty

EXPOSE 3000

CMD ["wetty", "--port", "3000", "--command", "/bin/bash", "--base", "/"]
