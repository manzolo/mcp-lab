FROM python:3.11-slim

WORKDIR /app

# Install libpq-dev for psycopg2 if needed, but psycopg2-binary usually suffices for slim
# However, best practice for stability might be just requests/fastapi first
RUN pip install fastapi uvicorn psycopg2-binary

COPY server.py .

CMD ["python", "server.py"]
