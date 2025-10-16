#!/bin/bash
set -e
echo "create datawarehouse user"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER dwh;
EOSQL
