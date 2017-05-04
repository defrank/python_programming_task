FROM python:3.5-slim

MAINTAINER Derek M. Frank <derek at frank dot sh>

WORKDIR /app

# Setup app.
COPY . /app

# Install Python dependencies.
RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]
