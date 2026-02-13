#!/bin/bash
# Initialize database
# Usage: ./init-db.sh

set -e

echo "🗄️ Initializing Malim database..."

# Run migrations
python -m src.db.migrations

echo "✅ Database initialized!"
