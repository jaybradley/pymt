'''
Graphx: all low level function to draw object in OpenGL.

Previous version of graphx was rely on Immediate mode of OpenGL. Immediate mode
is not anymore allowed in OpenGL 3.0, and OpenGL ES. That's why all draw* are
now deprecated.

In order to create line, rectangle.. you must create object, then draw them.

An example with a line ::

    # in init function
    line = Line([50, 50, 100, 100])

    # in draw function
    line.draw()

    # If you want to change point of the line later, you can do
    line.points = [80, 80, 100, 100]

    # Or even add points into the line
    line.points += [58, 35]


An example with a rectangle ::

    # in init function
    rect = Rectangle(pos=(50, 50), size=(200, 200))

    # in draw function
    rect.draw()

    # You can change pos, size...
    rect.pos = (10, 10)
    rect.size = (999, 999)

An example with a rectangle + texture ::

    # in init function
    img = Image('test.png')
    rect = Rectangle(size=(100, 100), texture=img.texture)

    # in draw function
    rect.draw()

'''

# TODO compatibility, must be removed
from old import *

import pymt
import math
import collections
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
    'line_strip': GL_LINE_STRIP,
    'triangles': GL_TRIANGLES,
    'triangle_fan': GL_TRIANGLE_FAN,
    'triangle_strip': GL_TRIANGLE_STRIP,
    'quads': GL_QUADS,
    'quad_strip': GL_QUAD_STRIP,
    'polygon': GL_POLYGON
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

class GraphicContext(object):
    '''Handle the saving/restore of the context
    
    TODO: explain more how it works
    '''
    __slots__ = ('state', 'stack', 'journal')
    def __init__(self):
        super(GraphicContext, self).__init__()
        self.state = {}
        self.stack = []
        self.journal = {}

        # create initial state
        self.reset()
        self.save()

    def __getattr__(self, attr):
        if attr in GraphicContext.__slots__:
            return super(GraphicContext, self).__getattribute__(attr)
        return super(GraphicContext, self).__getattribute__('state')[attr]

    def __setattr__(self, attr, value):
        if attr in GraphicContext.__slots__:
            super(GraphicContext, self).__setattr__(attr, value)
        else:
            # save into the context
            super(GraphicContext, self).__getattribute__('state')[attr] = value
            # save into the journal for a futur play
            super(GraphicContext, self).__getattribute__('journal')[attr] = True

    def reset(self):
        self.color = (1, 1, 1, 1)
        self.blend = False
        self.blend_sfactor = GL_SRC_ALPHA
        self.blend_dfactor = GL_ONE_MINUS_SRC_ALPHA
        self.linewidth = 1

    def save(self):
        self.stack.append(self.state.copy())

    def restore(self):
        newstate = self.stack.pop()
        state = self.state
        set = self.__setattr__
        for k, v in newstate.items():
            if state[k] != v:
                set(k, v)

    def flush(self):
        # activate all the last changes done on context
        # apply all the actions in the journal !
        if not len(self.journal):
            return
        state = self.state
        journal = self.journal
        for x in journal.keys():
            value = state[x]
            if x == 'color':
                glColor4f(*value)
            elif x == 'blend':
                if value:
                    glEnable(GL_BLEND)
                else:
                    glDisable(GL_BLEND)
            elif x in ('blend_sfactor', 'blend_dfactor'):
                glBlendFunc(state['blend_sfactor'], state['blend_dfactor'])
            elif x == 'linewidth':
                glLineWidth(value)
        journal.clear()


#: Default canvas used in graphic element
default_context = GraphicContext()

class GraphicInstruction(object):
    __slots__ = ('context', )
    def __init__(self):
        super(GraphicInstruction, self).__init__()
        self.context = default_context
    def draw(self):
        '''Draw/Execute the graphical element on screen'''
        pass

class GraphicContextSave(GraphicInstruction):
    def draw(self):
        self.context.save()

class GraphicContextRestore(GraphicInstruction):
    def draw(self):
        self.context.restore()

class GraphicContextChange(GraphicInstruction):
    __slots__ = ('instructions', )
    def __init__(self, **kwargs):
        super(GraphicContextChange, self).__init__()
        self.instructions = kwargs
    def draw(self):
        for k, v in self.instructions.iteritems():
            setattr(self.context, k, v)

class GraphicElement(GraphicInstruction):
    '''
    This is the lowest graphical element you can use. It's an abstraction to
    Vertex Buffer Object, and you can push your vertex, color, texture ... and
    draw them easily.

    The format of the buffer is specified in characters code. For example,
    'vvcccc' mean you'll have 2 vertex + 4 colors coordinates.
    You have 6 differents components that you can use:
        * v: vertex
        * c: color
        * t: texture
        * n: normal
        * i: index (not yet used)
        * e: edge (not yet used)

    For each component, VBO are separated.
    
    :Parameters:
        `format`: string, default to None
            The format must be specified at start, and cannot be changed once
            the graphic is created.
        `type`: string, default to None
            Specify how the graphic will be drawed. One of: 'lines',
            'line_loop', 'line_strip', 'triangles', 'triangle_fan',
            'triangle_strip', 'quads', 'quad_strip', 'points', 'polygon'
        `usage`: string, default to 'GL_DYNAMIC_DRAW'
            Specify the usage of VBO. Can be one of 'GL_STREAM_DRAW',
            'GL_STREAM_READ', 'GL_STREAM_COPY', 'GL_STATIC_DRAW',
            'GL_STATIC_READ', 'GL_STATIC_COPY', 'GL_DYNAMIC_DRAW',
            'GL_DYNAMIC_READ', or 'GL_DYNAMIC_COPY'.
            Infos: http://www.opengl.org/sdk/docs/man/xhtml/glBufferData.xml
        `target`: string, default to 'GL_ARRAY_BUFFER'
            Target of the VBO. Can be one of 'GL_ARRAY_BUFFER',
            'GL_ELEMENT_ARRAY_BUFFER', 'GL_PIXEL_PACK_BUFFER', or
            'GL_PIXEL_UNPACK_BUFFER'.
            Infos: http://www.opengl.org/sdk/docs/man/xhtml/glBufferData.xml
    '''

    __slots__ = ('_vbo', '_vbo_usage', '_vbo_target',
                 '_data', '_format', '_type', '_count')

    def __init__(self, **kwargs):
        kwargs.setdefault('format', None)
        kwargs.setdefault('type', None)
        kwargs.setdefault('usage', 'GL_DYNAMIC_DRAW')
        kwargs.setdefault('target', 'GL_ARRAY_BUFFER')

        assert(kwargs.get('format') != None)
        assert(kwargs.get('type') != None)

        super(GraphicElement, self).__init__()

        self._data = {}
        self._vbo = {}
        self._vbo_usage = kwargs.get('usage')
        self._vbo_target = kwargs.get('target')
        self._format = {}
        self._type = 0
        self._count = 0
        self.type = kwargs.get('type')
        self.format = kwargs.get('format')

    def draw(self):
        format, type = self._format, self._type
        if type is None or len(format) == 0:
            return

        # bind data and enable required client state
        # first, for each format component, extract the gl function to use
        # and bind the vbo associated + activate
        _vbo = self._vbo
        for fmt, size in format.items():
            func, state = _pointers_gl[fmt[0]]
            _vbo[fmt].bind()
            func(size, GL_FLOAT, 0, None)
            glEnableClientState(state)

        # activate at the very last moment all changes done on context
        self.context.flush()

        # draw array
        glDrawArrays(type, 0, self.count)

        # deactivate client state
        for fmt in format.keys():
            _vbo[fmt].unbind()
            glDisableClientState(_pointers_gl[fmt[0]][1])

    def _set_format(self, format):
        if type(format) == str:
            # transform the 'vvttcccc' to
            # {'v': 2, 't': 2, 'c': 4}
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
        elif type(format) == dict:
            self._format = format
        else:
            raise Exception('Invalid format')
    def _get_format(self):
        return ''.join([x * y for x, y in self._format.items()])
    format = property(
        lambda self: self._get_format(),
        lambda self, x: self._set_format(x),
        doc='Return the format of the graphic in string (eg. "vvttcccc")')

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
        lambda self, x: self._set_data('v', x),
        doc='Get/set the vertex coordinates data')
    data_c = property(
        lambda self: self._get_data('c'),
        lambda self, x: self._set_data('c', x),
        doc='Get/set the colors coordinates data')
    data_t = property(
        lambda self: self._get_data('t'),
        lambda self, x: self._set_data('t', x),
        doc='Get/set the texture coordinates data')
    data_n = property(
        lambda self: self._get_data('n'),
        lambda self, x: self._set_data('n', x),
        doc='Get/set the normal coordinates data')
    data_e = property(
        lambda self: self._get_data('e'),
        lambda self, x: self._set_data('e', x),
        doc='Get/set the edges data (not used yet.)')
    data_i = property(
        lambda self: self._get_data('i'),
        lambda self, x: self._set_data('i', x),
        doc='Get/set the indexes data (not used yet.)')

    def _get_type(self):
        return self._type
    def _set_type(self, x):
        if type(x) is str:
            x = _type_gl[x]
        self._type = x
    type = property(
        lambda self: self._get_type(),
        lambda self, x: self._set_type(x),
        doc='''
            Specify how the graphic will be drawed. One of: 'lines',
            'line_loop', 'line_strip', 'triangles', 'triangle_fan',
            'triangle_strip', 'quads', 'quad_strip', 'points', 'polygon'
        ''')

    @property
    def count(self):
        '''Return the number of elements (if format is vv, and you have 4
        vertex, it will return 2). The number of elements is calculated on
        vertex.'''
        return self._count


class Line(GraphicElement):
    '''
    Construct line from points.
    This object is a simplification of Graphic method to draw line.
    '''
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
        lambda self, x: self._set_points(x),
        doc='''Add/remove points of the line'''
    )


class Rectangle(GraphicElement):
    '''
    Construct a rectangle from position + size.
    The rectangle can be use to draw shape of rectangle, filled rectangle,
    textured rectangle, rounded rectangle...

    ..warning ::
        Each time you change one property of the rectangle, vertex list is
        automaticly builded at the next draw() call. 

    :Parameters:
        `*values`: list, default to None
            Can be used to provide a tuple of (x, y, w, h)
        `pos`: list, default to (0, 0)
            Position of the rectangle
        `size`: list, default to (1, 1)
            Size of the rectangle
        `texture`: texture, default to None
            Specify the texture to use for the rectangle
        `tex_coords`: list, default to None
            If a texture is specified, the tex_coords will be taken from the
            texture argument. Otherwise, it will be set on 0-1 range.
        `colors_coords`: list, default to None
            Can be used to specify a color for each vertex drawed.
    '''
    __slots__ = ('_pos', '_size', '_texture', '_tex_coords', '_colors_coords',
                 '_need_build', '_stmt')
    def __init__(self, *values, **kwargs):
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
        if len(values) == 4:
            x, y, w, h = values
            self._pos = x, y
            self._size = w, h
        elif len(values) != 0:
            raise Exception('Rectangle values must be passed like this: Rectangle(x, y, w, h)')
        self._texture = kwargs.get('texture')
        self._tex_coords = kwargs.get('tex_coords')
        self._colors_coords = kwargs.get('colors_coords')
        self._need_build = True
        self._stmt = None
        if self._texture:
            self._stmt = gx_texture(self._texture)

    def build(self):
        '''Build all the vbos. This is automaticly called when a property
        change (position, size, tex_coords...)'''
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
        if self._need_build:
            self.build()
            self._need_build = False
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
        self._need_build = True
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
        self._need_build = True
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
        self._need_build = True
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
        self._need_build = True
        return True
    pos = property(lambda self: self._get_pos(),
                   lambda self, x: self._set_pos(x),
                   doc='Object position (x, y)')

    def _get_x(self):
        return self._pos[0]
    def _set_x(self, x):
        if x == self.pos[0]:
            return False
        self._pos = (x, self.y)
        self._need_build = True
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
        self._need_build = True
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
        if self._texture == x:
            return
        self._texture = x
        if self._texture:
            self._stmt = gx_texture(self._texture)
    texture = property(
        lambda self: self._get_texture(),
        lambda self, x: self._set_texture(x),
        doc='Texture to use on the object'
    )

    def _get_tex_coords(self):
        return self._tex_coords
    def _set_tex_coords(self, x):
        if self._tex_coords == x:
            return
        self._tex_coords = x
        self._need_build = True
    tex_coords = property(
        lambda self: self._get_tex_coords(),
        lambda self, x: self._set_tex_coords(x),
        doc='''
        Texture coordinates to use on the object. If nothing is set, it
        will take the coordinates from the current texture
        '''
    )

    def _get_colors_coords(self):
        return self._colors_coords
    def _set_colors_coords(self, x):
        if self._colors_coords == x:
            return
        self._colors_coords = x
        self._need_build = True
    colors_coords = property(
        lambda self: self._get_colors_coords(),
        lambda self, x: self._set_colors_coords(x),
        doc='Colors coordinates for each vertex'
    )


class RoundedRectangle(Rectangle):
    '''Draw a rounded rectangle

    warning.. ::
        Rounded rectangle support only vertex, not other things right now.
        It may change in the future.

    :Parameters:
        `radius` : int, default to 5
            Radius of corner
        `precision` : float, default to 0.5
            Precision of corner angle
        `corners` : tuple of bool, default to (True, True, True, True)
            Indicate if round must be draw for each corners
            starting to bottom-left, bottom-right, top-right, top-left
    '''
    __slots__ = ('_corners', '_precision', '_radius')
    def __init__(self, **kwargs):
        kwargs.setdefault('type', 'polygon')
        kwargs.setdefault('corners', (True, True, True, True))
        kwargs.setdefault('precision', .2)
        kwargs.setdefault('radius', 5)
        super(RoundedRectangle, self).__init__(**kwargs)
        self._corners = kwargs.get('corners')
        self._precision = kwargs.get('precision')
        self._radius = kwargs.get('radius')

    def build(self):
        radius = self._radius
        precision = self._precision
        cbl, cbr, ctr, ctl = self._corners
        x, y = self.pos
        w, h = self.size
        data_v = array('f', [])
        if cbr:
            data_v.extend((x + radius, y))
            data_v.extend((x + w - radius, y))
            t = math.pi * 1.5
            while t < math.pi * 2:
                sx = x + w - radius + math.cos(t) * radius
                sy = y + radius + math.sin(t) * radius
                data_v.extend((sx, sy))
                t += precision
        else:
            data_v.extend((x + w, y))

        if ctr:
            data_v.extend((x + w, y + radius))
            data_v.extend((x + w, y + h - radius))
            t = 0
            while t < math.pi * 0.5:
                sx = x + w - radius + math.cos(t) * radius
                sy = y + h -radius + math.sin(t) * radius
                data_v.extend((sx, sy))
                t += precision
        else:
            data_v.extend((x + w, y + h))

        if ctl:
            data_v.extend((x + w -radius, y + h))
            data_v.extend((x + radius, y + h))
            t = math.pi * 0.5
            while t < math.pi:
                sx = x  + radius + math.cos(t) * radius
                sy = y + h - radius + math.sin(t) * radius
                data_v.extend((sx, sy))
                t += precision
        else:
            data_v.extend((x, y + h))

        if cbl:
            data_v.extend((x, y + h - radius))
            data_v.extend((x, y + radius))
            t = math.pi
            while t < math.pi * 1.5:
                sx = x + radius + math.cos(t) * radius
                sy = y + radius + math.sin(t) * radius
                data_v.extend((sx, sy))
                t += precision
        else:
            data_v.extend((x, y))

        self.data_v = data_v

    def _get_corners(self):
        return self._corners
    def _set_corners(self, x):
        if self._corners == x:
            return
        if type(x) not in (list, tuple):
            raise Exception('Invalid corner type')
        if len(x) != 4:
            raise Exception('Must have 4 boolean inside the corners list')
        self._corners = x
        self._need_build = True
    corners = property(
        lambda self: self._get_corners(),
        lambda self, x: self._set_corners(x),
        doc='Get/set the corners to draw'
    )

    def _get_precision(self):
        return self._precision
    def _set_precision(self, x):
        if self._precision == x:
            return
        self._precision = x
        self._need_build = True
    precision = property(
        lambda self: self._get_precision(),
        lambda self, x: self._set_precision(x),
        doc='Get/set the precision of the corner'
    )
    
    def _get_radius(self):
        return self._radius
    def _set_radius(self, x):
        if self._radius == x:
            return
        self._radius = x
        self._need_build = True
    radius = property(
        lambda self: self._get_radius(),
        lambda self, x: self._set_radius(x),
        doc='Get/set the radius of the corner'
    )


class Color(GraphicInstruction):
    '''Define current color to be used (as float values between 0 and 1) ::

        c = Canvas()
        c.color(1, 0, 0, 1)
        c.rectangle(pos=(50, 50), size=(100, 100))

        c.draw()

    .. Note:
        Blending is activated if alpha value != 1

    :Parameters:
        `*color` : list
            Can have 3 or 4 float value (between 0 and 1)
        `sfactor` : opengl factor, default to GL_SRC_ALPHA
            Default source factor to be used if blending is activated
        `dfactor` : opengl factor, default to GL_ONE_MINUS_SRC_ALPHA
            Default destination factor to be used if blending is activated
        `blend` : boolean, default to None
            Set True if you really want to activate blending, even
            if the alpha color is 1 (mean no blending in theory)
    '''

    __slots__ = ('_blend', '_sfactor', '_dfactor', '_color')

    def __init__(self, *color, **kwargs):
        kwargs.setdefault('sfactor', GL_SRC_ALPHA)
        kwargs.setdefault('dfactor', GL_ONE_MINUS_SRC_ALPHA)
        kwargs.setdefault('blend', None)

        super(Color, self).__init__()

        self._blend = kwargs.get('blend')
        self._sfactor = kwargs.get('sfactor')
        self._dfactor = kwargs.get('dfactor')
        self._color = color

    def draw(self):
        force_blend = self._blend== True
        color = self._color
        ctx = self.context
        l = len(color)

        if l == 1:
            color = (color[0], color[0], color[0], 1)
        elif l == 3:
            color = (color[0], color[1], color[2], 1)
        elif l == 4:
            pass
        else:
            raise Exception('Unsupported color format')
            
        ctx.color = color
        if color[3] == 1 and not force_blend:
            ctx.blend = False
        else:
            ctx.blend = True
            ctx.sfactor = self._sfactor
            ctx.dfactor = self._dfactor

    def _get_color(self):
        return self._color
    def _set_color(self, x):
        if self._color == x:
            return
        self._color = x
    color = property(
        lambda self: self._get_color(),
        lambda self, x: self._set_color(x),
        doc='''Get/Set the color in tuple format (r, g, b, a)'''
    )


class CSSRectangle(GraphicInstruction):
    __slots__ = ('_style', '_prefix', '_state', '_objects', '_pos', '_size',
                 '_need_build')
    def __init__(self, *values, **kwargs):
        kwargs.setdefault('style', {})
        kwargs.setdefault('prefix', None)
        kwargs.setdefault('state', None)
        kwargs.setdefault('pos', (0, 0))
        kwargs.setdefault('size', (1, 1))

        super(CSSRectangle, self).__init__()

        self._objects = []
        self._style = kwargs.get('style')
        self._prefix = kwargs.get('prefix')
        self._state = kwargs.get('state')
        self._pos = kwargs.get('pos')
        self._size = kwargs.get('size')
        if len(values) == 4:
            x, y, w, h = values
            self._pos = x, y
            self._size = w, h
        elif len(values) != 0:
            raise Exception('CSSRectangle values must be passed like this: CSSRectangle(x, y, w, h)')

        self._need_build = True

    def build(self):
        self._objects = []

        state = self._state
        style = self._style
        prefix = self._prefix
        obj = self._objects

        # get background image.
        # don't add anything else if we just have a background image.
        bg_image = style.get('bg-image-' + str(state))
        if not bg_image:
            bg_image = style.get('bg-image')
        if bg_image:
            obj.append(Rectangle(pos=self._pos, size=self._size))
            return

        # lets use the ones for given state,
        # and ignore the regular ones if the state ones are there
        if state:
            state = '-' + state
            newstyle = {}
            overwrites = []
            for s in style:
                if state in s:
                    overwrite  = s.replace(state, '')
                    newstyle[overwrite] = style[s]
                    overwrites.append(overwrite)
                if s not in overwrites:
                    newstyle[s] = style[s]
            style = newstyle

        # hack to remove prefix in style
        if prefix is not None:
            prefix += '-'
            newstyle = {}
            for k in style:
                newstyle[k] = style[k]
            for k in style:
                if prefix in k:
                    newstyle[k.replace(prefix, '')] = style[k]
            style = newstyle

        style.setdefault('border-width', 1.5)
        style.setdefault('border-radius', 0)
        style.setdefault('border-radius-precision', .1)
        style.setdefault('draw-border', 0)
        style.setdefault('draw-background', 1)
        style.setdefault('draw-alpha-background', 0)
        style.setdefault('alpha-background', (1, 1, .5, .5))

        k = { 'pos': self._pos, 'size': self._size }

        linewidth = style.get('border-width')
        bordercolor = None
        if 'border-color' in style:
            bordercolor = style['border-color']

        roundrect = False
        if style['border-radius'] > 0:
            roundrect = True
            k.update({
                'radius': style['border-radius'],
                'precision': style['border-radius-precision']
            })

        # set the color of object
        obj.append(Color(*style['bg-color']))

        # add background object
        if style['draw-background']:
            if roundrect:
                obj.append(RoundedRectangle(**k))
            else:
                obj.append(Rectangle(**k))

        # add border object
        if style['draw-border']:
            if linewidth or bordercolor:
                obj.append(GraphicContextSave())
            if linewidth:
                obj.append(GraphicContextChange(linewidth=linewidth))
            if bordercolor:
                obj.append(Color(*bordercolor))
            if roundrect:
                obj.append(RoundedRectangle(type='line_loop', **k))
            else:
                obj.append(Rectangle(type='line_loop', **k))
            if linewidth or bordercolor:
                obj.append(GraphicContextRestore())
            # FIXME
            #if style['draw-alpha-background']:
            #    drawRoundedRectangleAlpha(alpha=style['alpha-background'], **k)

    def draw(self):
        if self._need_build:
            self.build()
            self._need_build = False
        for x in self._objects:
            x.draw()

    def _get_size(self):
        return self._size
    def _set_size(self, size):
        if self._size == size:
            return False
        self._size = size
        self._need_build = True
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
        self._need_build = True
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
        self._need_build = True
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
        self._need_build = True
        return True
    pos = property(lambda self: self._get_pos(),
                   lambda self, x: self._set_pos(x),
                   doc='Object position (x, y)')

    def _get_x(self):
        return self._pos[0]
    def _set_x(self, x):
        if x == self.pos[0]:
            return False
        self._pos = (x, self.y)
        self._need_build = True
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
        self._need_build = True
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

    def _get_state(self):
        return self._state
    def _set_state(self, x):
        if self._state == x:
            return
        self._state = x
        self._need_build = True
    state = property(
        lambda self: self._get_state(),
        lambda self, x: self._set_state(x),
        doc='Get/Set the css state to use'
    )

    def _get_prefix(self):
        return self._prefix
    def _set_prefix(self, x):
        if self._prefix == x:
            return
        self._prefix = x
        self._need_build = True
    prefix = property(
        lambda self: self._get_prefix(),
        lambda self, x: self._set_prefix(x),
        doc='Get/Set the css prefix to use'
    )

    def _get_style(self):
        return self._style
    def _set_style(self, x):
        if self._style == x:
            return
        self._style = x
        self._need_build = True
    style = property(
        lambda self: self._get_style(),
        lambda self, x: self._set_style(x),
        doc='Get/Set the css style to use (normally, its the widget.style property'
    )


class Canvas(object):
    '''Create a batch of graphic object.
    Can be use to store many graphic instruction, and call them for drawing.
    In a future, we'll do optimization on this, like merge vbo if possible.
    '''

    __slots__ = ('_batch', '_context')

    def __init__(self, **kwargs):
        self._batch = []
        self._context = default_context
        
    def add(self, graphic):
        '''Add a graphic element to draw'''
        #if isinstance(graphic, GraphicInstruction):
        #    raise Exception('Canvas accept only Graphic Instruction')
        self._batch.append(graphic)
        graphic.context = self._context
        return graphic

    def remove(self, graphic):
        '''Remove a graphic element from the list of objects'''
        try:
            self._batch.remove(graphic)
        except:
            pass

    def clear(self):
        '''Clear all the elements in canvas'''
        self._batch = []

    def draw(self):
        '''Draw all the canvas elements'''
        for x in self._batch:
            x.draw()

    def save(self):
        '''Push the current context to the stack'''
        self.add(GraphicContextSave())

    def restore(self):
        '''Restore the previous saved context'''
        self.add(GraphicContextRestore())

    @property
    def objects(self):
        return self._batch

    # facilities to create object
    def line(self, *largs, **kwargs):
        '''Create a Line() object, and add to the list.
        Check Line() for more information.'''
        return self.add(Line(*largs, **kwargs))

    def rectangle(self, *largs, **kwargs):
        '''Create a Rectangle() object, and add to the list.
        Check Rectangle() for more information.'''
        return self.add(Rectangle(*largs, **kwargs))

    def roundedRectangle(self, *largs, **kwargs):
        '''Create a RoundedRectangle() object, and add to the list.
        Check RoundedRectangle() for more information.'''
        return self.add(RoundedRectangle(*largs, **kwargs))

    def cssRectangle(self, *largs, **kwargs):
        '''Create a CSSRectangle() object, and add to the list.
        Check CSSRectangle() for more information.'''
        return self.add(CSSRectangle(*largs, **kwargs))

    def color(self, *largs, **kwargs):
        '''Create a Color() object, and add to the list.
        Check Color() for more information.'''
        return self.add(Color(*largs, **kwargs))

