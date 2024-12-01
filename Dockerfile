FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT 8080
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn -b :${PORT} app:app"]
