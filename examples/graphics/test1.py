# simple example with drawing line

from pymt import *
import math, random

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        p = []
        for x in xrange(50000):
            p.extend([100 + 50 * math.cos(x / 1000.), 100 + 50 * math.sin(x / 1000.)])
        self.line = Line(points=p)

    def draw(self):
        self.line.points += (map(lambda x: random.random() * 600, xrange(2)))
        self.line.draw()
        set_color(.2)
        drawLabel(label='%d' % self.line.count, font_size=35, pos=(50, 50),
                 center=False)

runTouchApp(MyObject())
