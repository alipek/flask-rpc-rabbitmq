import logging, time, timeit
from flask import Flask

from queue_tools import FibonacciRpcClient

from pythonjsonlogger import jsonlogger

logging.getLogger().setLevel(logging.INFO)

app = Flask(__name__)
app.config.from_object('config.Config')

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().addHandler(streamHandler)


@app.cli.command()
def fibonacci_client():
    fibonacci_rpc = FibonacciRpcClient(app.config['QUEUE_HOST'], app.config['QUEUE_USER'], app.config['QUEUE_PASS'],
                                       exchange='flask-rpc')
    while True:
        for num in range(1, 50):
            starttime = timeit.default_timer()
            response = fibonacci_rpc(num)
            elapsed = timeit.default_timer() - starttime

            logging.info("Response %r for param %f" % (response, elapsed), extra={'time': elapsed})
            time.sleep(app.config['FREQUENCY_REQUEST'])

    fibonacci_rpc.close()
