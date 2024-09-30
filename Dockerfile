FROM python:3.10-slim

RUN apt-get update && apt-get install -y git
 
WORKDIR /app/

COPY ./requirements.txt ./requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r requirements.txt
 
WORKDIR /app/
 
COPY . .

CMD ["python", "source/run4.py"]
