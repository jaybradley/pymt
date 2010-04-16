'''
Color picker: a simple color picker with 3 slider
'''

__all__ = ('MTColorPicker', )

from ....graphx import Rectangle, Color
from ...factory import MTWidgetFactory
from ..layout import MTBoxLayout
from ..scatter import MTScatterWidget
from ..slider import MTSlider

class MTColorPicker(MTScatterWidget):
    '''MTColorPicker is a implementation of a color picker using MTWidget

    :Parameters:
        `min` : int, default is 0
            Minimum value of slider
        `max` : int, default is 255
            Maximum value of slider
        `targets` : list, default is []
            List of widget to be affected by change
        `values` : list, default is [77, 77, 77]
            Default value of slider for RGB (0-255)

    :Events:
        `on_color`: tuple(r, g, b, a)
            Fired when the color change
    '''
    def __init__(self, **kwargs):
        kwargs.setdefault('min', 0)
        kwargs.setdefault('max', 255)
        kwargs.setdefault('values', [77, 77, 77])
        kwargs.setdefault('targets', [])

        super(MTColorPicker, self).__init__(**kwargs)

        self.register_event_type('on_color')

        self.size = (130, 290)
        self.targets = kwargs.get('targets')
        self._rectangle = Rectangle(10, 220, 110, 60)
        self._color = Color(0, 0, 0)

        # create sliders
        min, max = kwargs.get('min'), kwargs.get('max')
        size = (30, 200)
        self.sliders = [MTSlider(min=min, max=max, size=size, slidercolor=(1,0,0,1), cls='colorpicker-slider'),
                        MTSlider(min=min, max=max, size=size, slidercolor=(0,1,0,1), cls='colorpicker-slider'),
                        MTSlider(min=min, max=max, size=size, slidercolor=(0,0,1,1), cls='colorpicker-slider')]

        # add sliders to a vertical box layout
        vbox = MTBoxLayout(spacing=10, padding=10)
        for slider in self.sliders:
            slider.value = 77
            slider.push_handlers(on_value_change=self.update_color)
            vbox.add_widget(slider)
        self.add_widget(vbox)

        # update colors
        self.update_color()

    def draw(self):
        super(MTColorPicker, self).draw()
        self._color.color = self.current_color
        self._color.draw()
        self._rectangle.draw()

    def update_color(self, *largs):
        r = self.sliders[0].value / 255.
        g = self.sliders[1].value / 255.
        b = self.sliders[2].value / 255.
        for w in self.targets:
            w.color = (r, g, b, 1)
        self.current_color = (r, g, b, 1.0)
        self.dispatch_event('on_color', self.current_color)

    def on_color(self, color):
        pass

MTWidgetFactory.register('MTColorPicker', MTColorPicker)
