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
    __slots__ = ('_vbo', '_data', '_format', '_type', '_count', '_stride')
    def __init__(self, **kwargs):
        kwargs.setdefault('format', None)
        kwargs.setdefault('usage', 'GL_DYNAMIC_DRAW')
        kwargs.setdefault('target', 'GL_ARRAY_BUFFER')

        assert( kwargs.get('format') != None )

        super(Graphic, self).__init__()

        self._vbo = vbo.VBO(array('f'),
                            usage=kwargs.get('usage'),
                            target=kwargs.get('target'))
        self._format = []
        self._type = 0
        self._count = 0
        self._stride = 0
        self._data = array('f')
        self.type = kwargs.get('type')
        self.format = kwargs.get('format')

        assert(self._type != None)

    def draw(self):
        format, type = self._format, self._type
        if type is None or len(format) == 0:
            return
        index = 0

        # bind the vertex buffer
        self._vbo.bind()

        # bind data and enable required client state
        for fmt in format:
            size = len(fmt)
            func, state = _pointers_gl[fmt[0]]
            func(size, GL_FLOAT, index, None)
            glEnableClientState(state)
            index += size

        # draw array
        glDrawArrays(type, 0, self.count)

        # deactivate client state
        for fmt in format:
            glDisableClientState(_pointers_gl[fmt[0]][1])

    def _set_format(self, format):
        if type(format) == str:
            f, last = [], None
            for x in format:
                if last is None:
                    last = x
                elif last[0] == x:
                    last += x
                else:
                    f.append(last)
                    last = x
            if last is not None:
                f.append(last)
            self._format = f
            self._stride = len(format)
        else:
            self._format = format
            self._stride = sum([len(x) for x in format])
    def _get_format(self):
        return self._format
    format = property(
        lambda self: self._get_format(),
        lambda self, x: self._set_format(x))

    def _set_data(self, data):
        self._count = len(data) / self._stride
        self._data = data
        self._vbo.set_array(self._data.tostring())
    def _get_data(self):
        return self._data
    data = property(
        lambda self: self._get_data(),
        lambda self, x: self._set_data(x))

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

    @property
    def stride(self):
        return self._stride

class Line(Graphic):
    __slots__ = ('points')
    def __init__(self, points, **kwargs):
        kwargs.setdefault('type', 'line_loop')
        super(Line, self).__init__(format='vv', **kwargs)
        self.points = points

    def _get_points(self):
        return self.data.tolist()
    def _set_points(self, x):
        self.data = array('f', x)
    points = property(
        lambda self: self._get_points(),
        lambda self, x: self._set_points(x))

class Rectangle(Graphic):
    __slots__ = ('_pos', '_size', '_texture', '_tex_coords', '_colors_coords',
                 '_need_rebuild')
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

    def rebuild(self):
        x, y = self.pos
        w, h = self.size
        texture = self.texture
        tex_coords = self.tex_coords
        colors_coords = self.colors_coords

        v = array('f')

        # if texture is provided, use it
        if texture:
            if type(texture) in (pymt.Texture, pymt.TextureRegion):
                tex_coords = texture.tex_coords
            # if tex_coords is provided, use it
            if tex_coords is None:
                tex_coords = (0.0,0.0, 1.0,0.0, 1.0,1.0, 0.0,1.0)

        # build the vertex
        v.extend([x, y])
        if texture: v.extend(tex_coords[0:2])
        if colors_coords: v.extend(colors_coords[0:4])
        v.extend([x + w, y])
        if texture: v.extend(tex_coords[2:4])
        if colors_coords: v.extend(colors_coords[4:8])
        v.extend([x + w, y + h])
        if texture: v.extend(tex_coords[4:6])
        if colors_coords: v.extend(colors_coords[8:12])
        v.extend([x, y + h])
        if texture: v.extend(tex_coords[6:8])
        if colors_coords: v.extend(colors_coords[12:16])

        # assign data
        self.data = v

    def draw(self):
        if self._need_rebuild:
            self.rebuild()
            self._need_rebuild = False
        tex = self._texture
        if tex:
            tex.bind()
        super(Rectangle, self).draw()
        if tex:
            tex.release()

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

