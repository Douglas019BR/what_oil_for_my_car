#!/bin/sh
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
INTERVAL=${BACKUP_INTERVAL:-86400}
RETENTION=${BACKUP_RETENTION_DAYS:-7}

mkdir -p "$BACKUP_DIR"

while true; do
	stamp=$(date +%Y%m%d-%H%M%S)
	target="$BACKUP_DIR/what_oil-$stamp.dump"
	if pg_dump --format=custom --file="$target"; then
		echo "backup created: $target"
	else
		echo "backup failed: $target" >&2
		rm -f "$target"
	fi
	find "$BACKUP_DIR" -name 'what_oil-*.dump' -type f -mtime "+$RETENTION" -delete
	sleep "$INTERVAL"
done
