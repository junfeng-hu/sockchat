# coding: utf-8
import socket
import json

def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect( ("localhost", 8000))
    data = dict(meg="hello, server.")
    s.send(json.dumps(data))
    #data = s.recv(2048)
    #print data
    s.close()

if __name__ == "__main__":
    for i in range(1, 100):
        print ("create client %d" % i)
        connect()

