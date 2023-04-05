FROM python:3.8.16-slim-buster

WORKDIR /app
RUN apt-get update

# Install deps
COPY requirements.txt .env ./
RUN pip install -r requirements.txt

# Prisma
COPY prisma ./prisma
RUN python -m prisma generate

COPY cogs ./cogs
COPY essentials ./essentials
COPY main.py requirements.txt .env ./

CMD [ "prisma", "db", "push", "&&", "python", "main.py" ]