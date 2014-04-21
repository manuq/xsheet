#!/usr/bin/env python

from gi.repository import Gegl
from gi.repository import Gtk

from application import Application

Gegl.init([])
Gtk.init([])

application = Application()
application.run()
