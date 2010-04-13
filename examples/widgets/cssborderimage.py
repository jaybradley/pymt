from pymt import *
import os

image = os.path.join(os.path.dirname(__file__), 'css', 'whiteButton.png')
css_add_sheet('''
#btn2 {
    border-image: "%s" 12 12 12 12;
}
''' % image)

m = MTButton(label='Button 1')
m2 = MTButton(label='Button 2', id='btn2')

box = MTBoxLayout(spacing=50, padding=50)
box.add_widget(m)
box.add_widget(m2)

runTouchApp(box)
