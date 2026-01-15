FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY test_mcp.py .

CMD ["python", "test_mcp.py"]
