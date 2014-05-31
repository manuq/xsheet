import math
import cairo

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GeglGtk3 as GeglGtk

from settings import get_settings

_settings = get_settings()


CORNER_MARGIN = 10
TICK_STRONG_RADIUS = 10
TICK_SOFT_RADIUS = 5
TICK_SIZE = TICK_STRONG_RADIUS + CORNER_MARGIN

_PAN_STEP = 50
_ZOOM_STEP = 0.1


class CanvasView(GeglGtk.View):
    def __init__(self, xsheet):
        GeglGtk.View.__init__(self)
        self.set_autoscale_policy(GeglGtk.ViewAutoscale.DISABLED)
        self.override_background_color(Gtk.StateFlags.NORMAL,
                                       Gdk.RGBA(1, 1, 1, 1))

        self._xsheet = xsheet
        self._xsheet.connect('frame-changed', self._frame_changed_cb)

        self._tick_y = None
        self.connect('draw', self._draw_cb)

    def _frame_changed_cb(self, xsheet):
        self.queue_draw()

    def _draw_frame_number(self, widget, context):
        width = widget.get_allocated_width()

        context.save()
        context.select_font_face("sans-serif",
                                 cairo.FONT_SLANT_NORMAL,
                                 cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(17)

        text = "{0}".format(self._xsheet.current_frame + 1)
        x, y, w, h, dx, dy = context.text_extents(text)
        context.translate(width - w - x - CORNER_MARGIN,
                          h + CORNER_MARGIN)
        context.set_source_rgb(0, 0, 0)
        context.show_text(text)
        context.stroke()
        context.restore()

    def _get_tick_y(self, context):
        if self._tick_y is None:
            text_h = context.text_extents("0")[3]
            self._tick_y = text_h + TICK_SIZE + CORNER_MARGIN
        return self._tick_y

    def _draw_tick(self, widget, context, strong=False):
        width = widget.get_allocated_width()

        if strong:
            radius = TICK_STRONG_RADIUS
        else:
            radius = TICK_SOFT_RADIUS

        context.save()
        context.translate(width - TICK_SIZE, self._get_tick_y(context))
        context.set_source_rgb(0, 0, 0)
        context.arc(0, 0, radius, 0, 2 * math.pi)
        context.fill()
        context.restore()

    def _draw_cb(self, widget, context):
        self._draw_frame_number(widget, context)
        if self._xsheet.current_frame % 24 == 0:
            self._draw_tick(widget, context, True)
        elif self._xsheet.current_frame % self._xsheet.frames_separation == 0:
            self._draw_tick(widget, context, False)


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

        self._view = CanvasView(xsheet)
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

    def pan_view(self, direction):
        scale = self._view.props.scale
        if direction == "up":
            self._view.props.y -= _PAN_STEP * scale
        elif direction == "down":
            self._view.props.y += _PAN_STEP * scale
        elif direction == "left":
            self._view.props.x -= _PAN_STEP * scale
        elif direction == "right":
            self._view.props.x += _PAN_STEP * scale

    def zoom_view(self, direction):
        self._view.props.scale += _ZOOM_STEP * direction

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
