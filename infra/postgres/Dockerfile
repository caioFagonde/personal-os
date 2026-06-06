FROM postgis/postgis:16-3.4

# Prefer the packaged pgvector extension when available. Fall back to a source
# build with an explicit clang compatibility shim for PG images compiled with
# an older LLVM path.
RUN set -eux; \
    apt-get update; \
    if apt-get install -y --no-install-recommends postgresql-16-pgvector; then \
      rm -rf /var/lib/apt/lists/*; \
    else \
      apt-get install -y --no-install-recommends build-essential git postgresql-server-dev-16 ca-certificates clang llvm; \
      if [ ! -x /usr/bin/clang-13 ] && command -v clang >/dev/null 2>&1; then ln -s "$(command -v clang)" /usr/bin/clang-13; fi; \
      git clone --branch v0.8.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector; \
      cd /tmp/pgvector; make; make install; \
      cd /; rm -rf /tmp/pgvector /var/lib/apt/lists/*; \
      apt-get purge -y --auto-remove build-essential git postgresql-server-dev-16 clang llvm || true; \
    fi
