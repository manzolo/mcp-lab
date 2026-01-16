FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY agent.py gui.py ./
COPY lib/ ./lib/

ENTRYPOINT ["python", "agent.py"]
