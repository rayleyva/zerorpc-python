# -*- coding: utf-8 -*-
# Based on https://github.com/traviscline/gevent-zeromq/blob/master/gevent_zeromq/core.py

import zmq

import gevent.event
import gevent.core

STOP_EVERYTHING = False

class ZMQSocket(zmq.Socket):

    def __init__(self, context, socket_type):
        super(ZMQSocket, self).__init__(context, socket_type)
        on_state_changed_fd = self.getsockopt(zmq.FD)
        self._readable = gevent.event.Event()
        self._writable = gevent.event.Event()
        try:
            # gevent>=1.0
            self._state_event = gevent.hub.get_hub().loop.io(on_state_changed_fd,
                    gevent.core.READ)
            self._state_event.start(self._on_state_changed)
        except AttributeError:
            # gevent<1.0
            self._state_event = gevent.core.read_event(on_state_changed_fd,
                    self._on_state_changed, persist=True)

    def _on_state_changed(self, event=None, _evtype=None):
        if self.closed:
            self._writable.set()
            self._readable.set()
            return

        events = self.getsockopt(zmq.EVENTS)
        if events & zmq.POLLOUT:
            self._writable.set()
        if events & zmq.POLLIN:
            self._readable.set()

    def close(self):
        if not self.closed and getattr(self, '_state_event', None):
            try:
                # gevent>=1.0
                self._state_event.stop()
            except AttributeError:
                # gevent<1.0
                 self._state_event.cancel()
        super(ZMQSocket, self).close()

    def send(self, data, flags=0, copy=True, track=False):
        if flags & zmq.NOBLOCK:
            return super(ZMQSocket, self).send(data, flags, copy, track)
        flags |= zmq.NOBLOCK
        while True:
            try:
                return super(ZMQSocket, self).send(data, flags, copy, track)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    raise
            self._writable.clear()
            self._writable.wait()

    def recv(self, flags=0, copy=True, track=False):
        if flags & zmq.NOBLOCK:
            return super(ZMQSocket, self).recv(flags, copy, track)
        flags |= zmq.NOBLOCK
        while True:
            try:
                return super(ZMQSocket, self).recv(flags, copy, track)
            except zmq.ZMQError, e:
                if e.errno != zmq.EAGAIN:
                    raise
            self._readable.clear()
            while not self._readable.wait(timeout=10):
                events = self.getsockopt(zmq.EVENTS)
                if bool(events & zmq.POLLIN):
                    print "here we go, nobody told me about new messages!"
                    global STOP_EVERYTHING
                    STOP_EVERYTHING = True
                    raise gevent.GreenletExit()

zmq_context = zmq.Context()

def server():
    socket = ZMQSocket(zmq_context, zmq.REP)
    socket.bind('ipc://zmqbug')

    class Cnt:
        responded = 0

    cnt = Cnt()

    def responder():
        while not STOP_EVERYTHING:
            msg = socket.recv()
            socket.send(msg)
            cnt.responded += 1

    gevent.spawn(responder)

    while not STOP_EVERYTHING:
        print "cnt.responded=", cnt.responded
        gevent.sleep(0.5)

def client():
    socket = ZMQSocket(zmq_context, zmq.XREQ)
    socket.connect('ipc://zmqbug')

    class Cnt:
        recv = 0
        send = 0

    cnt = Cnt()

    def recvmsg():
        while not STOP_EVERYTHING:
            socket.recv()
            socket.recv()
            cnt.recv += 1

    def sendmsg():
        while not STOP_EVERYTHING:
            socket.send('', flags=zmq.SNDMORE)
            socket.send('hello')
            cnt.send += 1
            gevent.sleep(0)

    gevent.spawn(recvmsg)
    gevent.spawn(sendmsg)

    while not STOP_EVERYTHING:
        print "cnt.recv=", cnt.recv, "cnt.send=", cnt.send
        gevent.sleep(0.5)

gevent.spawn(server)
client()
