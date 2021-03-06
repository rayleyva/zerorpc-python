# -*- coding: utf-8 -*-
# Started by François-Xavier Bourlet <fx@dotcloud.com>, Jan 2012.

from nose.tools import assert_raises
import gevent
import gevent.event

from zerorpc import zmq
import zerorpc

def test_pushpull():
    endpoint = 'ipc://test_pushpull'

    pusher = zerorpc.Pusher()
    pusher.bind(endpoint)
    trigger = gevent.event.Event()

    class Puller(zerorpc.Puller):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    puller = Puller()
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'

def test_pubsub():
    endpoint = 'ipc://test_pubsub'

    pusher = zerorpc.Publisher()
    pusher.bind(endpoint)
    trigger = gevent.event.Event()

    class Subscriber(zerorpc.Subscriber):
        def lolita(self, a, b):
            print 'lolita', a, b
            assert a + b == 3
            trigger.set()

    puller = Subscriber()
    puller.connect(endpoint)
    gevent.spawn(puller.run)

    trigger.clear()
    pusher.lolita(1, 2)
    trigger.wait()
    print 'done'
