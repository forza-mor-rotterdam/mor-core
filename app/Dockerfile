FROM python:3.10.10-slim-bullseye

EXPOSE 8000
# Expose uwsgi stats interface
EXPOSE 9191

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    APP_HOME=/app \
    APP_USER=appuser \
    APP_USER_ID=2000 \
    LANG=nl_NL.UTF-8 \
    LANGUAGE=nl_NL \
    LC_ALL=nl_NL.UTF-8

RUN groupadd -r $APP_USER \
    && useradd -r -u $APP_USER_ID -g $APP_USER -d $APP_HOME -s /sbin/nologin -c "Docker image user" $APP_USER \
    && apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get autoremove -y \
    && apt-get install --no-install-recommends -y \
    build-essential \
    python-dev \
    unzip \
    curl \
    wget \
    dnsutils \
    vim-tiny \
    net-tools \
    netcat \
    libgeos-c1v5 \
    gdal-bin \
    postgresql-client \
    libgdal28 \
    libspatialite7 \
    libfreexl1 \
    libgeotiff-dev \
    libwebp6 \
    proj-bin \
    mime-support \
    gettext \
    libwebpmux3 \
    libwebpdemux2 \
    libxml2 \
    libfreetype6 \
    libtiff5 \
    libgdk-pixbuf2.0-0 \
    libmagic1 \
    libcairo2 \
    libpango1.0-0 \
    libpq-dev \
    gcc \
    graphviz \
    graphviz-dev \
    pkg-config \
    git \
    locales \
    && sed -i '/nl_NL.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/* /var/cache/debconf/*-old \
    && update-ca-certificates

WORKDIR /app

COPY . /app/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && mkdir -p /media \
    && mkdir -p /static \
    && chown $APP_USER:$APP_USER /media \
    && chown $APP_USER:$APP_USER /static \
    && chmod 744 /media \
    && chmod 744 /static \
    && mkdir -p /srv/web/var/cache \
    && chown $APP_USER:$APP_USER /srv/web/var/cache \
    && chmod -R ugo+rwx /srv/web/var/cache \
    && chown -R $APP_USER:$APP_USER $APP_HOME \
    && chmod -R +x /app/deploy

USER $APP_USER

ARG GIT_SHA
ENV GIT_SHA=$GIT_SHA
ARG DEPLOY_DATE
ENV DEPLOY_DATE=$DEPLOY_DATE
ARG ENVIRONMENT
ENV ENVIRONMENT=$ENVIRONMENT

CMD ["bash", "/app/deploy/docker-entrypoint.sh"]
