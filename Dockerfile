FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_runner.py .
COPY server.py .

CMD ["python", "bot_runner.py"]
