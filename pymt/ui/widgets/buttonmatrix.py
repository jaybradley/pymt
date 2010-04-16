'''
Button matrix: a lightweight and optimized grid of buttons
'''

#
# TODO: rewrite this using one specific VBO + color
#


__all__ = ['MTButtonMatrix']

from ...graphx import Canvas
from ..factory import MTWidgetFactory
from widget import MTWidget


class MTButtonMatrix(MTWidget):
    '''ButtonMatrix is a lightweight Grid of buttons/tiles
      collide_point returns which matrix element was hit
      draw_tile(i,j) draws the  tile @ matrix position (i,j)

    :Parameters:
        `matrix_size` : tuple, default to (3, 3)
            Matrix size
        `border` : int, default to 5
            Size of border
        `buttoncolor` : color, default to (.2, .2, .2, 1)
            Color of background
        `downcolor` : color, default to (0, .5, 1, 1)
            Color when the button is pushed

    :Events:
        `on_value_change` (matrix)
            Returns the whole matrix and a button is touched
        `on_press` (row,column,state)
            Returns the state and cell position of a button when touched
    '''
    def __init__(self,**kwargs):
        kwargs.setdefault('matrix_size', (3,3))
        kwargs.setdefault('border', 5)
        kwargs.setdefault('buttoncolor', (0.5,0.5,0.5,1))
        kwargs.setdefault('downcolor', (0,0.5,1,1))
        super(MTButtonMatrix, self).__init__(**kwargs)

        self.register_event_type('on_value_change')
        self.register_event_type('on_press')

        self._matrix_size = kwargs.get('matrix_size')
        self.border = kwargs.get('border')
        self.buttoncolor = kwargs.get('buttoncolor')
        self.downcolor = kwargs.get('downcolor')
        self.matrix = [[0 for i in range(self._matrix_size[1])] for j in range(self._matrix_size[0])]
        self.last_tile = 0
        self._canvas = Canvas()
        self._colors = []
        self._need_build = True

    def build(self):
        self._canvas.clear()
        canvas = self._canvas
        colors = self._colors
        x, y = self.pos
        w, h = self.size
        border = self.border
        mw, mh = self._matrix_size
        dw, dh = w / mw, h / mh
        for j in xrange(self._matrix_size[1]):
            for i in xrange(self._matrix_size[0]):
                p = x +  dw * i, y + dh * j
                s = dw - border, dh - border
                colors.append(canvas.color(*self.buttoncolor))
                canvas.rectangle(pos=p, size=s)

    def reset(self):
        self.matrix = [[0 for i in range(self._matrix_size[1])] for j in range(self._matrix_size[0])]

    def on_value_change(self, matrix):
        pass

    def _get_matrix_size(self):
        return self._matrix_size
    def _set_matrix_size(self, size):
        self._matrix_size = size
        self.matrix = [[0 for i in range(self._matrix_size[1])] for j in range(self._matrix_size[0])]
    matrix_size = property(_get_matrix_size,_set_matrix_size,
                           doc='Return size of matrix')

    def draw(self):
        if self._need_build:
            self.build()
            self._need_build = False
        self._canvas.draw()

    def collide_point(self, x, y):
        i = (x - self.x)/(self.width/self._matrix_size[0])
        j = (y - self.y)/(self.height/self._matrix_size[1])
        if i >= self._matrix_size[0] or j >= self._matrix_size[1]:
            return False # returns false if the click is not within the widget
        if i < 0 or j < 0:
            return False
        else:
            return (int(i),int(j))

    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            i, j = self.collide_point(touch.x, touch.y)
            mw, mh = self.matrix_size
            idx = j * mw + i
            if self.matrix[i][j]:
                self.matrix[i][j] = 0
                self._colors[idx].color = self.buttoncolor
            else:
                self.matrix[i][j] = 1
                self._colors[idx].color = self.downcolor
            self.dispatch_event('on_value_change', self.matrix)
            self.dispatch_event('on_press', (i,j, self.matrix[i][j]))
            self.last_tile = (i,j)

    def on_touch_move(self, touch):
        if self.collide_point(touch.x, touch.y) != self.last_tile:
           self.on_touch_down(touch)

MTWidgetFactory.register('MTButtonMatrix', MTButtonMatrix)
