#!/bin/bash

echo "Starting Data Ingestion Service with auto-table creation..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-wildfire_user} -d ${POSTGRES_DB:-wildfire_db}; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

# Run table generation based on discovered connectors
echo "Discovering connectors and creating tables..."
python /app/src/utils/generate_tables.py execute

# Check if tables were created successfully
if [ $? -eq 0 ]; then
    echo "Tables created/verified successfully"
else
    echo "Warning: Table creation had issues, but continuing..."
fi

# Start the main application
echo "Starting main application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload