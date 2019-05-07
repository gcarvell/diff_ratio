#!/usr/bin/python3

import asyncio
import time
from whisker_conn import WhiskerConnector
from concurrent.futures import CancelledError

port = 3233


class WhiskerClient:
	def __init__(self, loop, host, port, experiment):
		self.loop = loop
		self.host = host
		self.port = port
		self.main_conn = WhiskerConnector()
		self.imm_conn = None
		self.imm_port = None
		self.imm_code = None
		self.imm_conn_future = asyncio.Future()
		self.imm_reply_future = None
		self.experiment = experiment
	
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
		pass
		# print(', '.join(m))

	def handle_Imm(self, m):
		self.imm_port = int(m[1])

	def send_message(self, *m):
		# print("Sent: '" + " ".join(m) + "'")
		self.imm_conn.send_message(m)

	@asyncio.coroutine
	def handle_Code(self, m):
		self.imm_code = m[1]
		self.imm_conn = WhiskerConnector()
		self.imm_conn.add_handler('*', self.handle_reply)
		yield from self.imm_conn.connect(self.loop, 'localhost', self.imm_port)
		self.send_message('Link', self.imm_code)
		print("Connecting to immediate channel {}:{} with code {}".format(self.host, self.imm_port, self.imm_code))
		self.imm_conn_future.set_result(True)
#________________________________________________________________________________________________    @asyncio.coroutine
	def handle_Event(self, m):
		yield from self.experiment.events(m)

#________________________________________________________________________________________________    
	@asyncio.coroutine
	def setup(self,subject):
		print('Setup for subject: G'+ str(subject))
		if subject == 1 or subject == 5:
			self.houselight = '32'
			self.traylight = '33'
			self.food = '34'
			self.noise = '35'
			self.traysensor = '0'
			self.display = '0'
		elif subject == 2 or subject == 6:
			self.houselight = '40'
			self.traylight = '41'
			self.food = '42'
			self.noise = '43'
			self.traysensor = '8'
			self.display = '1'
		elif subject == 3 or subject == 7:
			self.houselight = '48'
			self.traylight = '49'
			self.food = '50'
			self.noise = '51'
			self.traysensor = '16'
			self.display = '2'
		elif subject == 4 or subject == 8:
			self.houselight = '56'
			self.traylight = '57'
			self.food = '58'
			self.noise = '59'
			self.traysensor = '24'
			self.display = '3'
		else:
			print('Incorrect subject')
			self.experiment.touchHandler('end')
		self.send_message('LineClaim', self.houselight)
		self.send_message('LineClaim', self.food)
		self.send_message('LineClaim', self.traylight)
		self.send_message('LineClaim', self.noise)
		self.send_message('LineClaim', self.traysensor)
		self.send_message('LineSetState', self.houselight, 'on')
		self.send_message('LineSetState', self.traylight, 'off')
		self.send_message('LineSetState', self.noise, 'off')
		#Display
		self.send_message('DisplayClaim', self.display)
		self.send_message('DisplayCreateDocument', 'doc')
		self.send_message('DisplayShowDocument', self.display, 'doc')
		self.send_message('DisplaySetBackgroundColour', 'doc', '0', '0', '0')
		#Timestamps and event co-ordinates
		self.send_message('TimeStamps', 'on')
		self.send_message('DisplayEventCoords', 'on')
		#Touch handlers
		self.send_message('DisplaySetBackgroundEvent', 'doc', 'TouchDown', 'touch.bg')
#________________________________________________________________________________________________

