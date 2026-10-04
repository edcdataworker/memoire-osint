#!/bin/sh
set -eu
# PostgreSQL requires its private TLS key to be owned by postgres and mode 0600.
install -o postgres -g postgres -m 600 /run/secrets/postgres.key /tmp/server.key
install -o postgres -g postgres -m 644 /run/secrets/postgres.crt /tmp/server.crt
exec docker-entrypoint.sh postgres -c ssl=on -c ssl_cert_file=/tmp/server.crt \
 -c ssl_key_file=/tmp/server.key -c hba_file=/etc/postgresql/pg_hba.conf \
 -c shared_buffers=128MB -c max_connections=40
