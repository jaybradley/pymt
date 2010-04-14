# simple example with drawing rectangle + texture

from pymt import *
import math, random, os

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        self.img = Image(os.path.join(os.path.dirname(__file__), 'pic1.jpg'))
        p = []
        for x in xrange(100):
            x, y = map(lambda x: random.random() * 600, xrange(2))
            p.append(Rectangle(pos=(x, y), size=(100, 100), texture=self.img.texture))
        self.p = p
        self.d = 0

    def draw(self):
        self.d += getFrameDt()
        if self.d > 1:
            for m in self.p:
                m.pos = map(lambda x: random.random() * 600, xrange(2))
            self.d = 0
        for m in self.p:
            m.draw()
runTouchApp(MyObject())
