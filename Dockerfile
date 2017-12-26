FROM python:3.6-alpine

ADD . /service
ENV FLASK_APP=/service/flask-rpc-rabbitmq.py FLASK_CMD=fibonacci_client

RUN pip install -r /service/requirements.txt

ENTRYPOINT /usr/local/bin/flask $FLASK_CMD
