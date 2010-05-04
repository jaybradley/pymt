# simple example with drawing line

from pymt import *
from random import random
import math
import os

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
        self.img = Image(os.path.join(os.path.dirname(__file__), 'brush_particle.png'))
        self.c = Canvas()
        p = []
        for x in xrange(500):
            p += list(map(lambda x: random() * 600, xrange(2)))
        self.c.color(0, .5, .7, .2)
        self.p = self.c.point(p, texture=self.img.texture, radius=20)

    def draw(self):
        self.c.draw()

    def on_touch_down(self, touch):
        self.p.radius = random() * 50

runTouchApp(MyObject())
