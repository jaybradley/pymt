# simple example with a canvas, and play with it

from pymt import *

class MyObject(MTWidget):
    def __init__(self, **kwargs):
        super(MyObject, self).__init__(**kwargs)
        c = Canvas()

        c.color(.5)
        c.line([10, 10, 50, 50, 10, 50])

        c.save() # save the current state of drawing
        c.color(1, 0, 0, .2)
        c.rectangle(pos=(5, 5), size=(70, 70))

        c.restore() # restore the old state (color will be restored)

        # this rectangle should be in gray
        c.rectangle(pos=(50, 50), size=(100, 100))

        self.c = c

    def draw(self):
        self.c.draw()

runTouchApp(MyObject())

