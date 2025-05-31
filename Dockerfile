FROM python:3.13-alpine

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /bot
COPY . .

CMD python -m bot
