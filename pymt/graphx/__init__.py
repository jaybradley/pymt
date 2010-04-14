'''
Graphx: all low level function to draw object in OpenGL.

Previous version of graphx was rely on Immediate mode of OpenGL. Immediate mode
is not anymore allowed in OpenGL 3.0, and OpenGL ES. That's why all draw* are
now deprecated.

In order to create line, rectangle.. you must create object, then draw them.

An example with a line ::

    line = Line([50, 50, 100, 100])
    line.draw()

    # If you want to change point of the line later, you can do
    line.points = [80, 80, 100, 100]

    # Or even add points into the line
    line.points += [58, 35]


An example with a rectangle ::

    rect = Rectangle(pos=(50, 50), size=(200, 200))
    rect.draw()

    # You can change pos, size...
    rect.pos = (10, 10)
    rect.size = (999, 999)

'''

# TODO compatibility, must be removed
from old import *

import pymt
from array import array
from pymt import BaseObject
from OpenGL.arrays import vbo
from OpenGL.GL import *


#
# Documentation:
#  http://www.opengl.org/wiki/Vertex_Buffer_Object
#
# Format:
#  v = Vertex (vv = xy, vvv = xyz)
#  c = Color (ccc = rgb, cccc = rgba)
#  t = Texture (tt = uv, ttt = uvw)
#  n = Normal (nn = xy, nnn = xyz)
#  i = Index
#  e = Edge
#
_pointers_gl = {
    'v': (glVertexPointer, GL_VERTEX_ARRAY),
    'c': (glColorPointer, GL_COLOR_ARRAY),
    't': (glTexCoordPointer, GL_TEXTURE_COORD_ARRAY),
    'n': (glNormalPointer, GL_NORMAL_ARRAY),
    'e': (glEdgeFlagPointer, GL_EDGE_FLAG_ARRAY),
    'i': (glIndexPointer, GL_INDEX_ARRAY),
}

_type_gl = {
    'points': GL_POINTS,
    'lines': GL_LINES,
    'line_loop': GL_LINE_LOOP,
    'triangles': GL_TRIANGLES,
    'triangle_fan': GL_TRIANGLE_FAN,
    'quads': GL_QUADS,
}

def _make_point_list(points):
    t = type(points)
    if not t in (tuple, list):
        raise Exception('Point list must be tuple or list of' +
                        'coordinates or points(tuple/list of 2D coords)')
    if type(points[0]) in (tuple, list): #flatten the points
        return [coord for point in points for coord in point]
    else:
        return list(points)

class Graphic(object):
    __slots__ = ('_vbo', '_vbo_usage', '_vbo_target',
                 '_data', '_format', '_type', '_count')
    def __init__(self, **kwargs):
        kwargs.setdefault('format', None)
        kwargs.setdefault('usage', 'GL_DYNAMIC_DRAW')
        kwargs.setdefault('target', 'GL_ARRAY_BUFFER')

        assert( kwargs.get('format') != None )

        super(Graphic, self).__init__()

        self._data = {}
        self._vbo = {}
        self._vbo_usage = kwargs.get('usage')
        self._vbo_target = kwargs.get('target')
        self._format = {}
        self._type = 0
        self._count = 0
        self.type = kwargs.get('type')
        self.format = kwargs.get('format')

        assert(self._type != None)

    def draw(self):
        format, type = self._format, self._type
        if type is None or len(format) == 0:
            return

        # bind data and enable required client state
        _vbo = self._vbo
        for fmt, size in format.items():
            func, state = _pointers_gl[fmt[0]]
            _vbo[fmt].bind()
            func(size, GL_FLOAT, 0, None)
            glEnableClientState(state)

        # draw array
        glDrawArrays(type, 0, self.count)

        # deactivate client state
        for fmt in format.keys():
            _vbo[fmt].unbind()
            glDisableClientState(_pointers_gl[fmt[0]][1])

    def _set_format(self, format):
        if type(format) == str:
            self._format = {}
            f, last = [], None
            for x in format:
                if last is None:
                    last = x
                elif last[0] == x:
                    last += x
                else:
                    self._format[last[0]] = len(last)
                    last = x
            if last is not None:
                self._format[last[0]] = len(last)
        else:
            self._format = format
    def _get_format(self):
        return self._format
    format = property(
        lambda self: self._get_format(),
        lambda self, x: self._set_format(x))

    def _set_data(self, typ, data):
        try:
            _vbo = self._vbo[typ]
        except KeyError:
            _vbo = vbo.VBO('', usage=self._vbo_usage, target=self._vbo_target)
            self._vbo[typ] = _vbo
        if typ == 'v':
            self._count = len(data) / self._format['v']
        if type(data) is not array:
            data = array('f', data)
        self._data[typ] = data
        _vbo.set_array(data.tostring())
    def _get_data(self, typ):
        try:
            return self._data[typ]
        except KeyError:
            return None
    data_v = property(
        lambda self: self._get_data('v'),
        lambda self, x: self._set_data('v', x))
    data_c = property(
        lambda self: self._get_data('c'),
        lambda self, x: self._set_data('c', x))
    data_t = property(
        lambda self: self._get_data('t'),
        lambda self, x: self._set_data('t', x))
    data_n = property(
        lambda self: self._get_data('n'),
        lambda self, x: self._set_data('n', x))
    data_e = property(
        lambda self: self._get_data('e'),
        lambda self, x: self._set_data('e', x))
    data_i = property(
        lambda self: self._get_data('i'),
        lambda self, x: self._set_data('i', x))

    def _get_type(self):
        return self._type
    def _set_type(self, x):
        if type(x) is str:
            x = _type_gl[x]
        self._type = x
    type = property(
        lambda self: self._get_type(),
        lambda self, x: self._set_type(x))

    @property
    def count(self):
        return self._count

class Line(Graphic):
    __slots__ = ('points')
    def __init__(self, points, **kwargs):
        kwargs.setdefault('type', 'line_loop')
        super(Line, self).__init__(format='vv', **kwargs)
        self.points = points

    def _get_points(self):
        return self.data_v.tolist()
    def _set_points(self, x):
        self.data_v = x
    points = property(
        lambda self: self._get_points(),
        lambda self, x: self._set_points(x))

class Rectangle(Graphic):
    __slots__ = ('_pos', '_size', '_texture', '_tex_coords', '_colors_coords',
                 '_need_rebuild', '_stmt')
    def __init__(self, **kwargs):
        kwargs.setdefault('type', 'quads')
        kwargs.setdefault('pos', (0, 0))
        kwargs.setdefault('size', (1, 1))
        kwargs.setdefault('texture', None)
        kwargs.setdefault('tex_coords', None)
        kwargs.setdefault('colors_coords', None)

        format = 'vv'
        if kwargs.get('texture'):
            format += 'tt'
        if kwargs.get('colors_coords'):
            format += 'cccc'
        kwargs.setdefault('format', format)
        
        super(Rectangle, self).__init__(**kwargs)

        self._pos = kwargs.get('pos')
        self._size = kwargs.get('size')
        self._texture = kwargs.get('texture')
        self._tex_coords = kwargs.get('tex_coords')
        self._colors_coords = kwargs.get('colors_coords')
        self._need_rebuild = True
        self._stmt = None
        if self._texture:
            self._stmt = gx_texture(self._texture)

    def rebuild(self):
        # build vertex
        x, y = self.pos
        w, h = self.size
        self.data_v = (x, y, x + w, y, x + w, y + h, x, y + h)

        # if texture is provided, use it
        texture = self.texture
        if texture:
            tex_coords = self.tex_coords
            if type(texture) in (pymt.Texture, pymt.TextureRegion):
                tex_coords = texture.tex_coords
            # if tex_coords is provided, use it
            if tex_coords is None:
                tex_coords = (0.0,0.0, 1.0,0.0, 1.0,1.0, 0.0,1.0)

            # assign tex_coords
            self.data_t = tex_coords

        # assign colors coords
        if self.colors_coords:
            self.data_c = self.colors_coords

    def draw(self):
        if self._need_rebuild:
            self.rebuild()
            self._need_rebuild = False
        stmt = self._stmt
        if stmt:
            stmt.bind()
        super(Rectangle, self).draw()
        if stmt:
            stmt.release()

    def _get_size(self):
        return self._size
    def _set_size(self, size):
        if self._size == size:
            return False
        self._size = size
        self._need_rebuild = True
        return True
    size = property(lambda self: self._get_size(),
                    lambda self, x: self._set_size(x),
                    doc='Object size (width, height)')

    def _get_width(self):
        return self._size[0]
    def _set_width(self, w):
        if self._size[0] == w:
            return False
        self._size = (w, self._size[1])
        self._need_rebuild = True
        return True
    width = property(lambda self: self._get_width(),
                     lambda self, x: self._set_width(x),
                     doc='Object width')

    def _get_height(self):
        return self._size[1]
    def _set_height(self, h):
        if self._size[1] == h:
            return False
        self._size = (self._size[0], h)
        self._need_rebuild = True
        return True
    height = property(lambda self: self._get_height(),
                     lambda self, x: self._set_height(x),
                      doc='Object height')

    def _get_pos(self):
        return self._pos
    def _set_pos(self, pos):
        if pos == self._pos:
            return False
        self._pos = tuple(pos)
        self._need_rebuild = True
        return True
    pos = property(lambda self: self._get_pos(),
                   lambda self, x: self._set_pos(x), doc='Object position (x, y)')

    def _get_x(self):
        return self._pos[0]
    def _set_x(self, x):
        if x == self.pos[0]:
            return False
        self._pos = (x, self.y)
        self._need_rebuild = True
        return True
    x = property(lambda self: self._get_x(),
                 lambda self, x: self._set_x(x),
                 doc = 'Object X position')

    def _get_y(self):
        return self._pos[1]
    def _set_y(self, y):
        if y == self.pos[1]:
            return False
        self._pos = (self.x, y)
        self._need_rebuild = True
        return True
    y = property(lambda self: self._get_y(),
                 lambda self, x: self._set_y(x),
                 doc = 'Object Y position')

    def _get_center(self):
        return (self._pos[0] + self._size[0] / 2., self._pos[1] + self._size[1] / 2.)
    def _set_center(self, center):
        return self._set_pos((center[0] - self._size[0] / 2.,
                              center[1] - self._size[1] / 2.))
    center = property(lambda self: self._get_center(),
                      lambda self, x: self._set_center(x),
                      doc='Object center (cx, cy)')

    def _get_texture(self):
        return self._texture
    def _set_texture(self, x):
        self._texture = x
        if self._texture:
            self._stmt = gx_texture(self._texture)
    texture = property(
        lambda self: self._get_texture(),
        lambda self, x: self._set_texture(x)
    )

    def _get_tex_coords(self):
        return self._tex_coords
    def _set_tex_coords(self, x):
        self._tex_coords = x
        self._need_rebuild = True
    tex_coords = property(
        lambda self: self._get_tex_coords(),
        lambda self, x: self._set_tex_coords(x)
    )

    def _get_colors_coords(self):
        return self._colors_coords
    def _set_colors_coords(self, x):
        self._colors_coords = x
        self._need_rebuild = True
    colors_coords = property(
        lambda self: self._get_colors_coords(),
        lambda self, x: self._set_colors_coords(x)
    )

