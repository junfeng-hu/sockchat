# coding: utf-8
import sys
import socket
import argparse
import threading
import json
import Queue

import utils

SERVER_ADDR = "127.0.0.1"

q = Queue.Queue()

def hanldesock(clientsocket, address):
    "thread target func"
    s = utils.SockHandle(clientsocket, address)
    data = s.read()
    data = json.loads(data)
    data = dict(data=data, sock=clientsocket, addr=address)
    q.put(data)

def worker():
    "work thread func"
    while True:
        data = q.get()
        print data
        "handle data"

def runserver():

    parse = argparse.ArgumentParser("Server Options")
    parse.add_argument("-p", "--port", default=8000, type=int, help="set listen port")
    args = parse.parse_args()
    port = args.port

    serversocket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind( (SERVER_ADDR, port))
    serversocket.listen(5)

    workthread = threading.Thread(target=worker)
    workthread.setDaemon(True)
    workthread.start()

    while True:
        print "before accept"
        (clientsocket, address) = serversocket.accept()
        clientthread = threading.Thread(target=hanldesock, args=(clientsocket, address))
        clientthread.setDaemon(True)
        clientthread.start()

    '''
    try:
        while True:
            print "before accept"
            (clientsocket, address) = serversocket.accept()
            clientthread = threading.Thread(target=hanldesock, args=(clientsocket, address))
            clientthread.setDaemon(True)
            clientthread.start()
    except KeyboardInterrupt:
        sys.exit(0)
    '''

if __name__ == "__main__":
    runserver()
