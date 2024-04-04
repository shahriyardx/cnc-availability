FROM python:3.8.16-slim-buster

WORKDIR /app
RUN apt-get update

# Install deps
COPY requirements.txt ./
RUN pip install -r --no-cache-dir -I requirements.txt

# Prisma
COPY prisma ./prisma
RUN python -m prisma generate

COPY cogs ./cogs
COPY utils ./utils
COPY essentials ./essentials
COPY main.py requirements.txt credentials.json .env ./

CMD prisma db push && python -u main.py
