import amqpstorm

from amqpstorm import Message


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

        result = self.channel.queue.declare(exclusive=True,auto_delete=True)
        self.channel.exchange.declare(self.exchange)
        self.channel.queue.bind(queue=self.queue_name, exchange = self.exchange)
        self.callback_queue = result['queue']

        self.channel.basic.consume(self._on_response, no_ack=True,
                                   queue=self.callback_queue)

    def close(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()

    def __call__(self, number):
        self.response = None
        message = Message.create(self.channel, body=str(number))
        message.reply_to = self.callback_queue
        self.correlation_id = message.correlation_id
        message.publish('', self.exchange)

        while not self.response:
            self.channel.process_data_events(to_tuple=False)
        return int(self.response)

    def _on_response(self, message):
        if self.correlation_id != message.correlation_id:
            return
        self.response = message.body
