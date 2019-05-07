
#!/usr/bin/python3
from session import * 
from experiment import *
from whisker_client import *
import asyncio

s = Session()
e = Experiment(s)
event_loop = asyncio.get_event_loop()
c = WhiskerClient(event_loop, 'localhost', port, e)
print(s.filename)

event_loop.run_until_complete(c.connect())
print('Client connected')
event_loop.run_until_complete(c.setup(s.subject))
print('Setup complete')
event_loop.run_until_complete(e.run(c))

try:
    event_loop.run_forever()
except KeyboardInterrupt:
    print(" Received Ctrl-C. Exiting.")
