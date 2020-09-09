#!/bin/bash

CHROME=$(which google-chrome)
CHROME_VERSION_MAJOR=$(${CHROME} --version | cut -d' ' -f 3 | cut -d. -f1)
CHROME_DRIVER_VERSION=$(curl https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION_MAJOR})

echo "Chrome Driver Version is: ${CHROME_DRIVER_VERSION}"

curl \
  -o chromedriver.zip \
  https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip

unzip chromedriver.zip
rm chromedriver.zip
chmod +x ./chromedriver
