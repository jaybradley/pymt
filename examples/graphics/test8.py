# drawing text

from pymt import *
import math, random, os

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        self.c = Canvas()
        self.generate()

    def generate(self):
        self.c.clear()
        for x in xrange(200):
            x, y = map(lambda x: int(random.random() * 600), xrange(2))
            self.c.color(*map(lambda x: random.random(), xrange(4)))
            self.c.text(label='I=%d' % x, pos=(x, y),
                        font_size=int(8 + random.random() * 30))

    def draw(self):
        self.c.draw()

    def on_touch_down(self, touch):
        self.generate()

runTouchApp(MyObject())
