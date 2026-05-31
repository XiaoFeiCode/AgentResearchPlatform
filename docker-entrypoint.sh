#!/bin/bash
set -e

echo "==> SentinelAI backend starting"
echo "==> Waiting for MySQL at ${DB_HOST}:${DB_PORT}..."

# Poll MySQL using pymysql (already in requirements.txt)
until python3 -c "
import os, sys
try:
    import pymysql
    conn = pymysql.connect(
        host=os.environ['DB_HOST'],
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME'],
        connect_timeout=5,
    )
    conn.close()
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
    echo "    MySQL not ready, retrying in 2s..."
    sleep 2
done

echo "==> MySQL is ready. Initializing database tables..."

python3 tools/SentinelSpider/schema/init_database.py

echo "==> Database initialization complete."
echo "==> Starting FastAPI on ${HOST:-0.0.0.0}:${PORT:-5000}..."

exec uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-5000}" --log-level info
