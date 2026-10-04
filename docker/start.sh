#!/bin/sh
# Container start-up.
#  1. As root, only: make the backup folder writable for the app's user, then
#     continue as that user (PUID/PGID, default 99:100 = Unraid's nobody:users).
#  2. Bring the database schema up to date. The database may still be starting
#     (e.g. right after a server reboot), so this is retried for a while.
#  3. Run the web server.
set -e

PUID="${PUID:-99}"
PGID="${PGID:-100}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

if [ "$(id -u)" = "0" ]; then
  if [ -d "$BACKUP_DIR" ]; then
    chown "$PUID:$PGID" "$BACKUP_DIR" || echo "WhatToPlay: could not change the owner of $BACKUP_DIR"
  fi
  exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$0" "$@"
fi

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

echo "WhatToPlay: starting the web server on port 8000 (running as $(id -u):$(id -g))"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
