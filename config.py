import os


class Config(object):
    QUEUE_USER = os.getenv('RABBITMQ_DEFAULT_USER', 'queue')
    QUEUE_PASS = os.getenv('RABBITMQ_DEFAULT_PASS', 'queue')
    QUEUE_HOST = os.getenv('RABBITMQ_HOST', 'queue')
    QUEUE_PORT = os.getenv('RABBITMQ_PORT', 5672)

    FREQUENCY_REQUEST = float(os.getenv('FREQUENCY_REQUEST', 1))
