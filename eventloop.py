#!/usr/bin/env python
# encoding: utf-8


import os
import socket
import errno
import select
import logging
import traceback


__all__ = ['EventLoop', 'EPOLL_NULL', 'EPOLL_IN',
        'EPOLL_OUT', 'EPOLL_ERR', 'EPOLL_HUP', 'EVENT_NAMES']


EPOLL_NULL = 0x00
EPOLL_IN = select.EPOLLIN
EPOLL_OUT = select.EPOLLOUT
EPOLL_ERR = select.EPOLLERR
EPOLL_HUP = select.EPOLLHUP


EVENT_NAMES = {
    EPOLL_NULL: 'EPOLL_NULL',
    EPOLL_IN: 'EPOLL_IN',
    EPOLL_OUT: 'EPOLL_OUT',
    EPOLL_ERR: 'EPOLL_ERR',
    EPOLL_HUP: 'EPOLL_HUP',
}



class EpollLoop(object):
    '''using epoll event loop'''

    def __init__(self):
        self._epoll = select.epoll()

    def poll(self, timeout):
        return self._epoll.poll(timeout)

    def add_fd(self, fd, mode):
        self._epoll.register(fd, mode)

    def remove_fd(self, fd):
        self._epoll.unregister(fd)

    def modify_fd(self, fd, mode):
        self._epoll.modify(fd, mode)

    def close(self):
        self._epoll.close()

class EventLoop(object):

    TIMEOUT=3.6

    def __init__(self):
        self._impl = EpollLoop()
        self._fd_to_sock = {}
        self._handlers = []
        self.stopping = False

    def poll(self, timeout=None):
        events = self._impl.poll(timeout)
        return [ (self._fd_to_sock[fd], fd, event) for fd, event in events]

    def add(self, sock, mode):
        fd = sock.fileno()
        self._fd_to_sock[fd] = sock
        self._impl.add_fd(fd, mode)

    def remove(self, sock):
        fd = sock.fileno()
        del self._fd_to_sock[fd]
        self._impl.remove_fd(fd)

    def modify(self, sock, mode):
        fd = sock.fileno()
        self._impl.modify_fd(fd, mode)

    def add_handler(self, handler):
        self._handlers.append(handler)

    #copy paste modify from shadowsocks/eventloop.py
    def run(self):
        logging.info("starting eventloop...")
        while not self.stopping:
            try:
                events = self.poll(self.TIMEOUT)
            except (OSError, IOError) as e:
                if errno_from_exception(e) == errno.EPIPE:
                    # Happens when the client closes the connection
                    logging.error('poll:%s', e)
                    continue
                else:
                    logging.error('poll:%s', e)
                    traceback.print_exc()
                    continue
            for handler in self._handlers:
                # TODO when there are a lot of handlers
                try:
                    handler(events)
                except (OSError, IOError) as e:
                    logging.error(e)
                    traceback.print_exc()

    def close(self):
        self.stopping = True
        self._impl.close()


# from tornado
def errno_from_exception(e):
    """Provides the errno from an Exception object.

    There are cases that the errno attribute was not set so we pull
    the errno out of the args but if someone instatiates an Exception
    without any args you will get a tuple error. So this function
    abstracts all that behavior to give you a safe way to get the
    errno.
    """

    if hasattr(e, 'errno'):
        return e.errno
    elif e.args:
        return e.args[0]
    else:
        return None


# from tornado
def get_sock_error(sock):
    error_number = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    return socket.error(error_number, os.strerror(error_number))

