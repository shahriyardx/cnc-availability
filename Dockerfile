FROM python:3.8.16-slim-buster

WORKDIR /app

RUN apt-get update

COPY cogs ./cogs
COPY essentials ./essentials
COPY prisma ./prisma
COPY main.py requirements.txt .env ./

RUN pip install -r requirements.txt
RUN python -m prisma generate

CMD [ "prisma", "db", "push", "&&", "python", "main.py" ]