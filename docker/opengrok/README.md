# OpenGrok Docker Container #

Copyright 2018 Google Inc.

Maintainer: [David Tomaschik](https://github.com/Matir/)

This is not an official Google product.

[OpenGrok](https://github.com/oracle/opengrok) is distributed by Oracle under
the CDDL and other open source licenses.

## Execution ##

You need to provide a volume with the code to be analyzed at `/src`.  If it is
not readable by the `tomcat8` user inside the container, a copy will be made, so
for large code repositories, making it world readable is easiest and avoids
copies.

    docker run -p <PORT>:8080 -v <CODEREPO>:/src -d matir/opengrok:latest
