'''
MTProxyPDF: a PDF viewer inside an inner window. The PDF is rendered to PNGs by ImageMagick.
'''

__all__ = ('MTProxyPDF', )

from pymt.ui.widgets.composed.innerwindow import MTInnerWindow
from pymt.ui.widgets.klist import MTList
from pymt.ui.widgets.layout import MTGridLayout
from pymt.ui.widgets.image import MTImage
from pymt import getClock
from pymt import pymt_data_dir
from pymt import Image
import tempfile
import os
import platform
import commands
import sys
import re
import threading 
import subprocess

class MTProxyPDF(MTInnerWindow):
    '''Uses Imagemagick to render PDF pages to PNG images which are placed in a GridLayout inside a MTList.'''

    # TODO: Should check timestamps to pick up newer versions of the PDF.
    # TODO: Should do something basic to allow for different resolutions such as [low, medium, high] based on the current size of the widget.
    # TODO: Consider other backends that don't rely on imagemagick.
    # TODO: Constrain resizing to keep the PDF's aspect ratio.
    # TODO: Possibly weight the pages so that when the velocity drops below a certain value they current page should move to be shown fully.
    # TODO: Kill off rendering jobs that are no longer needed. i.e. if the user skips passed three pages they shouldn't be rendered.
    
    def __init__(self, **kwargs):
        super(MTProxyPDF, self).__init__(**kwargs)
        
        self.pages_to_replace = {}

        self.filename = kwargs.get('filename')
        self.cache_directory = os.path.join(tempfile.gettempdir(), "pymt_ProxyPDF_cache") + os.sep
        if(not os.path.exists(self.cache_directory)):
            os.mkdir(self.cache_directory)
        
        self.number_of_pages = countPages(self.filename)
        #print "Number of pages = ", self.number_of_pages
        
        self.total_page_height = self.number_of_pages * self.height
        
        self.page_list = MTList(size=self.size, do_x=False)
        
        self.page_layout = MTGridLayout(cols=1)
        self.page_list.add_widget(self.page_layout)
        
        # add existing pages or loading page
        for page_number in xrange(self.number_of_pages):
            page_filename = self.cache_directory + self.filename.replace(os.sep, '_') + str(page_number) + '.png'
            if(not os.path.exists(page_filename)): # TODO check timetamps. If the file was modified later than the cached page then need to redo the page
                #page_filename = 'resources/graphics/loading.png'
                page_filename = os.path.join(pymt_data_dir, 'loader.png')
            aPage = MTImage(page_filename)
            aPage.size = (self.width, self.height)
            self.page_layout.add_widget(aPage)
        
        self.add_widget(self.page_list)
        
    def on_resize(self, new_width, new_height):                
        self.page_layout.size = (new_width, new_height)
        self.page_list.size = (new_width, new_height)
        for page in self.page_layout.children:
            page.size = (new_width, new_height)
        
        self.total_page_height = self.number_of_pages * self.height
        
    def draw(self):
        self.current_page = max(1, min(self.number_of_pages, int(abs((self.page_list.content_y + self.total_page_height) / self.height))))
        page_filename = self.cache_directory + self.filename.replace(os.sep, '_') + str(self.current_page - 1) + '.png'
        
        # check if there's a file for the current page number already. If not then render one using ImageMagick's convert function
        if(not os.path.exists(page_filename)): # TODO check timestamps. If the file was modified later than the cached page then need to redo the page
            if(not self.page_layout.children[self.current_page - 1].child in self.pages_to_replace):
                self.pages_to_replace[self.page_layout.children[self.current_page - 1].child] = RenderPDFPageInThread(self, page_filename, self.width, self.height, self.filename, self.current_page, self.page_layout.children[self.current_page - 1].child)
                self.pages_to_replace[self.page_layout.children[self.current_page - 1].child].start()

    def replace_image(self, page_number, new_image):
        del self.pages_to_replace[self.page_layout.children[page_number - 1].child]
        self.page_layout.children[page_number - 1].child = new_image



class RenderPDFPageInThread(threading.Thread):
  def __init__(self, caller, page_filename, width, height, filename, page_number, image_to_replace):
    super(RenderPDFPageInThread, self).__init__()
    self.page_filename = page_filename
    self.filename = filename
    self.page_number = page_number
    self.image_to_replace = image_to_replace
    self.width = width
    self.height = height
    self.process = None
    self.caller = caller
    
  def run(self):
    self.process = subprocess.Popen(['convert', '-density', '100', self.filename + '[' + str(self.page_number -1) + ']', self.page_filename], shell=False)
    getClock().schedule_interval(self.check_render, 1)

  def check_render(self, delta):
    if(self.process.poll() == 0): # process finished
        new_image = Image(self.page_filename)
        new_image.size = (self.width, self.height)
        #self.image_to_replace = new_image
        self.caller.replace_image(self.page_number, new_image)
        return False # stop checking


# Count PDF pages in pure python from http://code.activestate.com/recipes/496837/
rxcountpages = re.compile(r"$\s*/Type\s*/Page[/\s]", re.MULTILINE|re.DOTALL)

def countPages(filename):
    data = file(filename,"rb").read()
    return len(rxcountpages.findall(data))

