#!/usr/bin/env python

# FIXME use libmymaint through introspection
import sys
sys.path.append("../mypaint")

from gi.repository import Gegl
from gi.repository import Gtk

from application import Application

Gegl.init([])
Gtk.init([])

application = Application()
application.run()
