from gettext import gettext as _

from gi.repository import Gtk

class ApplicationWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        Gtk.ApplicationWindow.__init__(self, application=application,
                                       default_width=640, default_height=480,
                                       title=_("xsheet"))
