FROM postgis/postgis:16-3.4
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git postgresql-server-dev-16 ca-certificates \
    && git clone --branch v0.8.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector && make && make install \
    && rm -rf /tmp/pgvector /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16
