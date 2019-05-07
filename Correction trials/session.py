#!/usr/bin/python3
import numpy as np
import csv
import time

class Session:
	def __init__(self):
		self.subject = int(input("Subject: "))
		self.iti = int(input("ITI: "))
		self.pairs = get_pairs()
		self.locations = get_locations()
		self.order = np.random.permutation(np.arange(100))
		self.angles = [(90,90) for x in range(100)]#np.array([(np.random.randint(179),np.random.randint(179)) for i in range(100)]).astype("int")
		self.filename = self.get_filename()

	def get_filename(self):
		timenow = time.localtime(time.time())
		order = [2,1,0,3,4]
		punctuation = ['-', '-', ' ', '-', '']
		date = 'Dif G{} '.format(self.subject)
		for i in range(len(order)):
			date += str(timenow[order[i]])
			date += punctuation[i]
		return(str(date))

def get_coords(side,length, angle):
	if side == 0:
		x1 = 192
	elif side == 1:
		x1 = 576
	else:
		print('Error setting origin')
	x2 = x1
	y0 = (length/2)
	y1 = int(round(192 - y0, 0))
	y2 = int(round(192 + y0, 0))

	'''opp = (length/2)*(np.sin((np.radians(90-angle))))
	adj = np.sqrt((length/2)**2 - opp**2)
	if side == 0:
		x0 = 192
	elif side == 1:
		x0 = 576
	else:
		print('Error setting origin')
	y0 = 192
	x1 = int(round(x0 - opp, 0))
	x2 = int(round(x0 + opp, 0))
	y1 = int(round(y0 - adj, 0))
	y2 = int(round(y0 + adj, 0))'''
	coords = [x1, y1, x2, y2]
	return coords

def get_pairs():
	reader = csv.reader(open("pairs1.csv", "rt"), delimiter=",")
	x = list(reader)
	pairs = np.array([(row[0],row[1]) for row in x]).astype("int")
	return pairs

def get_locations():
	reader = csv.reader(open("pairs1.csv", "rt"), delimiter=",")
	x = list(reader)
	location = np.array([row[2] for row in x]).astype("float")
	return location

