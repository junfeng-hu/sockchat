#!/usr/bin/env python
# encoding: utf-8

import argparse
import logging

import settings
from chatclient import ChatClient
from eventloop import EventLoop


def runclient():

    logging.basicConfig(level=logging.INFO,
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    parse = argparse.ArgumentParser("Client Options")
    parse.add_argument("-a", "--addr", default=settings.ADDR, type=str, help="set connect address")
    parse.add_argument("-p", "--port", default=settings.PORT, type=int, help="set connect port")
    args = parse.parse_args()
    addr = args.addr
    port = args.port
    loop = EventLoop()
    chat_client = ChatClient(addr, port)
    chat_client.add_to_loop(loop)
    try:
        loop.run()
    except (KeyboardInterrupt, IOError, OSError) as e:
        logging.error(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    runclient()
