FROM python:3.5-slim

MAINTAINER Derek M. Frank <derek at frank dot sh>

ENV DB /var/tmp/proxy.sqlite

WORKDIR /app

# Setup app.
COPY . /app

# Install system dependencies.
RUN apt-get update && apt-get install -y \
    sqlite3 libsqlite3-dev

# Install Python dependencies.
RUN pip install -r requirements.txt

# Setup database.
RUN touch "${DB}" \
    && sqlite3 "${DB}" <db-schema.txt

EXPOSE 8080

CMD ["python", "main.py"]
