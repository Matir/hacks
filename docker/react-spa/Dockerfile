FROM node:16-buster

RUN mkdir -p /app/src /app/srv/css /app/srv/js

WORKDIR /app

RUN npm install \
  sass @babel/core @babel/cli @babel/preset-react http-server react react-dom

RUN cp /app/node_modules/react/umd/react.development.js /app/srv/js/react.js
RUN cp /app/node_modules/react-dom/umd/react-dom.development.js /app/srv/js/react-dom.js
COPY dev.sh /app
RUN chmod +x /app/dev.sh

VOLUME /app/src
EXPOSE 8080/tcp

CMD /app/dev.sh
