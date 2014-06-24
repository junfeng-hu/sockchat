#!/usr/bin/env python
# encoding: utf-8

import socket
import eventloop

class UserOnServer(object):

    def __init__(self, server, fd_to_users,
            loop, user_sock):
        self._server = server

        self._fd_to_users = fd_to_users
        fd_to_users[user_sock.fileno()] = self
        self._loop = loop

        self._user_sock = user_sock
        user_sock.setblocking(False)
        user_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        loop.add(local_sock, eventloop.POLL_IN | eventloop.POLL_ERR)






class UserOnClient(object):
    pass
