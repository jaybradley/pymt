'''
Touch and hold: search for a held touch
'''

__all__ = ('InputPostprocTouchAndHold', )

from pymt.vector import Vector
from pymt.utils import curry
from pymt.clock import getClock

class InputPostprocTouchAndHold(object):
    def __init__(self):
        #print "InputPostprocTouchAndHold constructed"
        self.hold_distance = 10 # distance is in pixels
        self.hold_time = 1.2
        self.touches = {}
        self.queue = []

    def _timeout(self, touch, *largs):
        #print "InputPostprocTouchAndHold::_timeout"
        distance = Vector(touch.opos).distance(touch.pos)
        #print "distance", distance, "self.hold_distance", self.hold_distance, "touch.opos", touch.opos, "touch.pos", touch.pos
        if distance > self.hold_distance:
            #print "Distance for touch and hold is too great"
            return
        #print "Touch is held"
        touch.is_held = True
        self.queue.append(('move', touch))
        
    def process(self, events):
        #print "InputPostprocTouchAndHold::process"
        if len(self.queue):
            events = self.queue + events
            self.queue = []

        schedule = getClock().schedule_once
        unschedule = getClock().unschedule
        for type, touch in events:
            if type == 'down':
                touch.userdata['touchandhold.func'] = curry(self._timeout, touch)
                schedule(touch.userdata['touchandhold.func'], self.hold_time)
            elif type == 'up':
                unschedule(touch.userdata['touchandhold.func'])
        return events
