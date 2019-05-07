#!/usr/bin/python3.6
# This client is for training animals to eat from the feeder. 
# Sessions last 60 min
# Trials consist of: tray light goes turns on 
#					after 500ms, 4 pellets drop
#					after 5s tray light goes off
#					ITI: VI m=30s sd=2.5s
import asyncio
import random
import time
from whisker_conn import WhiskerConnector

port = 3233


class WhiskerClient:
	def __init__(self, loop, host, port):
		self.loop = loop
		self.host = host
		self.port = port
		self.main_conn = WhiskerConnector()
		self.imm_conn = None
		self.imm_port = None
		self.imm_code = None
		self.imm_conn_future = asyncio.Future()
		self.imm_reply_future = None
		self.screen_active = True
		self.expt_active = True
	
	@asyncio.coroutine
	def connect(self):
		self.main_conn.add_handler('*', self.handle_main_all)
		self.main_conn.add_handler('ImmPort:', self.handle_Imm)
		self.main_conn.add_handler('Code:', self.handle_Code)
		self.main_conn.add_handler('Event:', self.handle_Event)
		print("Connecting to Whisker Server at {}:{}".format(self.host, self.port))
		yield from self.main_conn.connect(self.loop, 'localhost', self.port)
		yield from self.imm_conn_future

	def handle_main_all(self, m):
		if m is None:
			self.loop.stop()
			print("Server disconnected. Exiting.")
		else:
			print("Main: '" + " ".join(m) + "'")
	
	def handle_reply(self, m):
		if m is not None:
			self.imm_reply_future.set_result(m)

	def handle_Imm(self, m):
		self.imm_port = int(m[1])

	@asyncio.coroutine
	def send_message(self, *m):
		if self.imm_reply_future is not None: yield from self.imm_reply_future
		self.imm_reply_future = asyncio.Future()
		print("Sent: '" + " ".join(m) + "'")
		self.imm_conn.send_message(m)
		result = yield from self.imm_reply_future
		self.imm_reply_future = None
		print("Reply: '" + " ".join(result) + "'")
		return result

	@asyncio.coroutine
	def handle_Code(self, m):
		self.imm_code = m[1]
		self.imm_conn = WhiskerConnector()
		self.imm_conn.add_handler('*', self.handle_reply)
		print(self.imm_port)
		yield from self.imm_conn.connect(self.loop, 'localhost', self.imm_port)
		yield from self.send_message('Link', self.imm_code)
		print("Connecting to immediate channel {}:{} with code {}".format(self.host, self.imm_port, self.imm_code))
		self.imm_conn_future.set_result(True)
#________________________________________________________________________________________________

	@asyncio.coroutine
	def handle_Event(self, m):
		message = m[1]
		if message == 'iti_end':
			print('ITI over')
			yield from self.feed(2)			
		
		elif message == 'iti_start':
			print('iti starting')
			yield from self.iti()
					
		elif message == 'end':
		#when experiment timer finished, end experiment
			self.expt_active = False
			self.screen_active = False
			yield from client.send_message('TimerClearAllEvents')
			yield from client.send_message('DisplayAddObject', 'document', 'done', 'text', '50', '50', 'All Done', '-textcolour', '255', '255', '255')
			print('experiment is over')
		pass

#________________________________________________________________________________________________
	@asyncio.coroutine
	def iti(self):
		iti = random.gauss(30, 2.5)
		while iti<20 or iti>40 :   
			iti = random.gauss(30, 2.5)
			pass
		print(int(iti))
		time.sleep(iti)
		yield from client.send_message('TimerSetEvent', '0', '0', 'iti_end')
#________________________________________________________________________________________________
	@asyncio.coroutine
	def feed(self, n):
		yield from client.send_message('LineSetState', 'TrayLight', 'on')
		time.sleep(1)
		for x in range(0,n):
			yield from client.send_message('LineSetState', 'PelletDispenser', 'on')
			time.sleep(0.5)
			yield from client.send_message('LineSetState', 'PelletDispenser', 'off')
			time.sleep(0.5)
			pass
		time.sleep(5)
		yield from client.send_message('LineSetState', 'TrayLight', 'off')
		yield from client.send_message('TimerSetEvent', '0', '0', 'iti_start')
#________________________________________________________________________________________________

	@asyncio.coroutine
	def start_Expt(self):
		#Start experiment timer
		yield from client.send_message('TimerSetEvent', '3600000', '0', 'end')
		print('I started the experiment')
		#send message to start iti
		yield from client.send_message('TimerSetEvent', '0', '0', 'iti_start')

#________________________________________________________________________________________________

event_loop = asyncio.get_event_loop()
client = WhiskerClient(event_loop, 'localhost', port)

@asyncio.coroutine
def run():
	#claim lines - houselight, tray light, pellet dispenser, white noise
	yield from client.send_message('LineClaim', '32', '-alias', 'HouseLight')
	yield from client.send_message('LineClaim', '33', '-alias', 'TrayLight')
	yield from client.send_message('LineClaim', '34', '-alias', 'PelletDispenser')
	yield from client.send_message('LineClaim', '35', '-alias', 'WhiteNoise')
	#Group feeder and tray
	yield from client.send_message('LineSetAlias', 'PelletDispenser', 'Feeder')
	yield from client.send_message('LineSetAlias', 'TrayLight', 'Feeder')
	#Initial states - House light on, traylight off, white noise on 
	yield from client.send_message('LineSetState', 'HouseLight', 'on')
	yield from client.send_message('LineSetState', 'Feeder', 'off')
	yield from client.send_message('LineSetState', 'WhiteNoise', 'off') #***TURN ON****
	#Set up display 
	yield from client.send_message('DisplayClaim', '0', '-alias', 'screen')
	yield from client.send_message('DisplayCreateDocument', 'document')
	yield from client.send_message('DisplayShowDocument', 'screen', 'document')
	#draw background/mask
	yield from client.send_message('DisplayAddObject', 'document', 'mask', 'rectangle', '10', '10', '758', '1014', '-brushsolid', '0', '0', '0')
	#start experiment
	yield from client.start_Expt()

event_loop.run_until_complete(client.connect())
print('here')
event_loop.run_until_complete(run())

try:
	event_loop.run_forever()
except KeyboardInterrupt as e:
	print(" Received Ctrl-C. Exiting.")


