FROM python:3.8-alpine

WORKDIR /app

COPY cogs ./cogs
COPY essentials ./essentials
COPY prisma ./prisma
COPY main.py requirements.txt .env ./

RUN pip install -r requirements.txt
RUN prisma generate

CMD [ "prisma", "db", "push", "&&", "python", "-u", "main.py" ]