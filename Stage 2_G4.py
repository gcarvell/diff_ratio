#!/usr/bin/python3.6
''' This client is for training animals to touch the orientation dot
# Sessions last 60 min
# Trials consist of: 
#					Crosshair displayed on screen
# 					When crosshair is touched, crosshair disappears, tray light goes turns on and 4 pellets drop
#					Otherwise, after 5s, crosshair disappears, tray light goes turns on and 2 pellets drop
#					after 5s tray light goes off
#					ITI: VI m=5s sd=5s
'''
import asyncio
import random
import time
import csv
from concurrent.futures import CancelledError
from whisker_conn import WhiskerConnector

port = 3233


class WhiskerClient:
	def __init__(self, loop, host, port):
		input('Press any key ')
		self.loop = loop
		self.host = host
		self.port = port
		self.main_conn = WhiskerConnector()
		self.imm_conn = None
		self.imm_port = None
		self.imm_code = None
		self.imm_conn_future = asyncio.Future()
		self.filename = self.get_filename()
		self.iti_active = False
		self.trial_active = False
		self.feeder_active = False
		self.data_frame = []
		self.awaiting = False
		self.count = 0
		self.num_touch = 0
		self.no_touch = 0
	
	def get_filename(self):
		timenow = time.localtime(time.time())
		order = [2,1,0,3,4]
		punctuation = ['-', '-', ' - ', '-', '']
		date = 'Stage 2 G4 '
		for i in range(len(order)):
			date += str(timenow[order[i]])
			date += punctuation[i]
		return(str(date))

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
		print(self.imm_port)
		yield from self.imm_conn.connect(self.loop, 'localhost', self.imm_port)
		self.send_message('Link', self.imm_code)
		print("Connecting to immediate channel {}:{} with code {}".format(self.host, self.imm_port, self.imm_code))
		self.imm_conn_future.set_result(True)
#________________________________________________________________________________________________

	@asyncio.coroutine
	def handle_Event(self, m):
		message = m[1]
		print(message)
		
		if message == 'TouchCircle' or message == 'TouchCircleEdge':
			print('Touched circle')
			self.trial_active = False
			self.no_touch = 0
			yield from self.show_circle(False)
			yield from self.feed(6)
		elif message == 'BGTouchDown':
			self.draw_cursor(m)
		elif message == 'DeleteCursor':
			self.send_message('DisplayDeleteObject', 'document', 'cursor')
		elif message == 'end':
		#when experiment timer finished, end experiment
			self.data_frame = ['Total: ', self.count, '\n', 'Touch: ', self.num_touch]
			self.log()
			print('Experiment is over')
			self.loop.stop()
		pass
#________________________________________________________________________________________________
	def log(self):
		with open('{}.csv'.format(self.filename), 'a+') as out_file:
			print('logging trial')
			if self.count == 1:
				out_file.write(str(self.filename) + '\n')
			timenow = time.localtime(time.time())
			out_file.write(str(timenow[3]) + str(timenow[4]) + str(timenow[5])+',')
			out_string = ', '.join(map(str, self.data_frame))
			out_file.write(out_string)
			out_file.write('\n')
			out_file.close()
			print(out_string)

#________________________________________________________________________________________________
	@asyncio.coroutine
	def trial(self):
		self.trial_active = True
		yield from self.show_circle(True)
		if self.no_touch<10:
			yield from asyncio.sleep(10)
			if self.trial_active:
				self.trial_active = False
				self.no_touch +=1
				yield from self.show_circle(False)
				print('Fixation circle hidden after 3 seconds')
				yield from self.feed(1)
		else:
			yield from asyncio.sleep(180)
			self.no_touch = 0
			if self.trial_active:
				self.trial_active = False
				yield from self.show_circle(False)
				print('No response after 60 seconds, Go to ITI')
				yield from self.iti()
#________________________________________________________________________________________________                       
	def draw_cursor(self, m):
		self.send_message('DisplayDeleteObject', 'document', 'cursor')
		self.send_message('TimerClearEvent', 'DeleteCursor')
		x = m[2]
		y = m[3]
		x1 = int(x) - 10
		y1 = int(y) - 10
		x2 = int(x) + 10
		y2 = int(y) + 10
		self.send_message('DisplayAddObject', 'document', 'cursor', 'ellipse', str(x1), str(y1), str(x2), str(y2), '-brushsolid', '255', '255', '0')
		self.send_message('TimerSetEvent', '1000', '0', 'DeleteCursor')
#________________________________________________________________________________________________
	
	@asyncio.coroutine
	def iti(self):
		self.iti_active = True
		self.count += 1
		if self.count>1:
			yield from self.show_circle(False)
			print('ITI in progress: ' + str(50))
			yield from asyncio.sleep(50)
		self.iti_active = False
		yield from self.trial()

#________________________________________________________________________________________________
	@asyncio.coroutine
	def feed(self, n):
		self.send_message('DisplayDeleteObject', 'document', 'cursor')
		self.feeder_active = True
		if n == 1:
			feed_type = 'auto'
			n=3
		else:
			feed_type = 'touch'
			self.num_touch += 1
		self.data_frame = [self.count,feed_type,self.num_touch]
		self.log()
		print('Feeder activated: ' + feed_type)
		self.send_message('LineSetState', 'TrayLight', 'on')
		for x in range(0,n):
			self.send_message('LineSetState', 'PelletDispenser', 'on')
			yield from asyncio.sleep(0.5)
			self.send_message('LineSetState', 'PelletDispenser', 'off')
			yield from asyncio.sleep(0.5)
		yield from asyncio.sleep(3)
		self.send_message('LineSetState', 'TrayLight', 'off')
		self.feeder_active = False
		print('Feeder off')
		yield from self.iti()
#________________________________________________________________________________________________
	@asyncio.coroutine
	def show_circle(self, show):
		if show:
			print('Displaying fixation circle')
			self.send_message('DisplayAddObject', 'document', 'TargetCircleEdge', 'ellipse', '164', '121', '584', '561', '-pencolour', '0', '0', '0', '-brushsolid', '0', '0', '0')
			self.send_message('DisplaySetEvent', 'document', 'TargetCircleEdge', 'TouchDown', 'TouchCircleEdge')
			self.send_message('DisplayAddObject', 'document', 'TargetCircle', 'ellipse', '324', '281', '444', '401')
			self.send_message('DisplaySetEvent', 'document', 'TargetCircle', 'TouchDown', 'TouchCircle')
		else:
			print('Removing fixation circle')
			self.send_message('DisplayDeleteObject', 'document', 'TargetCircle')
			self.send_message('DisplayDeleteObject', 'document', 'TargetCircleEdge')
#________________________________________________________________________________________________

	@asyncio.coroutine
	def start_Expt(self):
		#Start experiment timer
		self.send_message('TimerSetEvent', '3600000', '0', 'end')
		print('I started the experiment')
		#send message to start iti
		yield from self.iti()
#________________________________________________________________________________________________

event_loop = asyncio.get_event_loop()
client = WhiskerClient(event_loop, 'localhost', port)

@asyncio.coroutine
def run():
	#claim lines - houselight, tray light, pellet dispenser, white noise, tray input
	client.send_message('LineClaim', '56', '-alias', 'HouseLight')
	client.send_message('LineClaim', '57', '-alias', 'TrayLight')
	client.send_message('LineClaim', '58', '-alias', 'PelletDispenser')
	client.send_message('LineClaim', '59', '-alias', 'WhiteNoise')
	client.send_message('LineClaim', '24', '-alias', 'Tray')
	#Initial states - House light on, traylight off, white noise on 
	client.send_message('LineSetState', 'HouseLight', 'on')
	client.send_message('LineSetState', 'PelletDispenser', 'off')
	client.send_message('LineSetState', 'TrayLight', 'off')
	client.send_message('LineSetState', 'WhiteNoise', 'off') #***TURN ON?****
	#Set up display 
	client.send_message('DisplayClaim', '3', '-alias', 'screen')
	client.send_message('DisplayCreateDocument', 'document')
	client.send_message('DisplayShowDocument', 'screen', 'document')
	#draw background
	client.send_message('DisplaySetBackgroundColour', 'document', '0', '0', '0')
	#draw crosshairs
	#Timestamps and event co-ordinates displayed
	client.send_message('TimeStamps', 'on')
	client.send_message('DisplayEventCoords', 'on')
	#Add touch handlers
	client.send_message('DisplaySetBackgroundEvent', 'document', 'TouchDown', 'BGTouchDown')
	#start experiment
	yield from client.start_Expt()

event_loop.run_until_complete(client.connect())
print('here')
event_loop.run_until_complete(run())

try:
	event_loop.run_forever()
except KeyboardInterrupt as e:
	print(" Received Ctrl-C. Exiting.")



