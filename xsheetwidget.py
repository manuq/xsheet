import math
import cairo

from gi.repository import Gtk
from gi.repository import Gdk

NUMBERS_WIDTH = 45.0
NUMBERS_MARGIN = 5.0
CEL_WIDTH = 55.0
CEL_HEIGHT = 25.0

MIN_ZOOM = 0.01
MAX_ZOOM = 4.0
ZOOM_STEP = 0.05

SOFT_LINE_WIDTH = 0.2
STRONG_LINE_WIDTH = 0.5
SECONDS_LINE_WIDTH = 1.0
ELEMENT_CEL_RADIUS = 3.0

def _get_cairo_color(gdk_color):
    return (float(gdk_color.red), float(gdk_color.green), float(gdk_color.blue))


class _XSheetDrawing(Gtk.DrawingArea):
    def __init__(self, xsheet, adjustment):
        Gtk.DrawingArea.__init__(self)

        self.props.vexpand = True

        self._background_color = _get_cairo_color(self.get_style_context().lookup_color('theme_bg_color')[1])
        self._background_color_high = _get_cairo_color(self.get_style_context().lookup_color('theme_bg_color')[1])
        self._background_color_high = [color * 1.05 for color in self._background_color_high]
        self._selected_color = _get_cairo_color(self.get_style_context().lookup_color('theme_selected_bg_color')[1])
        self._fg_color = _get_cairo_color(self.get_style_context().lookup_color('theme_fg_color')[1])
        self._selected_fg_color = _get_cairo_color(self.get_style_context().lookup_color('theme_selected_fg_color')[1])

        self._xsheet = xsheet
        self._adjustment = adjustment
        self._pixbuf = None
        self._offset = 0
        self._first_visible_frame = 0
        self._last_visible_frames = 0
        self._zoom_factor = 1.0
        self._scrubbing = False
        self._dragging = False
        self._drag_start = 0
        self._zooming = False
        self._zoom_start = 0
        self._zoom_start_factor = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.SCROLL_MASK)

        self.connect('draw', self.draw_cb)
        self.connect('configure-event', self.configure_event_cb)
        self.connect("motion-notify-event", self.motion_notify_cb)
        self.connect("button-press-event", self.button_press_cb)
        self.connect("button-release-event", self.button_release_cb)
        self.connect("scroll-event", self.scroll_cb)

        self._xsheet.connect('frame-changed', self.xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self.xsheet_changed_cb)
        self._adjustment.connect("value-changed", self.scroll_changed_cb)

        widget_width = NUMBERS_WIDTH + CEL_WIDTH * self._xsheet.layers_length
        self.set_size_request(widget_width, -1)

    @property
    def virtual_height(self):
        return self._xsheet.frames_length * CEL_HEIGHT * self._zoom_factor

    def configure(self):
        width = self.get_allocated_width()
        height = self.props.parent.get_allocated_height()

        if self._pixbuf is not None:
            self._pixbuf.finish()
            self._pixbuf = None

        self._pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        self._adjustment.props.step_increment = CEL_HEIGHT / self.virtual_height
        self._adjustment.props.page_increment = height / self.virtual_height / 2
        self._adjustment.props.page_size = height / self.virtual_height
        self._calculate_visible_frames()

    def configure_event_cb(self, widget, event, data=None):
        self.configure()
        return False

    def xsheet_changed_cb(self, xsheet):
        if (self._xsheet.frame_idx < self._first_visible_frame):
            self._adjustment.props.value -= self._adjustment.props.page_size

        if (self._xsheet.frame_idx >= self._last_visible_frames):
            self._adjustment.props.value += self._adjustment.props.page_size

        self.queue_draw()

    def update_offset(self):
        dy = self.virtual_height - self.get_allocated_height()
        dx = self._adjustment.props.upper - self._adjustment.props.page_size
        self._offset = -1 * self._adjustment.props.value * dy / dx
        self._calculate_visible_frames()

    def _calculate_visible_frames(self):
        self._first_visible_frame = int(-1 * self._offset / CEL_HEIGHT / self._zoom_factor)
        self._last_visible_frames = (self._first_visible_frame +
                                     int(math.ceil(self.get_allocated_height() / CEL_HEIGHT / self._zoom_factor)))

    def scroll_changed_cb(self, adjustment):
        self.update_offset()
        self.queue_draw()

    def draw_cb(self, widget, context):
        if self._pixbuf is None:
            print('No buffer to paint')
            return False

        drawing_context = cairo.Context(self._pixbuf)

        drawing_context.translate(0, self._offset)

        self.draw_background(drawing_context)
        self.draw_selected_row(drawing_context)
        self.draw_grid(drawing_context)
        self.draw_numbers(drawing_context)
        self.draw_elements(drawing_context)

        context.set_source_surface(self._pixbuf, 0, 0)
        context.paint()

    def draw_background(self, context):
        width = self.get_allocated_width()
        height = -1 * self._offset + self.get_allocated_height()
        current_layer_x = NUMBERS_WIDTH + self._xsheet.layer_idx * CEL_WIDTH

        context.set_source_rgb(*self._background_color)
        context.rectangle(0, 0, current_layer_x, height)
        context.rectangle(current_layer_x + CEL_WIDTH, 0, width, height)
        context.fill()

        context.set_source_rgb(*self._background_color_high)
        context.rectangle(current_layer_x, 0, CEL_WIDTH, height)
        context.fill()

    def draw_selected_row(self, context):
        if (self._xsheet.frame_idx < self._first_visible_frame or
            self._xsheet.frame_idx > self._last_visible_frames):
            return

        y = self._xsheet.frame_idx * CEL_HEIGHT * self._zoom_factor
        width = context.get_target().get_width()
        context.set_source_rgb(*self._selected_color)
        context.rectangle(0, y, width, CEL_HEIGHT * self._zoom_factor)
        context.fill()

    def draw_grid_horizontal(self, context):
        pass_frame_lines = False
        pass_separation_lines = False
        if self._zoom_factor * CEL_HEIGHT < 5:
            pass_frame_lines = True
        if self._zoom_factor * CEL_HEIGHT * self._xsheet.frames_separation < 5:
            pass_separation_lines = True

        line_factor = 1
        if  self._zoom_factor < 0.2:
            line_factor = 0.5

        width = context.get_target().get_width()
        context.set_source_rgb(*self._fg_color)
        for i in range(self._first_visible_frame, self._last_visible_frames + 1):
            if i % 24 == 0:
                context.set_line_width(SECONDS_LINE_WIDTH)
            elif i % self._xsheet.frames_separation == 0:
                if pass_separation_lines:
                    continue
                context.set_line_width(STRONG_LINE_WIDTH * line_factor)
            else:
                if pass_frame_lines:
                    continue
                context.set_line_width(SOFT_LINE_WIDTH * line_factor)

            y = i * CEL_HEIGHT * self._zoom_factor
            context.move_to(0, y)
            context.line_to(width, y)
            context.stroke()

    def draw_grid_vertical(self, context):
        context.set_source_rgb(*self._fg_color)
        context.set_line_width(SOFT_LINE_WIDTH)

        y1 = self._offset
        y2 = -1 * self._offset + self.get_allocated_height()

        context.move_to(NUMBERS_WIDTH, y1)
        context.line_to(NUMBERS_WIDTH, y2)

        for i in range(self._xsheet.layers_length):
            x = NUMBERS_WIDTH + i * CEL_WIDTH
            context.move_to(x, y1)
            context.line_to(x, y2)
        context.stroke()

    def draw_grid(self, context):
        self.draw_grid_vertical(context)
        self.draw_grid_horizontal(context)

    def draw_numbers(self, context):
        context.select_font_face("sans-serif",
                                 cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(13)

        draw_step = 1
        if self._zoom_factor < 0.15:
            draw_step = 8
        elif  self._zoom_factor < 0.2:
            draw_step = 4
        elif self._zoom_factor < 0.6:
            draw_step = 2

        for i in range(self._first_visible_frame, self._last_visible_frames + 1):
            if i % draw_step != 0:
                continue

            if i == self._xsheet.frame_idx:
                context.set_source_rgb(*self._selected_fg_color)
            else:
                context.set_source_rgb(*self._fg_color)

            text = str(i+1).zfill(3)
            x, y, width, height, dx, dy = context.text_extents(text)
            context.move_to(NUMBERS_WIDTH - width - NUMBERS_MARGIN,
                            (i * CEL_HEIGHT * self._zoom_factor) + CEL_HEIGHT * self._zoom_factor /2 + height/2)
            context.show_text(text)

    def _draw_cel(self, context, layer_idx, frame_idx, cel):
        if frame_idx == self._xsheet.frame_idx:
            context.set_source_rgb(*self._selected_fg_color)
        else:
            context.set_source_rgb(*self._fg_color)

        context.arc(NUMBERS_WIDTH + CEL_WIDTH * (layer_idx + 0.5),
                    CEL_HEIGHT * self._zoom_factor * (frame_idx + 0.5),
                    ELEMENT_CEL_RADIUS, 0, 2 * math.pi);
        context.fill()

    def draw_elements(self, context):
        for layer_idx in range(self._xsheet.layers_length):
            layer = self._xsheet.get_layers()[layer_idx]
            # FIXME cut the result of layer.get_changing_frames() to
            # the visible frames.
            for frame_idx in layer.get_changing_frames():
                cel = layer[frame_idx]
                if cel is not None:
                    self._draw_cel(context, layer_idx, frame_idx, cel)

    def _get_frame_from_point(self, x, y):
        return int((y - self._offset) / CEL_HEIGHT / self._zoom_factor)

    def button_press_cb(self, widget, event):
        if event.button == 1:
            self._scrubbing = True
        elif event.button == 2:
            self._dragging = True
            self._drag_start = event.y
        elif event.button == 3:
            self._zooming = True
            self._zoom_start = event.y
            self._zoom_start_factor = self._zoom_factor

    def button_release_cb(self, widget, event):
        if not self._scrubbing and not self._dragging and not self._zooming:
            frame_idx = self._get_frame_from_point(event.x, event.y)
            self._xsheet.go_to_frame(frame_idx)

        if self._scrubbing:
            self._scrubbing = False
        if self._dragging:
            self._dragging = False
            self._drag_start = 0
        if self._zooming:
            self._zooming = False
            self._zoom_start = 0
            self._zoom_start_factor = None

    def motion_notify_cb(self, widget, event):
        x, y = event.x, event.y
        frame_idx = self._get_frame_from_point(event.x, event.y)
        if self._scrubbing:
            self._xsheet.go_to_frame(frame_idx)
        elif self._dragging:
            dy = (self._drag_start - event.y) / self.virtual_height
            self._adjustment.props.value += dy
            self._drag_start = event.y
        elif self._zooming:
            self.zoom_by_offset(self._zoom_start - event.y)

    def zoom_by_direction(self, direction):
        self.zoom(self._zoom_factor + ZOOM_STEP * direction)

    def zoom_by_offset(self, offset):
        self.zoom(self._zoom_start_factor - 0.01 * offset)

    def zoom(self, value):
        if value < MIN_ZOOM or value > MAX_ZOOM:
            return False

        self._zoom_factor = value
        self.configure()
        self.update_offset()
        self.queue_draw()

        return True

    def scroll_cb(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_by_direction(1)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_by_direction(-1)

        else:
            if event.direction == Gdk.ScrollDirection.UP:
                self._adjustment.props.value -= self._adjustment.props.step_increment
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self._adjustment.props.value += self._adjustment.props.step_increment


class XSheetWidget(Gtk.Grid):
    def __init__(self, xsheet):
        Gtk.Grid.__init__(self)
        self.props.orientation = Gtk.Orientation.HORIZONTAL

        adjustment = Gtk.Adjustment()
        adjustment.props.lower = 0
        adjustment.props.upper = 1
        adjustment.props.page_size = 0.1

        drawing = _XSheetDrawing(xsheet, adjustment)
        self.add(drawing)
        drawing.show()

        scrollbar = Gtk.VScrollbar(adjustment=adjustment)
        self.add(scrollbar)
        scrollbar.show()
