import json

import amqpstorm
import time
import logging
from amqpstorm import Message, Connection
from math import sqrt

LOGGER = logging.getLogger()


class FibonacciRpcClient(object):
    def __init__(self, host, username, password, exchange=None, queue_name='fibonacci'):
        """
        :param host: RabbitMQ Server e.g. 127.0.0.1
        :param username: RabbitMQ Username e.g. guest
        :param password: RabbitMQ Password e.g. guest
        :return:
        """
        self.host = host
        self.username = username
        self.password = password
        self.channel = None
        self.response = None
        self.connection = None
        self.callback_queue = None
        self.queue_name = queue_name
        self.correlation_id = None
        self.exchange = exchange
        self.open()

    def open(self):
        self.connection = amqpstorm.Connection(self.host,
                                               self.username,
                                               self.password)

        self.channel = self.connection.channel()

        result = self.channel.queue.declare(exclusive=True, auto_delete=True)
        self.channel.exchange.declare(self.exchange, auto_delete=True)
        self.channel.queue.bind(queue=self.queue_name, exchange=self.exchange)
        self.callback_queue = result['queue']

        self.channel.basic.consume(self._on_response, no_ack=True,
                                   queue=self.callback_queue)

    def close(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()

    def __call__(self, *args):
        self.response = None
        dumps_body = json.dumps(list(args))
        message = Message.create(self.channel, body=dumps_body)
        message.reply_to = self.callback_queue
        self.correlation_id = message.correlation_id
        message.publish('', self.exchange)

        while not self.response:
            self.channel.process_data_events(to_tuple=False)
        result = json.loads(self.response)
        return int(result['result'])

    def _on_response(self, message):
        if self.correlation_id != message.correlation_id:
            return
        self.response = message.body


class RpcServer(object):
    def __init__(self, hostname='127.0.0.1',
                 username='guest', password='guest',
                 rpc_queue='rpc_queue', exchange='rpc_server',
                 max_retries=None):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.rpc_queue = rpc_queue
        self.max_retries = max_retries
        self.exchange_name = exchange
        self._connection = None
        self._consumers = []

    def start_server(self):
        """Start the RPC Server.
        :return:
        """
        if not self._connection or self._connection.is_closed:
            self._create_connection()
        try:
            # Check our connection for errors.
            self._connection.check_for_errors()
            self._update_consumers()
        except amqpstorm.AMQPError as why:
            # If an error occurs, re-connect and let update_consumers
            # re-open the channels.
            LOGGER.warning(why)
            self._stop_consumers()
            self._create_connection()
        time.sleep(1)

    def stop(self):
        """Stop all consumers.
        :return:
        """
        while self._consumers:
            consumer = self._consumers.pop()
            consumer.stop()
        self._connection.close()

    def _create_connection(self):
        """Create a connection.
        :return:
        """
        attempts = 0
        while True:
            attempts += 1
            try:
                self._connection = Connection(self.hostname,
                                              self.username,
                                              self.password)
                break
            except amqpstorm.AMQPError as why:
                LOGGER.warning(why)
                if self.max_retries and attempts > self.max_retries:
                    raise Exception('max number of retries reached')
                time.sleep(min(attempts * 2, 30))
            except KeyboardInterrupt:
                break

    def _update_consumers(self):
        """Update Consumers.
            - Add more if requested.
            - Make sure the consumers are healthy.
            - Remove excess consumers.
        :return:
        """
        # Do we need to start more consumers.
        consumer = Consumer(self.rpc_queue, self.exchange_name)
        self._start_consumer(consumer)

        # Check that all our consumers are active.
        if not consumer.active:
            self._start_consumer(consumer)

    def _start_consumer(self, consumer):
        """Start a consumer as a new Thread.
        :param Consumer consumer:
        :return:
        """
        consumer.start(self._connection)


def fib(number):
    if number == 0:
        return 0
    elif number == 1:
        return 1
    else:
        return ((1 + sqrt(5)) ** number - (1 - sqrt(5)) ** number) / (2 ** number * sqrt(5))


class Consumer(object):
    def __init__(self, rpc_queue, exchange=''):
        self.rpc_queue = rpc_queue
        self.channel = None
        self.active = False
        self.exchange_name = exchange

    def start(self, connection):
        self.channel = None
        try:
            self.active = True
            self.channel = connection.channel(rpc_timeout=10)
            self.channel.basic.qos(1)
            self.channel.queue.declare(self.rpc_queue,auto_delete=True)
            if self.exchange_name != '':
                self.channel.exchange.declare(self.exchange_name, auto_delete=True)
                self.channel.queue.bind(self.rpc_queue, self.exchange_name)
            self.channel.basic.consume(self, self.rpc_queue, no_ack=False)
            self.channel.start_consuming(to_tuple=False)
            if not self.channel.consumer_tags:
                # Only close the channel if there is nothing consuming.
                # This is to allow messages that are still being processed
                # in __call__ to finish processing.
                self.channel.close()
        except amqpstorm.AMQPError as error:
            LOGGER.critical(error)
            pass
        finally:
            self.active = False

    def stop(self):
        if self.channel:
            self.channel.close()

    def __call__(self, message):
        """Process the RPC Payload.
        :param Message message:
        :return:
        """
        args = None
        try:

            args = message.json()
        except BaseException as e:
            LOGGER.error(e)

        LOGGER.debug(isinstance(args,(list)))

        response = fib(*args)
        # response = fib(number)

        properties = {
            'correlation_id': message.correlation_id,
            'content_type': 'application/json',
            'content_encoding': 'UTF-8',
            'headers': {
                'jsonrpc': '2.0',
            }
        }

        response = Message.create(message.channel, json.dumps({'result': response}), properties)
        response.publish(message.reply_to)

        message.ack()
