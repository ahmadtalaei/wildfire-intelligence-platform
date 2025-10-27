FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client library
RUN pip install --no-cache-dir psycopg2-binary

# Copy the data generator script
COPY generate_monitoring_data.py /app/

# Make it executable
RUN chmod +x /app/generate_monitoring_data.py

# Run the generator
CMD ["python", "-u", "/app/generate_monitoring_data.py"]
