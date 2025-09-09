# This Dockerfile allows you to build a custom sandbox image with additional tools.
#
# To build it, run:
#   docker build --build-arg CLI_VERSION_ARG="$(gemini --version)" -t gemini-cli-sandbox-matir:"$(gemini --version)" .
#
# Then, configure the gemini-cli to use this new image:
# gemini --sandbox-image=gemini-cli-sandbox-matir:"$(gemini --version)"

ARG CLI_VERSION_ARG=missing
FROM us-docker.pkg.dev/gemini-code-dev/gemini-cli/sandbox:${CLI_VERSION_ARG}

# Switch to the root user to install packages
USER root

# Example: Install common development tools.
# Add your desired packages here.
RUN apt-get update && apt-get install -y \
    curl \
    git \
    jq \
    shellcheck \
    && rm -rf /var/lib/apt/lists/*

# Increase UID_MAX and GID_MAX
RUN sed -i \
  -e 's/^\(UID_MAX\s\+\)[0-9]\+/\11000000/' \
  -e 's/^\(GID_MAX\s\+\)[0-9]\+/\11000000/' \
  /etc/login.defs

# Switch back to the non-root user
# IMPORTANT: You may need to change 'gemini' to the correct username if it's different
USER node
