FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive"

# Security Patch for CVE-2021-44228
ENV LOG4J_FORMAT_MSG_NO_LOOKUPS=true

# Create non-root user & required dirs
RUN useradd -g root -M crafty \
    && mkdir /crafty \
    && chown -R crafty:root /crafty

# Install required system packages
RUN apt-get update \
    && apt-get -y --no-install-recommends install \
        sudo \
        gcc \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        libmariadb-dev \
        default-jre \
        openjdk-8-jre-headless \
        openjdk-11-jre-headless \
        openjdk-16-jre-headless \
        openjdk-17-jre-headless \
    && apt-get autoremove \
    && apt-get clean

# Switch to service user for installing crafty deps
USER crafty
WORKDIR /crafty
COPY --chown=crafty:root requirements.txt ./
RUN python3 -m venv ./.venv \
    && . .venv/bin/activate \
    && pip3 install --no-cache-dir --upgrade setuptools==50.3.2 pip==22.0.3 \
    && pip3 install --no-cache-dir -r requirements.txt \
    && deactivate
USER root

# Copy Source w/ perms & prepare default config from example
COPY --chown=crafty:root ./ ./
RUN mv ./app/config ./app/config_original \
    && mv ./app/config_original/default.json.example ./app/config_original/default.json \
    && chmod +x ./docker_launcher.sh

# Expose Web Interface port & Server port range
EXPOSE 8000
EXPOSE 8443
EXPOSE 19132
EXPOSE 25500-25600

# Start Crafty through wrapper
ENTRYPOINT ["/crafty/docker_launcher.sh"]
CMD ["-d", "-i"]

# Add meta labels
ARG BUILD_DATE
ARG BUILD_REF
ARG CRAFTY_VER
LABEL \
    maintainer="Zedifus <https://gitlab.com/zedifus>" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${CRAFTY_VER} \
    org.opencontainers.image.title="Crafty Controller" \
    org.opencontainers.image.description="A Game Server Control Panel / Launcher" \
    org.opencontainers.image.url="https://craftycontrol.com/" \
    org.opencontainers.image.documentation="https://wiki.craftycontrol.com/" \
    org.opencontainers.image.source="https://gitlab.com/crafty-controller/crafty-4" \
    org.opencontainers.image.vendor="Arcadia Technology, LLC." \
    org.opencontainers.image.licenses="GPL-3.0"
