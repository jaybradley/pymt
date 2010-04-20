# simple example drawing a circle

from random import randint
from pymt import *

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        set_color(1, 0, 0)
        self.circles = []
        self.circles.append(Circle(pos=(100, 100), radius=100, filled=True))
        #self.circle.filled = False

    def draw(self):
        x = randint(0, 500)
        y = randint(0, 500)
        r = randint(5, 100)
        f = bool(r % 2)
        self.circles.append(Circle(pos=(x, y), radius=r, filled=f))
        for c in self.circles:
            c.draw()

runTouchApp(MyObject())
