#!/bin/bash
# DB 일일 백업 스크립트
# crontab: 0 2 * * * /Users/honghyeongi/policonomy/scripts/backup_db.sh >> /Users/honghyeongi/policonomy/logs/backup.log 2>&1

set -e

DB_SRC="/Users/honghyeongi/policonomy/data/policonomy.db"
BACKUP_DIR="/Users/honghyeongi/policonomy/data/backup"
DATE=$(date +%Y-%m-%d)
BACKUP_FILE="$BACKUP_DIR/policonomy_$DATE.db"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_SRC" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: DB 파일 없음: $DB_SRC"
  exit 1
fi

sqlite3 "$DB_SRC" ".backup '$BACKUP_FILE'"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 백업 완료: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# 7일 초과 백업 삭제
find "$BACKUP_DIR" -name "policonomy_*.db" -mtime +$KEEP_DAYS -delete
REMAINING=$(ls "$BACKUP_DIR"/policonomy_*.db 2>/dev/null | wc -l | tr -d ' ')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 보관 중: ${REMAINING}개"
