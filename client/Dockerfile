FROM python:3.11-slim

WORKDIR /app

RUN pip install requests

COPY agent.py .

ENTRYPOINT ["python", "agent.py"]
