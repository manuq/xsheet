from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GeglGtk3 as GeglGtk

from settings import get_settings

_settings = get_settings()


class CanvasWidget(Gtk.EventBox):
    def __init__(self, xsheet, root_node):
        Gtk.EventBox.__init__(self)
        self.props.expand = True

        self._xsheet = xsheet
        self._xsheet.connect('frame-changed', self._xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self._xsheet_changed_cb)

        self._drawing = False
        self._panning = False
        self._last_event = None
        self._last_view_event = (0.0, 0.0, 0.0)  # (x, y, time)

        self._surface = None

        self._view = GeglGtk.View()
        self._view.set_autoscale_policy(GeglGtk.ViewAutoscale.DISABLED)
        self._view.override_background_color(Gtk.StateFlags.NORMAL,
                                             Gdk.RGBA(1, 1, 1, 1))
        self._view.set_node(root_node)
        self._view.set_size_request(800, 400)
        self.add(self._view)
        self._view.show()

        self.connect("motion-notify-event", self._motion_to_cb)
        self.connect("button-press-event", self._button_press_cb)
        self.connect("button-release-event", self._button_release_cb)

    @property
    def view(self):
        return self._view

    def _xsheet_changed_cb(self, xsheet):
        cel = self._xsheet.get_cel()
        if cel is not None:
            self._surface = cel.surface
        else:
            self._surface = None

    def _motion_to_cb(self, widget, event):
        (x, y, time) = event.x, event.y, event.time

        view_x = ((x + self._view.props.x) /
                  self._view.props.scale)
        view_y = ((y + self._view.props.y) /
                  self._view.props.scale)

        if self._drawing:
            if self._surface is None:
                return

            pressure = event.get_axis(Gdk.AxisUse.PRESSURE)
            if pressure is None:
                pressure = 0.5

            xtilt = event.get_axis(Gdk.AxisUse.XTILT)
            ytilt = event.get_axis(Gdk.AxisUse.YTILT)
            if xtilt is None or ytilt is None:
                xtilt = 0
                ytilt = 0

            dtime = (time - self._last_view_event[2])/1000.0

            self._surface.begin_atomic()
            brush = _settings['brush']
            brush.stroke_to(self._surface, view_x, view_y,
                            pressure, xtilt, ytilt, dtime)
            self._surface.end_atomic()

        elif self._panning:
            if self._last_event is not None:
                self._view.props.x -= x - self._last_event[0]
                self._view.props.y -= y - self._last_event[1]

            self._last_event = (x, y, time)

        self._last_view_event = (view_x, view_y, time)

    def _button_press_cb(self, widget, event):
        if event.button == 1:
            self._drawing = True

            if not self._xsheet.has_cel():
                self._xsheet.add_cel()

        elif event.button == 2:
            self._panning = True

    def _button_release_cb(self, widget, event):
        if event.button == 1:
            self._drawing = False
            _settings['brush'].reset()

        elif event.button == 2:
            self._panning = False
            self._last_event = None
