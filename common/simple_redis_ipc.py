# -*- coding: utf-8 -*-

import redis
import threading
import sys
import time
import json
import Queue

# ipc with multiple client/multiple server through redis.
# There is one public channel per server, each client incr an uniq key and
# listen on a private channel whose name is formed based on the value of the
# incremented key, then client send this channel name with the command to the
# server he choose, server listen on its public channel and reply on the
# private channel the client asked. Command are sent as serialized json
# object, reply from server too, so the python object passed to send_command(),
# send_reply() must be serializable as json.

# The prefix purpose is rather to avoid accidental key name collision rather
# than a dumb security through than to give real security.
# FIXME: allow to choose different prefix for different application or
# force the caller to pass a key of at least 32 char?
key_prefix = '3hdE9rLwpsInqRZ+9GWy2w3/7jrBZBjJmCrYylu3ruE'

class channelListener(threading.Thread):
    def __init__(self, r, channel, queue):
        threading.Thread.__init__(self)
        self.channel = channel
        self.redis = r
        self.pubsub = r.pubsub()
        self.pubsub.subscribe(channel)
        self.queue = queue
        self.force_stop = False

    def work(self, item):
        self.queue.put(json.loads(item['data']))

    def _run(self):
        for item in self.pubsub.listen():
            if item['type'] == 'message':
                self.work(item)

    def run(self):
        while True:
            try:
                self._run()
            except redis.ConnectionError:
                if self.force_stop:
                    #print >> sys.stderr, "stopping thread"
                    break
                self.pubsub.subscribe(self.channel)

# wait for the reply, it's simpler this way.
# 25 seconds timeout to avoir browser side timeout, typically 30 seconds.
def send_command(server_name, cmd, timeout = 25):
    if cmd.has_key('cmd') and cmd['cmd'] == 'ping':
        start = time.time()
    r = redis.Redis(host = 'tools-redis', socket_timeout = 1)
    new_val = r.incr(key_prefix + '_cmd_token')
    channel_name = key_prefix + '_cmd_reply_channel_' + str(new_val)
    try:
        cmd_redis = json.dumps( {'channel_name' : channel_name, 'cmd' : cmd} )
    except UnicodeDecodeError:
        return 1, json.dumps({ 'error' : 4, 'text' : 'Ill formed request' })
    queue = Queue.Queue()
    try:
        listener = channelListener(r, channel_name, queue)
        listener.start()
        public_channel = key_prefix + '_' + server_name
        # FIXME: this is not sufficient, as someone can listen but not the
        # server, see the comment about key_prefix.
        nr_subscribed = r.publish(public_channel, cmd_redis)
        if nr_subscribed:
            try:
                reply = queue.get(timeout = timeout)
            except Queue.Empty:
                reply = None
        else:
            reply = None
    finally:
        listener.force_stop = True

    if cmd.has_key('cmd') and cmd['cmd'] == 'ping':
        stop = time.time()
        if not reply:
            reply = { 'no reply from server' : server_name }

        reply.update( { 'ping' : stop-start, 'server' : server_name } )
        return nr_subscribed, json.dumps(reply)

    # We really don't want this, the socket_timeout is way too long
    #listener.join()
    #if listener.is_alive():
    #    time.sleep(0)
    #    if listener.is_alive():
    #        print "send_command: listener is alive"

    return nr_subscribed, reply

# FIXME: this is inneficient, we should get the queue from the caller and
# let the caller waiting on the queue.
def wait_for_request(server_name, timeout = 0.5):
    r = redis.Redis(host = 'tools-redis', socket_timeout = 0.25)
    public_channel = key_prefix + '_' + server_name
    queue = Queue.Queue()
    try:
        listener = channelListener(r, public_channel, queue)
        listener.start()
        try:
            time.sleep(0)
            cmd = queue.get(timeout = timeout)
        except Queue.Empty:
            cmd = None
    finally:
        listener.force_stop = True

    listener.join()

    if listener.is_alive():
        time.sleep(0)
        if listener.is_alive():
            print >> sys.stderr, "wait_for_request: request listener is alive"

    return cmd

def send_reply(in_request, reply):
    r = redis.Redis(host = 'tools-redis', socket_timeout = 1)
    r.publish(in_request['channel_name'], json.dumps(reply))

def test_client():
    while True:
        time.sleep(0)
        nr_subscribed, reply = send_command('simple_redis_ipc', 'A command')
        print >> sys.stderr, "client, reply from server:", reply

def test_server():
    while True:
        time.sleep(0)
        request = wait_for_request('simple_redis_ipc')
        print >> sys.stderr, "server, command from client:", request
        if request:
           send_reply(request, 'answer to ' + str(request))

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == '-client':
        test_client()
    elif len(sys.argv) == 2 and sys.argv[1] == '-server':
        test_server()
    else:
        print >> sys.stderr, '%s must run as with -client or -server command line option' % sys.argv[0]
