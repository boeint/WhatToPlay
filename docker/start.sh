#!/bin/sh
# Container start-up: bring the database schema up to date, then run the app.
# The database may still be starting (e.g. right after a server reboot), so
# the migration step is retried for a while before giving up.
set -e

attempts=30
delay=5

echo "WhatToPlay: applying database migrations..."
i=1
until alembic upgrade head; do
  if [ "$i" -ge "$attempts" ]; then
    echo "WhatToPlay: database still unreachable after $attempts attempts. Check DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD."
    exit 1
  fi
  echo "WhatToPlay: database not reachable yet (attempt $i/$attempts), retrying in ${delay}s..."
  i=$((i + 1))
  sleep "$delay"
done

echo "WhatToPlay: starting the web server on port 8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
