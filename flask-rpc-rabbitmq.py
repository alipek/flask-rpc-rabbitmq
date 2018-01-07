import logging, time, timeit
from flask import Flask

from queue_tools import FibonacciRpcClient, RpcServer

from pythonjsonlogger import jsonlogger

logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object('config.Config')

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().addHandler(streamHandler)


@app.cli.command()
def fibonacci_client():
    fibonacci_rpc = FibonacciRpcClient(app.config['QUEUE_HOST'], app.config['QUEUE_USER'], app.config['QUEUE_PASS'],
                                       exchange='rpc_server')
    while True:
        for num in range(1, 50):
            starttime = timeit.default_timer()
            response = fibonacci_rpc(num)
            elapsed = timeit.default_timer() - starttime

            logging.info("Response %r for param %d" % (response, num), extra={'time': elapsed})
            time.sleep(app.config['FREQUENCY_REQUEST'])

    fibonacci_rpc.close()


@app.cli.command()
def fibonacci_server():
    RPC_SERVER = RpcServer(hostname=app.config['QUEUE_HOST'],username=app.config['QUEUE_USER'],password=app.config['QUEUE_PASS'],
                           rpc_queue='fibonacci')


    RPC_SERVER.start_server()