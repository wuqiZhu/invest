FROM python:3.9-slim

WORKDIR /app

COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

EXPOSE 5000

CMD ["python", "scripts/news_api_server.py"]
