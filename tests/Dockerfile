FROM python:3.11-slim

WORKDIR /app

RUN pip install requests

COPY test_mcp.py .

CMD ["python", "test_mcp.py"]
