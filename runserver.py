#!/usr/bin/env python
# encoding: utf-8

import argparse
import logging


import settings

from chatserver import ChatServer

from eventloop import EventLoop

def runserver():

    logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    parse = argparse.ArgumentParser("Server Options")
    parse.add_argument("-p", "--port", default=settings.PORT, type=int, help="set listen port")
    args = parse.parse_args()
    port = args.port
    loop = EventLoop()
    chat_server = ChatServer(settings.ADDR, port)
    chat_server.add_to_loop(loop)
    try:
        loop.run()
    except (KeyboardInterrupt, IOError, OSError) as e:
        logging.error(e)
        import traceback
        traceback.print_exc()



if __name__ == "__main__":
    runserver()
