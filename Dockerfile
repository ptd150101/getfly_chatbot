FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc libpq-dev

WORKDIR /app/

COPY ./requirements.txt ./requirements.txt

RUN pip install uv

RUN uv pip install --system -r requirements.txt


COPY . .

EXPOSE 2000
CMD ["python", "source/run.py"]
