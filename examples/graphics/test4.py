# simple example with drawing rounded rectangle

from pymt import *
import math, random, os

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        p = []
        for x in xrange(100):
            x, y = map(lambda x: random.random() * 600, xrange(2))
            p.append(RoundedRectangle(pos=(x, y), size=(100, 100), radius=50))
        self.p = p
        self.idx = 0

    def draw(self):
        self.idx += 1
        for m in self.p:
            m.radius = abs(math.cos(self.idx / 20.)) * 50
            m.draw()
runTouchApp(MyObject())

