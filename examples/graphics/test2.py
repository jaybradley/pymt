# simple example with drawing rectangle

from pymt import *
import math, random

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        p = []
        for x in xrange(100):
            x, y = map(lambda x: random.random() * 600, xrange(2))
            p.append(Rectangle(pos=(x, y), size=(100, 100)))
        self.p = p

    def draw(self):
        x, y = map(lambda x: random.random() * 600, xrange(2))
        for m in self.p:
            x, y = map(lambda x: random.random() * 600, xrange(2))
            m.pos = x, y
            m.draw()

runTouchApp(MyObject())
