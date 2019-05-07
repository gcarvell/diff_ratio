''' STATES:
0.iti - ITI in progress
1.fix - Fixation circle is being displayed
2.stim - Stimulus is being displayed in NORMAL trial
3.stim.corr - Stimulus is being displayed in CORRECTION trial
4.black.bg - Blackout after a touch to the background during trial
5.feed - Feeder is active after NORMAL trial
6.feed.corr - Feeder is active after CORRECTION trial
7.feedback - Green feedback is being displayed after correct response
8.black.corr - Blackout after an incorrect response on the response bar
9.feedback.corr - Red feedback is being displayed after an incorrect response
10.feedback.after.corr - Green feedback is being displayed after correct response in CORRECTION trial
11.feedback.after.corr.incorrect - Red feedback is being displayed after an incorrect response in CORRECTION trial
12. black.bg.corr - Blackout after a touch to the background during CORRECTION trial
DATA:

0'Trial', 'Fix time', 'Stim time', Order', 'Left length', 'Right length', 'Left angle', 'Right angle', 'Correct location', 
'Response time' 'Response location', 'Correction trial?', 'Reinforcer'

'''
import asyncio
from whisker_client import *
import numpy as np
import time

class Experiment():
    def __init__(self, session):
        self.states = ['iti','fix','stim','stim.corr','black.bg','feed','feed.corr','feedback','black.corr','feedback.corr','feedback.after.corr', 'feedback.after.corr.incorrect', 'black.bg.corr']
        self.state = self.states[0]
        self.trial = 0
        self.session = session
        self.headers = ['Trial', 'Fix time', 'Stim time', 'Order', 'Left length', 'Right length', 'Left angle', 'Right angle', 'Correct location', 'Correction trial', 'Response location', 'Response time', 'Correct response?', 'Reinforcer']
        self.data = []
        self.first = True
        self.bgtouch = False
        self.index = 0
        self.consecutive = 0

    @asyncio.coroutine
    def run(self,client):
        self.client = client
        self.log(self.headers)
        yield from asyncio.sleep(2)
        yield from self.iti()
    
    def log(self, data):
        with open('{}.csv'.format(self.session.filename), 'a+') as out_file:
            out_string = ','.join(map(str, data))
            out_file.write(out_string)
            print(out_string)
            out_file.write('\n')
            out_file.close()
        self.data = []

    def get_time(self):
        timenow = time.localtime(time.time())
        timestamp = '{}:{}:{}'.format(timenow[3], timenow[4], timenow[5])
        return timestamp

    @asyncio.coroutine
    def events(self,message):
        if isinstance(message,list):
            m = message[1]
        else:
            m = message

        if m == 'end':
            print("end trial")
        elif self.state == 'iti':
            if m == 'timer.iti':
                self.state = self.states[1]
                print('Transition: iti -> fix')
                yield from self.fix()
            elif m == 'touch.bg':
                pass
            else:
                print('Error: iti -> fix')
                print('Message was: ' + m)
        elif self.state == 'fix':
            if m == 'touch.fix' or m == 'touch.fixedge':
                self.hideFix()
                self.state = self.states[2]
                print('Transition: fix -> stim')
                yield from self.stim()
            elif m=='touch.bg':
                pass
            else:
                print('Error: fix -> stim')
        elif self.state == 'stim':
            if m == 'touch' or m =='touch.in':
                print('check location')
                print(message[2])
                print(self.session.locations[self.index])
                correct = self.check(message[2])
                print(correct)
                if correct:
                    self.state = self.states[7]
                    print('Transition: stim -> feedback')
                    yield from self.feedback()
                if not correct:
                    print('go to correction trial')
                    self.state = self.states[9]
                    print('Transition: stim -> feedback.corr')
                    yield from self.feedback()
            elif m == 'touch.bg':
                self.bgtouch = True
                self.state = self.states[4]
                print('Transition: stim -> black.bg')
                yield from self.black()
            else:
                print('Error: stim -> ?')
        elif self.state == 'stim.corr':
            if m =='touch' or m == 'touch.in' or m == 'touch.fb':
                correct = self.check(message[2])
                if correct:
                    self.state = self.states[10]
                    print('Transition: stim.corr -> feedback.after.corr')
                    yield from self.feedback()
                else:
                    self.state = self.states[11]
                    print('Transition: stim.corr -> feedback.after.corr.incorrect')
                    yield from self.feedback()
            elif m == 'touch.bg':
                self.bgtouch = True
                self.state = self.states[12]
                print('Transition: stim -> black.bg.corr')
                yield from self.black()
            else:
                print('Error: stim.corr -> ?')
        elif self.state == 'black.bg':
            if m == 'timer.bg':
                self.state = self.states[2]
                print('Transition: black.bg -> stim')
                yield from self.stim()
            else:
                print('Error: black.bg -> stim')
        elif self.state == 'black.bg.corr':
            if m == 'timer.bg.corr':
                self.state = self.states[3]
                print('Transition: black.bg.corr -> stim.corr')
                yield from self.stim()
            else:
                print('Error: black.bg.corr -> stim.corr')
        elif self.state == 'black.corr':
            if m == 'timer.corr':
                self.state = self.states[3]
                print('Transition: black.corr -> stim.corr')
                yield from self.stim()
            else:
                print('Error: black.corr -> stim.corr')
        elif self.state == 'feedback':
            if m == 'timer.feedback':
                self.state = self.states[5]
                print('Transition: feedback -> feed')
                yield from self.feed(4)
            else:
                print('Error: feedback -> feed')
        elif self.state == 'feedback.after.corr':
            if m == 'timer.feedback':
                self.state = self.states[6]
                print('Transition: feedback.after.corr -> feed.corr')
                yield from self.feed(1)
            else:
                print('Error: feedback.after.corr -> feed.corr')
        elif self.state == 'feedback.corr':
            if m == 'timer.feedback.corr':
                self.state = self.states[8]
                print('Transition: feedback.corr -> black.corr')
                yield from self.black()              
            #else:
                #print('Error: feedback.corr -> feed.corr')
        elif self.state == 'feed' or self.state == 'feed.corr' or self.state == 'feedback.after.corr.incorrect':
            if m == 'timer.feedback.corr':
                print('Transition: feedback.after.corr.incorrect -> iti')
            elif m == 'trial.over':
                print('Transition: feed -> iti')
            if m == 'timer.feedback.corr' or m == 'trial.over':
                self.state = self.states[0]
                print('Logging trial')
                self.log(self.data)
                print(self.data)
                yield from self.iti()
        else:
            print('Error: bad state - {}'.format(self.state))
            print('Error: message was - {}'.format(m))

    @asyncio.coroutine
    def iti(self):
        if self.trial >99:
            yield from self.events('end')
        else:
            if self.first:
                self.first = False
            else:
                self.trial += 1
            print('\nITI {}s'.format(self.session.iti))
            yield from asyncio.sleep(self.session.iti)
            print('\nTrial: '+str(self.trial))
            self.data.append(self.trial)
            print(self.data)
            yield from self.events('timer.iti')

    @asyncio.coroutine
    def fix(self):
        print('Drawing fixation circle')
        self.data.append(self.get_time())
        print(self.data)
        self.client.send_message('DisplayAddObject', 'doc', 'fixedge', 'ellipse', '334', '291', '434', '391', '-pencolour', '0','0','0','-brushsolid', '0','0','0')
        self.client.send_message('DisplaySetEvent', 'doc', 'fixedge', 'TouchDown', 'touch.fixedge')
        self.client.send_message('DisplayAddObject', 'doc', 'fix', 'ellipse', '354', '311', '414', '371')
        self.client.send_message('DisplaySetEvent', 'doc', 'fix', 'TouchDown', 'touch.fix')
    
    def hideFix(self):
        self.client.send_message('DisplayDeleteObject', 'doc', 'fix')
        self.client.send_message('DisplayDeleteObject', 'doc', 'fixedge')

    @asyncio.coroutine
    def stim(self):
        i=self.index
        if not self.bgtouch:
            info = [self.get_time(), i, self.session.pairs[i][0], self.session.pairs[i][1], self.session.angles[self.trial][0], self.session.angles[self.trial][1], self.session.locations[i], 'False']
            if self.state == 'stim':
                print(self.data) 
                self.data.extend(info)
                print(self.data)
            elif self.state == 'stim.corr':
                self.data.append('0')
                fixtime = self.data[1]
                self.log(self.data)
                self.data = [self.trial,fixtime]
                print(self.data)
                info = [self.get_time(), i, self.session.pairs[i][0], self.session.pairs[i][1], self.session.angles[self.trial][0], self.session.angles[self.trial][1], self.session.locations[i], 'True']
                self.data.extend(info)
                print(self.data)
            else:
                print('Error: Problem recording data')
        self.bgtouch = False
        left = self.get_coords('l', self.session.pairs[i][0], self.session.angles[self.trial][0])
        right = self.get_coords('r', self.session.pairs[i][1], self.session.angles[self.trial][1])
        print('left:{}\nlength: {}\nangle:{}'.format(left, self.session.pairs[i][0],self.session.angles[self.trial][0]))
        print('lright: {}\nlength: {}\nangle:{}'.format(right, self.session.pairs[i][1],self.session.angles[self.trial][1]))
        self.client.send_message('DisplayAddObject', 'doc', 'left', 'line', str(left[0]), str(left[1]), str(left[2]), str(left[3]), '-penwidth', '7')
        self.client.send_message('DisplayAddObject', 'doc', 'right', 'line', str(right[0]), str(right[1]), str(right[2]), str(right[3]), '-penwidth', '7')
        print('diplay lines until touch')
        yield from asyncio.sleep(2)
        print('display response bar')
        self.client.send_message('DisplayAddObject', 'doc', 'bar', 'rectangle', '68', '637', '700', '737', '-pencolour', '0', '0', '0', '-brushsolid', '0', '0', '0')#black, can be responded to
        self.client.send_message('DisplayAddObject', 'doc', 'bar.overlay', 'rectangle', '68', '667', '700', '707', '-pencolour', '150', '150', '150', '-brushsolid', '150', '150', '150')#white and transparent
        self.client.send_message('DisplaySetEvent', 'doc', 'bar.overlay', 'TouchDown', 'touch.in')
        self.client.send_message('DisplaySetEvent', 'doc', 'bar', 'TouchDown', 'touch')
        if self.session.locations[i]>0.2 and self.session.locations[i]<0.8:
            print('Display circle at correct location')
            loc=int(632*float(self.session.locations[i])+68)
            self.client.send_message('DisplayAddObject', 'doc', 'indicator', 'ellipse', str(loc-30), '657', str(loc+30), '717', '-brushsolid', '225', '225', '225')
            yield from asyncio.sleep(1)
            self.client.send_message('DisplayDeleteObject', 'doc', 'indicator')
        if self.state == 'stim.corr':
            print('Display circle at correct location')
            loc=int(632*float(self.session.locations[i])+68)
            self.client.send_message('DisplayAddObject', 'doc', 'feedback', 'ellipse', str(loc-30), '657', str(loc+30), '717', '-brushsolid', '225', '225', '225')
            self.client.send_message('DisplaySetEvent', 'doc', 'feedback', 'TouchDown', 'touch.fb')

    def check(self, loc):
        x = (int(loc)-68)/632
        self.data.append(x)
        print(self.data)
        i=self.index
        xmin = self.session.locations[i]-0.15
        xmax = self.session.locations[i]+0.15
        return xmin <= x <= xmax

    def get_coords(self,side,length, angle):
        opp = (length/2)*(np.sin((np.radians(90-angle))))
        adj = np.sqrt((length/2)**2 - opp**2)
        if side == 'l':
            x0 = 192
        elif side == 'r':
            x0 = 576
        else:
            print('Error setting origin')
        y0 = 192
        x1 = int(round(x0 - opp, 0))
        x2 = int(round(x0 + opp, 0))
        y1 = int(round(y0 - adj, 0))
        y2 = int(round(y0 + adj, 0))
        coords = [x1, y1, x2, y2]
        return coords

    @asyncio.coroutine
    def black(self):
        self.client.send_message('DisplayAddObject', 'doc', 'black', 'rectangle', '0', '0', '768', '1024', '-brushsolid', '0', '0', '0')
        self.client.send_message('LineSetState', self.client.houselight, 'off')
        if self.state == 'black.bg':
            print('Blackout for 1s after touch to background')
            yield from asyncio.sleep(1)
            self.client.send_message('DisplayDeleteObject', 'doc', 'black')
            self.client.send_message('LineSetState', self.client.houselight, 'on')
            yield from self.events('timer.bg')
        if self.state == 'black.bg.corr':
            print('Blackout for 1s after touch to background')
            yield from asyncio.sleep(1)
            self.client.send_message('DisplayDeleteObject', 'doc', 'black')
            self.client.send_message('LineSetState', self.client.houselight, 'on')
            yield from self.events('timer.bg.corr')
        elif self.state == 'black.corr':
            print('Blackout for 2s after incorrect response')
            yield from asyncio.sleep(2) 
            self.client.send_message('DisplayDeleteObject', 'doc', 'black')
            self.client.send_message('LineSetState', self.client.houselight, 'on')
            yield from self.events('timer.corr')         
        pass

    @asyncio.coroutine
    def feedback(self):
        self.data.append(self.get_time())#response time
        loc=int(632*float(self.session.locations[self.index])+68)
        if self.state == 'feedback' or self.state =='feedback.after.corr':
            if self.state == 'feedback':
                self.consecutive +=1
                if self.consecutive ==3:
                    self.index +=1
                    if self.index == 20:
                        self.index = 0
            else:
                self.consecutive = 0
            self.data.append('True')
            print(self.data)
            print('show green circle at correct location')
            self.client.send_message('DisplayAddObject', 'doc', 'feedback', 'ellipse', str(loc-30), '657', str(loc+30), '717', '-brushsolid', '0', '190', '0')
            print('Display feedback for 2s')
            yield from asyncio.sleep(2)
            self.hideStim()
            yield from self.events('timer.feedback')
        elif self.state == 'feedback.corr' or self.state =='feedback.after.corr.incorrect':
            self.consecutive = 0
            self.data.append('False')
            if self.state =='feedback.after.corr.incorrect':
                self.data.append('0')
            print(self.data)
            print('show red circle at correct location')
            self.client.send_message('DisplayAddObject', 'doc', 'feedback', 'ellipse', str(loc-30), '657', str(loc+30), '717', '-brushsolid', '190', '0', '0')
            print('Display feedback for 2s')
            yield from asyncio.sleep(2)
            self.hideStim()
            print('timer message: timer.feedback.corr')
            yield from self.events('timer.feedback.corr')
        else:
            print('Error')

    def hideStim(self):
        self.client.send_message('DisplayDeleteObject', 'doc', 'left')
        self.client.send_message('DisplayDeleteObject', 'doc', 'right')
        self.client.send_message('DisplayDeleteObject', 'doc', 'bar')
        self.client.send_message('DisplayDeleteObject', 'doc', 'bar.overlay')
        self.client.send_message('DisplayDeleteObject', 'doc', 'feedback')

    @asyncio.coroutine
    def feed(self, n):
        if self.state == 'feed' or self.state == 'feed.corr':
            self.data.append(n)
            self.client.send_message('LineSetState', self.client.traylight, 'on')
            '''for x in range(0,n):
                self.client.send_message('LineSetState', self.client.food, 'on')
                yield from asyncio.sleep(0.5)
                self.client.send_message('LineSetState', self.client.food, 'off')
                yield from asyncio.sleep(0.5)
            yield from asyncio.sleep(4)'''
            self.client.send_message('LineSetState', self.client.traylight, 'off')
        else:
              print('Error bad state for feed')
        yield from self.events('trial.over')
