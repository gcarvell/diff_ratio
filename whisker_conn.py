#!/usr/bin/python3

import asyncio
import traceback

class WhiskerConnector:
    """ A client/server for the Whisker protocol.

    Clients and servers are pretty similar:

    # define some handlers
    def handle_all(message): print(message)
    def handle_Event(message): print('got an event message', message)

    # create connector and bind handlers
    conn = WhiskerConnector()
    conn.add_handler('*', handle_all)
    conn.add_handler('Event', handle_Event)

    # create our event loop
    event_loop = asyncio.get_event_loop()

    # connect
    conn.connect(event_loop, 'localhost', 3323)

    # wait for a Ctrl-C
    try:
        event_loop.run_forever()
    except KeyboardException:
        print('Received Ctrl-C. Exiting')
    """
    def __init__(self):
        self._protocol = WhiskerProtocol(self._recv_message)
        self._handlers = []

    @asyncio.coroutine
    def connect(self, loop, host, port=3233):
        yield from loop.create_connection(lambda: self._protocol, host, port)

    def add_handler(self, name, handler): self._handlers.append((name, handler))

    def send_message(self, message): self._protocol.send_message(message)
    
    def _recv_message(self, message): asyncio.ensure_future(self._recv_message_async(message))

    @asyncio.coroutine
    def _recv_message_async(self, message):
        for handler in self._handlers:
            if handler[0] == '*' or (message is not None and handler[0] == message[0]):
                try:
                    result = handler[1](message)
                    if asyncio.iscoroutine(result): yield from result
                except Exception:
                    traceback.print_exc()

class WhiskerProtocol(asyncio.Protocol):
    def __init__(self, recv_message=lambda m: None, on_connect=lambda t: None):
        self.recv_message = recv_message
        self.on_connect = on_connect
        self.transport = None
        self.send_buf = []
        self.ended = False
        self.framing = WhiskerFraming(self._handle_message)

    def send_message(self, message):
        if self.transport is None:
            self.send_buf.append(message)
        else:
            self.transport.write(self.framing.from_message(message))

    def connection_made(self, transport):
        self.transport = transport
        for m in self.send_buf:
            self.send_message(m)
        self.on_connect(transport)

    def data_received(self, data): self.framing.on_data(data)
    def eof_received(self): self._end()
    def connection_lost(self, arg): self._end()

    def _end(self):
        if self.ended: return
        self.ended = True
        self.framing.on_data(b'')
        self._handle_message(None)
    
    def _handle_message(self, message):
        self.recv_message(message)
        

class WhiskerFraming:
    def __init__(self, message_cb=lambda m: None):
        self.message_cb = message_cb
        self.output_buf = []
        self.cur_message = []
        self.cur_param = ''
        self.prev_c = ''
        self.in_quote = False
    
    def from_message(self, message):
        buf = ''
        first = True
        for m in message:
            if not first: buf += ' '
            first = False
            if any(c in m for c in ';\n\r '):
                m = '"' + m + '"'
            buf += m
        return bytes(buf + '\n', 'utf-8')

    def on_data(self, data_bin=b''):
        data = str(data_bin, 'utf-8')
        self.output_buf = []
        if len(data):
            for c in data:
                if not self.in_quote and c in ';\n\r':
                    self._end_param()
                    self._end_message()
                elif not self.in_quote and c == ' ':
                    self._end_param()
                elif c == '"':
                    self.in_quote = not self.in_quote
                else:
                    self.cur_param += c
                self.prev_c = c
        else:
            self._end_param()
            self._end_message()

        return self.output_buf

    def _end_param(self):
        if self.prev_c == ' ': return
        self.cur_message.append(self.cur_param)
        self.cur_param = ''

    def _end_message(self):
        if self.cur_message == [] or self.cur_message == ['']: return
        self.message_cb(self.cur_message)
        self.output_buf.append(self.cur_message)
        self.cur_message = []
