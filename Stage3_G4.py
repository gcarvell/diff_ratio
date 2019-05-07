

#!/usr/bin/python3.6
''' #Stage 3
This client is for training animals to peck the response bar after pecking the fixation circle. 
Sessions last 60 min
Trials consist of: 
	ITI: VI m=20s sd=4s
	Fixation circle displayed on screen
	Fixation circle must be touched to progress.
	After touch, fixation circle is removed from screen, and response bar is displayed.
	If response bar is touched, it disappears and large reinforcement (4 pellets) is given
	Otherwise, response bar is displayed for 5s, then disappears and small reinforcement (1 pellet) is given.
	Pellet tray light is illuminated for 5s following food delivery.
				
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
		date = 'Stage 3 G4 '
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
			self.trial_active = True
			yield from self.show_circle(False)
			yield from self.show_bar(True)
			yield from self.bar_wait()
		elif message == 'TouchMarker':
			print('Touched marker')
			self.trial_active = False
			self.no_touch = 0
			yield from self.show_bar(False)
			yield from self.feed(6)
		elif message == 'TouchBar' or message =='TouchBarEdge':
			self.show_response_marker(False)
		elif message == 'BGTouchDown':
			if self.trial_active:
				yield from self.blackout()
			else:
				self.draw_cursor(m)
		elif message == 'DeleteCursor':
			self.send_message('DisplayDeleteObject', 'document', 'cursor')
		elif message == 'end':
		#when experiment timer finished, end experiment
			self.log(['Total: ', self.count, '\n', 'Touch: ', self.num_touch])
			self.send_message('TimerClearAllEvents')
			self.send_message('DisplayRelinquishAll')
			self.send_message('LineRelinquishAll')
			print('Experiment is over')
			self.loop.stop()
		pass

#________________________________________________________________________________________________
	def log(self, data_frame):
		print('Logging trial')
		with open('{}.csv'.format(self.filename), 'a+') as out_file:
			if self.count == 1:
				out_file.write(str(self.filename) + '\n')
			timenow = time.localtime(time.time())
			out_file.write(str(timenow[3]) + str(timenow[4]) + str(timenow[5])+',')
			out_string = ', '.join(map(str, data_frame))
			out_file.write(out_string)
			out_file.write('\n')
			out_file.close()
#________________________________________________________________________________________________
	@asyncio.coroutine
	def trial(self):
		self.trial_active = True
		yield from self.show_circle(True)

#________________________________________________________________________________________________
	@asyncio.coroutine
	def blackout(self):
		self.send_message('DisplayAddObject', 'document', 'black', 'rectangle', '0', '0', '768', '1024', '-brushsolid', '0', '0', '0')
		self.send_message('LineSetState', 'HouseLight', 'off')
		print('Blackout for 1s after touch to background')
		yield from asyncio.sleep(1)
		self.send_message('DisplayDeleteObject', 'document', 'black')
		self.send_message('LineSetState', 'HouseLight', 'on')
#________________________________________________________________________________________________
	@asyncio.coroutine
	def bar_wait(self):
		if self.no_touch<10:
			yield from asyncio.sleep(10)
			timer = 5
		else:
			yield from asyncio.sleep(60)
			timer = 60
		if self.trial_active:
			self.trial_active = False
			self.no_touch +=1
			yield from self.show_bar(False)
			print('Response bar hidden after ' + str(timer) + ' seconds')
			yield from self.feed(1)
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
		elif n==2:
			feed_type = 'bar'
		else:
			feed_type = 'touch'
			self.num_touch += 1
		self.log([self.count,feed_type,self.num_touch])
		print('Trial {}\nFeeder activated: {}'.format(self.count,feed_type))
		self.send_message('LineSetState', 'TrayLight', 'on')
		for x in range(0,n):
			self.send_message('LineSetState', 'PelletDispenser', 'on')
			yield from asyncio.sleep(0.5)
			self.send_message('LineSetState', 'PelletDispenser', 'off')
			yield from asyncio.sleep(0.5)
		yield from asyncio.sleep(4)
		self.send_message('LineSetState', 'TrayLight', 'off')
		self.feeder_active = False
		print('Feeder off')
		yield from self.iti()
#________________________________________________________________________________________________
	@asyncio.coroutine
	def show_circle(self, show):
		if show:
			print('Drawing fixation circle')
			self.send_message('DisplayAddObject', 'document', 'TargetCircleEdge', 'ellipse', '264', '221', '484', '461', '-pencolour', '0', '0', '0', '-brushsolid', '0', '0', '0')
			self.send_message('DisplaySetEvent', 'document', 'TargetCircleEdge', 'TouchDown', 'TouchCircleEdge')
			self.send_message('DisplayAddObject', 'document', 'TargetCircle', 'ellipse', '344', '301', '424', '381')
			self.send_message('DisplaySetEvent', 'document', 'TargetCircle', 'TouchDown', 'TouchCircle')
			print('Waiting for peck')
		else:
			print('Removing fixation circle')
			self.send_message('DisplayDeleteObject', 'document', 'TargetCircleEdge')
			self.send_message('DisplayDeleteObject', 'document', 'TargetCircle')


#________________________________________________________________________________________________
	@asyncio.coroutine
	def show_bar(self, show):
		if show:
			print('Drawing response bar')
			self.trial_active = True
			self.send_message('DisplayAddObject', 'document', 'ResponseBarEdge', 'rectangle', '68', '637', '700', '737', '-pencolour', '0', '0', '0', '-brushsolid', '0', '0', '0')#black, can be responded to
			self.send_message('DisplayAddObject', 'document', 'ResponseBarOverlay', 'rectangle', '68', '667', '700', '707', '-pencolour', '150', '150', '150', '-brushsolid', '150', '150', '150')#white and transparent
			self.send_message('DisplaySetEvent', 'document', 'ResponseBarEdge', 'TouchDown', 'TouchBarEdge')
			self.send_message('DisplaySetEvent', 'document', 'ResponseBarOverlay', 'TouchDown', 'TouchBar')
			self.show_response_marker(True)
			print ('Waiting for 5 seconds (or peck)')
		else:
			print('Removing response bar')
			self.send_message('DisplayDeleteObject', 'document', 'ResponseBarEdge')
			self.send_message('DisplayDeleteObject', 'document', 'ResponseBarOverlay')
			self.send_message('DisplayDeleteObject', 'document', 'ResponseMarker')
#________________________________________________________________________________________________
	def show_response_marker(self, first):
		y1=647
		y2=727
		x1=[133,239,344,449,555]
		x2=[213,319,424,529,635]
		if first:
			self.loc = random.randint(0,4)
			self.send_message('DisplayAddObject', 'document', 'ResponseMarker', 'ellipse', str(x1[self.loc]), str(y1), str(x2[self.loc]), str(y2), '-brushsolid', '255', '255', '255')
		else:
			self.send_message('DisplayAddObject', 'document', 'ResponseMarker', 'ellipse', str(x1[self.loc]), str(y1), str(x2[self.loc]), str(y2), '-brushsolid', '0', '200', '0')
		print('drawing response marker at' + str(self.loc))
		self.send_message('DisplaySetEvent', 'document', 'ResponseMarker', 'TouchDown', 'TouchMarker')
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
	client.send_message('DisplayRelinquishAll')
	client.send_message('LineRelinquishAll')
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
	#Timestamps and event co-ordinates displayed
	client.send_message('TimeStamps', 'on')
	client.send_message('DisplayEventCoords', 'on')
	#Add touch handlers
	client.send_message('DisplaySetEvent', 'document', 'TargetCircle', 'TouchDown', 'TouchCircle')
	client.send_message('DisplaySetBackgroundEvent', 'document', 'TouchDown', 'BGTouchDown')
	client.send_message('DisplaySetBackgroundEvent', 'document', 'TouchUp', 'BGTouchUp')
	#start experiment
	yield from client.start_Expt()

event_loop.run_until_complete(client.connect())
print('here')
event_loop.run_until_complete(run())

try:
	event_loop.run_forever()
except KeyboardInterrupt as e:
	print(" Received Ctrl-C. Exiting.")



