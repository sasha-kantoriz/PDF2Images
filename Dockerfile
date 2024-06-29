FROM python:3

ENV PYTHONUNBUFFERED=1

RUN apt-get update -y && apt-get install poppler-utils -y

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

VOLUME /app/pdfs
VOLUME /app/images
VOLUME /app/output

CMD python script.py
