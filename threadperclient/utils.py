#!/usr/bin/env python
# encoding: utf-8

SIZE = 2048
class SockHandle(object):
    "read write socket data"
    def __init__(self, clientsocket, address):
        self.sock = clientsocket
        self.addr = address

    def read(self):
        chunks = []
        while True:
            chunk = self.sock.recv(SIZE)
            chunks.append(chunk)
            if len(chunk) < SIZE:
                break
        return "".join(chunks)

    def write(self, data):
        self.sock.send(data)


