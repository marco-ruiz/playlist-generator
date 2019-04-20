FROM python:3.7-alpine
MAINTAINER "Marco Ruiz"

WORKDIR /app

COPY requirements.txt /app
RUN pip install -r requirements.txt

COPY . /app

CMD ["python", "playlist.py"]