#!/usr/bin/env python
# encoding: utf-8

import socket
import errno
import logging
import traceback
import json
import urllib
import hashlib

import psycopg2

#user module
import eventloop
import utils

BUF_SIZE = 32 * 1024

conn = utils.get_db_conn(True)

__all__ = ["ChatServer"]

class UserOnServer(object):

    _STATE = eventloop.EPOLL_IN | eventloop.EPOLL_ERR | eventloop.EPOLL_HUP
    def __init__(self, server, fd_to_users, userid_login_status,
            userid_to_fd, loop, user_sock):
        self._closed = False
        self._userid = None
        self._logined = False
        self._readbuf = ""
        self._writebuf = ""

        self._server = server

        fd_to_users[user_sock.fileno()] = self
        self._fd_to_users = fd_to_users

        self._userid_login_status = userid_login_status
        self._userid_to_fd = userid_to_fd

        self._loop = loop

        self._user_sock = user_sock
        self._user_sock_fileno = self._user_sock.fileno()
        user_sock.setblocking(False)
        user_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        loop.add(user_sock, self._STATE)

    def __hash__(self):
        return id(self)


    def closed(self):
        return self._closed

    def _check_closed(self):
        if self.closed():
            raise IOError("client socket is closed")

    def close(self):
        self._closed = True
        if self._user_sock is not None:
            self._loop.remove(self._user_sock)
            if self._logined:
                userid = self._userid
                self._logined = False
                self._userid_login_status[userid] = False
                del self._userid_to_fd[userid]
                self._broadquit()

            fd = self._user_sock.fileno()
            self._user_sock.close()
            del self._fd_to_users[fd]

    def write(self, data):
        self._check_closed()
        self._writebuf += data
        self._need_write()

    def handle_event(self, sock, event):
        if self.closed():
            logging.error("Got events for closed sock: %d", self._user_sock.fileno())
            return
        if event & eventloop.EPOLL_IN:
            self._on_read()
        if self.closed():
            return
        if event & eventloop.EPOLL_OUT:
            self._on_write()
        if self.closed():
            return
        if event & (eventloop.EPOLL_ERR | eventloop.EPOLL_HUP):
            self.close()
        state = self._STATE
        if len(self._writebuf) > 0:
            state |= eventloop.EPOLL_OUT
        self._loop.modify(self._user_sock, state)

    def _need_write(self):
        state = self._STATE
        if len(self._writebuf) > 0:
            state |= eventloop.EPOLL_OUT
        self._loop.modify(self._user_sock, state)

    def _on_read(self):
        try:
            tmp = self._user_sock.recv(BUF_SIZE)
        except socket.error, e:
            logging.error(e)
            if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                return
            else:
                self.close()
        if not tmp:
            self.close()
            return
        message = None
        self._readbuf += tmp
        if "&" in tmp:
            message, self._readbuf = self._readbuf.split("&")
        if message:
            meg = json.loads(urllib.unquote(message))
            action = meg["action"]
            if action == "sign":
                self._handle_sign(meg)
            elif action == "login":
                self._handle_login(meg)
            elif action == "list":
                self._handle_list(meg)
            elif action == "send":
                self._handle_send(meg)
            elif action == "logout":
                self._handle_logout(meg)
            else:
                logging.error("don't support action %s", action)

    def _on_write(self):
        while self._writebuf:
            try:
                num_bytes = self._user_sock.send(self._writebuf)
                self._writebuf = self._writebuf[num_bytes:]
            except socket.error, e:
                if e[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    break
                else:
                    logging.error("Write error on %d: %s",
                                    self._user_sock.fileno(), e)
                    self.close()
                    return

    def _broadquit(self):
        ret = {}
        ret["status"] = "ok"
        ret["data"] = "user %s leave..." % self._userid
        ret["action"] = "broadcast"
        ret = urllib.quote(json.dumps(ret))
        for u, fd in self._userid_to_fd.items():
            if u ==self._userid or self._userid_login_status[u] is not True:
                continue
            user = self._fd_to_users[fd]
            user.write(ret + "&")

    def _broadlogin(self):
        ret = {}
        ret["status"] = "ok"
        ret["data"] = "user %s enter..." % self._userid
        ret["action"] = "broadcast"
        ret = urllib.quote(json.dumps(ret))
        for u, fd in self._userid_to_fd.items():
            if u ==self._userid or self._userid_login_status[u] is not True:
                continue
            user = self._fd_to_users[fd]
            user.write(ret + "&")



    #application layer code
    def _handle_sign(self, meg):
        self._check_closed()
        ret = {}
        ret["action"] = "sign"
        if self._logined:
            ret["status"] = "error"
            ret["data"] = "already logined"
        else:
            name = meg["name"]
            password = meg["password"]
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO users(name, password) VALUES(%s, %s);", (name, _md5(password)))
                cursor.close()
                ret["status"] = "ok"
                ret["data"] = "successfully sign"

            except psycopg2.Error, e:
                logging.error(e)
                ret["status"] = "error"
                ret["data"] = e.message

        ret = urllib.quote(json.dumps(ret))
        self.write(ret + "&")

    def _handle_login(self, meg):
        self._check_closed()
        ret = {}
        ret["action"] = "login"
        if self._logined:
            ret["status"] = "error"
            ret["data"] = "already logined"
        else:
            name = meg["name"]
            password = meg["password"]
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE name=%s and password=%s", (name, _md5(password)))
            user = cursor.fetchone()
            cursor.close()
            if not user:
                ret["status"] = "error"
                ret["data"] = "no such user: %s or password error" % user
            else:
                ret["status"] = "ok"
                ret["data"] = "successfully login"
                self._logined = True
                self._userid = name
                self._userid_login_status[name] = True
                self._userid_to_fd[name] = self._user_sock_fileno
                self._broadlogin()

        ret = urllib.quote(json.dumps(ret))
        self.write(ret + "&")



    def _handle_list(self, meg):
        self._check_closed()
        ret = {}
        ret["action"] = "list"
        if not self._logined:
            ret["status"] = "error"
            ret["data"] = "not login, please login first"
        else:
            ret["status"] = "ok"
            online_users = []
            for u, status in self._userid_login_status.items():
                if status == True:
                    online_users.append(u)
            ret["data"] = "%d online users" % len(online_users)
            ret["users"] = online_users

        ret = urllib.quote(json.dumps(ret))
        self.write(ret + "&")



    def _handle_send(self, meg):
        self._check_closed()
        ret = {}
        ret["action"] = "send"
        if not self._logined:
            ret["status"] = "error"
            ret["data"] = "not login, please login first"
        else:
            From = meg["from_"]
            To = meg.get("to", None)
            info = meg["info"]
            #TODO support file transport
            filename = meg.get("filename", None)
            if filename:
                filedata = meg["filedata"]
            meg["status"] = "ok"
            meg["action"] = "recv"
            meg["data"] = "successfully received message"
            meg_data = urllib.quote(json.dumps(meg))
            if To:
                if self._userid_login_status[To] is not True:
                    ret["status"] = "error"
                    ret["data"] = "user %s not online" % To
                else:
                    fd = self._userid_to_fd[To]
                    user = self._fd_to_users[fd]
                    user.write(meg_data + "&")
                    ret["status"] = "ok"
                    ret["data"] = "successfully send to %s" % To
            else:
                for u, fd in self._userid_to_fd.items():
                    if u ==self._userid or self._userid_login_status[u] is not True:
                        continue
                    user = self._fd_to_users[fd]
                    user.write(meg_data + "&")
                    ret["status"] = "ok"
                    ret["data"] = "successfully broadcast all online users"

        ret = urllib.quote(json.dumps(ret))
        self.write(ret + "&")

    def _handle_logout(self, meg):
        self._check_closed()
        ret = {}
        ret["action"] = "logout"
        if not self._logined:
            ret["status"] = "error"
            ret["data"] = "not login, please login first"
        else:
            self._logined = False
            userid = self._userid
            self._userid_login_status[userid] = False
            del self._userid_to_fd[userid]
            self._broadquit()
            ret["status"] = "ok"
            ret["data"] = "successfully logout"

        ret = urllib.quote(json.dumps(ret))
        self.write(ret + "&")



def _md5(password):
    return hashlib.md5(password).hexdigest()





class ChatServer(object):

    def __init__(self, addr, port):
        self._eventloop = None
        self._closed = False
        self._fd_to_users = {}
        self._userid_to_fd = {}
        self._userid_login_status = {}

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind( (addr, port))
        server_socket.setblocking(False)
        logging.info("starting listen port %d...", port)
        server_socket.listen(1024)
        self._server_socket = server_socket

    def add_to_loop(self, loop):
        if self._eventloop:
            raise Exception('already add to loop')
        if self._closed:
            raise Exception('already closed')
        self._eventloop = loop
        loop.add_handler(self._handle_events)

        self._eventloop.add(self._server_socket,
                            eventloop.EPOLL_IN | eventloop.EPOLL_ERR)

    def _handle_events(self, events):
        for sock, fd, event in events:
            if sock:
                logging.info('fd %d %s', fd,
                        eventloop.EVENT_NAMES.get(event, event))
            if sock == self._server_socket:
                if event & eventloop.EPOLL_ERR:
                    # TODO
                    raise Exception('server_socket error')
                try:
                    client_sock, address = self._server_socket.accept()
                    logging.info('accept client from %s', address)

                    UserOnServer(self, self._fd_to_users, self._userid_login_status,
                            self._userid_to_fd, self._eventloop, client_sock)
                except (OSError, IOError) as e:
                    error_no = eventloop.errno_from_exception(e)
                    if error_no in (errno.EAGAIN, errno.EINPROGRESS):
                        continue
                    else:
                        logging.error(e)
                        traceback.print_exc()
            else:
                if sock:
                    user = self._fd_to_users.get(fd, None)
                    if user:
                        user.handle_event(sock, event)
                else:
                    logging.warn('poll removed fd')


    def close(self):
        self._closed = True
        self._server_socket.close()


