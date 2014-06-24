#!/usr/bin/env python
# encoding: utf-8

import sys
import socket
import errno
import logging
import traceback
import json
import urllib


import eventloop


BUF_SIZE = 32 * 1024

def prompt(userid="You") :
    sys.stdout.write('<%s> ' % userid)
    sys.stdout.flush()


class ChatClient(object):


    _STATE = eventloop.EPOLL_IN | eventloop.EPOLL_ERR | eventloop.EPOLL_HUP
    def __init__(self, addr, port):
        self._loop = None
        self._closed = False
        self._logined = False
        chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        chat_socket.setblocking(False)
        try:
            chat_socket.connect( (addr, port))
        except socket.error, e:
            if e[0] != errno.EINPROGRESS:
                traceback.print_exc()
                raise e
        logging.info("conecting address: %s port: %d...",addr, port)
        self._chat_socket = chat_socket
        self._stdin = sys.stdin
        self._stdout = sys.stdout
        self._readbuf = ""
        self._writebuf = ""
        self._name = ""
        self._password = ""

    def add_to_loop(self, loop):
        if self._loop:
            raise Exception('already add to loop')
        if self._closed:
            raise Exception('already closed')
        self._loop = loop
        loop.add_handler(self._handle_events)

        self._loop.add(self._chat_socket, self._STATE)

        self._loop.add(self._stdin, eventloop.EPOLL_IN\
                | eventloop.EPOLL_ERR)

    def closed(self):
        return self._closed

    def _check_closed(self):
        if self.closed():
            raise IOError("client socket is closed")

    def close(self):
        self._closed = True

    def _handle_events(self, events):
        for f, fd, event in events:
            #if f:
            #   logging.info('f:%s fd %d %s', str(f), fd,
            #            eventloop.EVENT_NAMES.get(event, event))
            if f == self._chat_socket:
                self._handle_sock_event(event)
            elif f == self._stdin:
                self._handle_stdin_event(event)
            else:
                logging.error("don't know type f: %s", str(f))

        state = self._STATE
        if len(self._writebuf) > 0:
            state |= eventloop.EPOLL_OUT
        self._loop.modify(self._chat_socket, state)


    def _handle_sock_event(self, event):
        if self.closed():
            raise Exception('client_socket error')

        if event & eventloop.EPOLL_IN:
            self._on_read_sock()

        if self.closed():
            raise Exception('client_socket error')

        if event & eventloop.EPOLL_OUT:
            self._on_write_sock()

        if event & (eventloop.EPOLL_ERR | eventloop.EPOLL_HUP):
            self.close()
            raise Exception('client_socket error')

    def _handle_stdin_event(self, event):
        CMD = ["sign", "login", "list", "send", "logout", "help"]
        CMD_FORMATS = ["<sign name password>",
                "<login name password>",
                "<list>",
                "<send from to message>",
                "<logout>",
                "<help>"
                ]
        if event & eventloop.EPOLL_IN:
            meg = self._stdin.readline().strip()
            if not meg:
                return
            messages = meg.split(" ")
            cmd = messages[0]
            if cmd in CMD:
                if cmd == "help":
                    print "Please use these formats"
                    for c in CMD_FORMATS:
                        print c
                elif cmd == "sign":
                    self._dosign(messages)
                elif cmd == "login":
                    self._dologin(messages)
                elif cmd == "list":
                    self._dolist(messages)
                elif cmd == "send":
                    self._dosend(messages)
                elif cmd == "logout":
                    self._dologout(messages)
                else:
                    pass
            else:
                print "Please use these formats"
                for c in CMD_FORMATS:
                    print c

        if event & (eventloop.EPOLL_ERR | eventloop.EPOLL_HUP):
            logging.error("stdin error. event: %d", event)

        if not self._name:
            prompt()
        else:
            prompt(self._name)


    def _on_read_sock(self):
        try:
            tmp = self._chat_socket.recv(BUF_SIZE)
        except socket.error, e:
            logging.error(e)
            if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                return
            else:
                self.close()
                raise Exception('client_socket error')
        if not tmp:
            self.close()
            raise Exception('client_socket error')

        self._readbuf += tmp
        messages = None
        if "&" in tmp:
            messages = self._readbuf.split("&")
            self._readbuf = messages[-1]
            messages = messages[0:-1]
        if messages:
            print "Response:"
            for meg in messages:
                meg = json.loads(urllib.unquote(meg))
                logging.info(meg)
                self._handle_meg(meg)

    def _handle_meg(self, meg):

        action = meg["action"]
        status = meg["status"]
        if status == "ok":
            print "action <%s> successed" % action
            print "status: <%s>" % status
            if action == "login":
                self._logined = True
            elif action == "logout":
                self._logined = False
            elif action == "list":
                print "online users:"
                online_users = meg["users"]
                for u in online_users:
                    print "name: <%s>" % u
            elif action == "recv":
                From = meg["from_"]
                To = meg.get("to", None)
                info = meg["info"]
                if To == None:
                    meg_type = "broadcast"
                else:
                    meg_type = "private"
                print "receive <%s> message from <%s>" % (meg_type, From)
                print "message: <%s>" % info
            print "info: <%s>" % meg["data"]
        else:
            if status == "error":
                print "action <%s> failured" % action
                print "status: <%s>" % status
                print "info: <%s>" % meg["data"]
            else:
                logging.error("no such status: %s", status)

        if not self._name:
            prompt()
        else:
            prompt(self._name)


    def _on_write_sock(self):
        while self._writebuf:
            try:
                num_bytes = self._chat_socket.send(self._writebuf)
                self._writebuf = self._writebuf[num_bytes:]
            except socket.error, e:
                if e[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    break
                else:
                    logging.error("Write error on %d: %s",
                                    self._user_sock.fileno(), e)
                    self.close()
                    return

    def write(self, req):
        req = urllib.quote(json.dumps(req))
        self._writebuf += (req + "&")

    def _dosign(self, messages):
        self._check_closed()
        if self._logined:
            print ("already logined")
            return
        try:
            cmd, name, password = messages
        except ValueError, e:
            print ("using <%s name password> format" % messages[0])
            return
        self._name = name
        self._password = password
        req = dict(action="sign", name=name, password=password)
        self.write(req)


    def _dologin(self, messages):
        self._check_closed()
        if self._logined:
            print ("already logined")
            return
        try:
            cmd, name, password = messages
        except ValueError, e:
            print ("using <%s name password> format" % messages[0])
            return

        self._name = name
        self._password = password

        req = dict(action="login", name=name, password=password)
        self.write(req)

    def _dolist(self, messages):
        self._check_closed()
        if not self._logined:
            print ("please login first")
            return
        try:
            cmd, = messages
        except ValueError, e:
            print ("using <%s> format" % messages[0])
            return

        req = dict(action="list")
        self.write(req)

    def _dosend(self, messages):
        self._check_closed()
        if not self._logined:
            print ("please login first")
            return
        try:
            cmd, from_, to, message = messages
        except ValueError, e:
            print ("using <%s from to message> format" % messages[0])
            return


        if to == "ALL":
            to = None
        req = dict(action="send", from_=from_, to=to, info=message)
        self.write(req)

    def _dologout(self, messages):
        self._check_closed()
        if not self._logined:
            print ("please login first")
            return
        try:
            cmd, = messages
        except ValueError, e:
            print ("using <%s> format" % messages[0])
            return

        req = dict(action="logout")
        self.write(req)





