#!/bin/sh
set -eu
writer=$(cat /run/secrets/writer)
reader=$(cat /run/secrets/reader)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
 -v writer="$writer" -v reader="$reader" <<'SQL'
CREATE ROLE osint_writer LOGIN PASSWORD :'writer';
CREATE ROLE osint_reader LOGIN PASSWORD :'reader';
SQL
