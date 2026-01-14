FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better Docker layer caching
# Note: psycopg2-binary includes pre-built libraries, so no need for build dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY server.py .

CMD ["python", "server.py"]
