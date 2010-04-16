# simple example with drawing line

from pymt import *
from random import random
import math

css_add_sheet('''
myobject {
    draw-background: 1;
    bg-color: rgba(0, 255, 0, 255);
    draw-border: 1;
    border-color: rgb(255, 0, 0);
    border-radius: 25;
    border-radius-precision: 0.1;
    border-width: 4;
}
''')

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        self.c = Canvas()
        for x in xrange(500):
            x, y, w, h = map(lambda x: random() * 600, xrange(4))
            self.c.cssRectangle(x, y, w, h, style=self.style)

    def draw(self):
        self.c.draw()

runTouchApp(MyObject())
