import math
import cairo

from gi.repository import Gtk
from gi.repository import Gdk

NUMBERS_WIDTH = 45.0
NUMBERS_MARGIN = 5.0
CEL_WIDTH = 55.0
CEL_HEIGHT = 25.0

MIN_ZOOM = 0
MAX_ZOOM = 4
ZOOM_STEP = 0.05

SOFT_LINE_WIDTH = 0.2
STRONG_LINE_WIDTH = 0.5
SECONDS_LINE_WIDTH = 1.0
ELEMENT_CEL_RADIUS = 3.0
CLEAR_RADIUS = 4

FRAMES = 24 * 60


def _get_cairo_color(gdk_color):
    return (float(gdk_color.red), float(gdk_color.green),
            float(gdk_color.blue))


class _XSheetDrawing(Gtk.DrawingArea):
    def __init__(self, xsheet, adjustment):
        Gtk.DrawingArea.__init__(self)

        self.props.vexpand = True

        self._background_color = _get_cairo_color(
            self.get_style_context().lookup_color('theme_bg_color')[1])
        self._background_color_high = _get_cairo_color(
            self.get_style_context().lookup_color('theme_bg_color')[1])
        self._background_color_high = \
            [color * 1.05 for color in self._background_color_high]
        self._selected_color = _get_cairo_color(
            self.get_style_context().lookup_color(
                'theme_selected_bg_color')[1])
        self._fg_color = _get_cairo_color(
            self.get_style_context().lookup_color('theme_fg_color')[1])
        self._selected_fg_color = _get_cairo_color(
            self.get_style_context().lookup_color(
                'theme_selected_fg_color')[1])

        self._xsheet = xsheet
        self._adjustment = adjustment
        self._pixbuf = None
        self._offset = 0
        self._first_visible_frame = 0
        self._last_visible_frames = 0
        self._zoom_factor = 1.0
        self._scrubbing = False
        self._panning = False
        self._pan_start = 0
        self._zooming = False
        self._zoom_start = 0
        self._zoom_start_factor = None

        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.SCROLL_MASK)

        self.connect('draw', self._draw_cb)
        self.connect('configure-event', self._configure_event_cb)
        self.connect("motion-notify-event", self._motion_notify_cb)
        self.connect("button-press-event", self._button_press_cb)
        self.connect("button-release-event", self._button_release_cb)
        self.connect("scroll-event", self._scroll_cb)

        self._xsheet.connect('frame-changed', self._xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self._xsheet_changed_cb)
        self._adjustment.connect("value-changed", self._scroll_changed_cb)

        widget_width = NUMBERS_WIDTH + CEL_WIDTH * self._xsheet.layers_length
        self.set_size_request(widget_width, -1)

    @property
    def virtual_height(self):
        return FRAMES * CEL_HEIGHT * self._zoom_factor

    def _configure(self):
        width = self.get_allocated_width()
        height = self.props.parent.get_allocated_height()

        if self._pixbuf is not None:
            self._pixbuf.finish()
            self._pixbuf = None

        self._pixbuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        self._adjustment.props.step_increment = \
            CEL_HEIGHT / self.virtual_height
        self._adjustment.props.page_increment = \
            height / self.virtual_height / 2
        self._adjustment.props.page_size = height / self.virtual_height
        self._calculate_visible_frames()

    def _configure_event_cb(self, widget, event, data=None):
        self._configure()
        return False

    def _xsheet_changed_cb(self, xsheet):
        if (self._xsheet.current_frame < self._first_visible_frame):
            self._adjustment.props.value -= self._adjustment.props.page_size

        if (self._xsheet.current_frame >= self._last_visible_frames):
            self._adjustment.props.value += self._adjustment.props.page_size

        self.queue_draw()

    def _update_offset(self):
        dy = self.virtual_height - self.get_allocated_height()
        dx = self._adjustment.props.upper - self._adjustment.props.page_size
        self._offset = -1 * self._adjustment.props.value * dy / dx
        self._calculate_visible_frames()

    def _calculate_visible_frames(self):
        self._first_visible_frame = \
            int(-1 * self._offset / CEL_HEIGHT / self._zoom_factor)
        self._last_visible_frames = (
            self._first_visible_frame + int(math.ceil(
                self.get_allocated_height() / CEL_HEIGHT / self._zoom_factor)))

    def _scroll_changed_cb(self, adjustment):
        self._update_offset()
        self.queue_draw()

    def _draw_cb(self, widget, context):
        if self._pixbuf is None:
            print('No buffer to paint')
            return False

        drawing_context = cairo.Context(self._pixbuf)

        drawing_context.translate(0, self._offset)

        self._draw_background(drawing_context)
        self._draw_selected_row(drawing_context)
        self._draw_grid(drawing_context)
        self._draw_numbers(drawing_context)
        self._draw_elements(drawing_context)

        context.set_source_surface(self._pixbuf, 0, 0)
        context.paint()

    def _draw_background(self, context):
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

    def _draw_selected_row(self, context):
        skip_draw = (self._xsheet.current_frame < self._first_visible_frame or
                     self._xsheet.current_frame > self._last_visible_frames)
        if skip_draw:
            return

        y = self._xsheet.current_frame * CEL_HEIGHT * self._zoom_factor
        width = context.get_target().get_width()
        context.set_source_rgb(*self._selected_color)
        context.rectangle(0, y, width, CEL_HEIGHT * self._zoom_factor)
        context.fill()

    def _draw_grid_horizontal(self, context):
        pass_frame_lines = False
        pass_separation_lines = False
        if self._zoom_factor * CEL_HEIGHT < 5:
            pass_frame_lines = True
        if self._zoom_factor * CEL_HEIGHT * self._xsheet.frames_separation < 5:
            pass_separation_lines = True

        line_factor = 1
        if self._zoom_factor < 0.2:
            line_factor = 0.5

        width = context.get_target().get_width()
        context.set_source_rgb(*self._fg_color)
        for i in range(self._first_visible_frame,
                       self._last_visible_frames + 1):
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

    def _draw_grid_vertical(self, context):
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

    def _draw_grid(self, context):
        self._draw_grid_vertical(context)
        self._draw_grid_horizontal(context)

    def _draw_numbers(self, context):
        context.select_font_face("sans-serif",
                                 cairo.FONT_SLANT_NORMAL,
                                 cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(13)

        draw_step = 1
        if self._zoom_factor < 0.0075:
            draw_step = 128
        elif self._zoom_factor < 0.015:
            draw_step = 64
        elif self._zoom_factor < 0.03:
            draw_step = 32
        elif self._zoom_factor < 0.06:
            draw_step = 16
        elif self._zoom_factor < 0.12:
            draw_step = 8
        elif self._zoom_factor < 0.24:
            draw_step = 4
        elif self._zoom_factor < 0.48:
            draw_step = 2

        for i in range(self._first_visible_frame,
                       self._last_visible_frames + 1):
            if i % draw_step != 0:
                continue

            if i == self._xsheet.current_frame:
                context.set_source_rgb(*self._selected_fg_color)
            else:
                context.set_source_rgb(*self._fg_color)

            text = str(i+1).zfill(3)
            x, y, width, height, dx, dy = context.text_extents(text)
            context.move_to(NUMBERS_WIDTH - width - NUMBERS_MARGIN,
                            (i * CEL_HEIGHT * self._zoom_factor) +
                            CEL_HEIGHT * self._zoom_factor / 2 + height/2)
            context.show_text(text)
            context.stroke()

    def _draw_cel(self, context, layer_idx, frame, repeat):
        context.set_line_width(STRONG_LINE_WIDTH)
        if frame == self._xsheet.current_frame:
            context.set_source_rgb(*self._selected_fg_color)
        else:
            context.set_source_rgb(*self._fg_color)

        context.arc(NUMBERS_WIDTH + CEL_WIDTH * (layer_idx + 0.5),
                    CEL_HEIGHT * self._zoom_factor * (frame + 0.5),
                    ELEMENT_CEL_RADIUS, 0, 2 * math.pi)
        if repeat:
            context.stroke()
        else:
            context.fill()

    def _draw_clear(self, context, layer_idx, frame):
        context.set_line_width(STRONG_LINE_WIDTH * 3)
        if frame == self._xsheet.current_frame:
            context.set_source_rgb(*self._selected_fg_color)
        else:
            context.set_source_rgb(*self._fg_color)

        center_x = NUMBERS_WIDTH + CEL_WIDTH * (layer_idx + 0.5)
        center_y = CEL_HEIGHT * self._zoom_factor * (frame + 0.5)

        context.move_to(center_x - CLEAR_RADIUS, center_y - CLEAR_RADIUS)
        context.line_to(center_x + CLEAR_RADIUS, center_y + CLEAR_RADIUS)
        context.stroke()
        context.move_to(center_x - CLEAR_RADIUS, center_y + CLEAR_RADIUS)
        context.line_to(center_x + CLEAR_RADIUS, center_y - CLEAR_RADIUS)
        context.stroke()

    def _draw_elements(self, context):
        for layer_idx in range(self._xsheet.layers_length):
            layer = self._xsheet.get_layers()[layer_idx]
            first = self._first_visible_frame
            last = self._last_visible_frames

            for frame in range(first, last):
                if layer.get_type_at(frame) == 'repeat clear':
                    continue
                elif layer.get_type_at(frame) == 'clear':
                    self._draw_clear(context, layer_idx, frame)
                elif layer.get_type_at(frame) == 'cel':
                    self._draw_cel(context, layer_idx, frame, repeat=False)
                elif layer.get_type_at(frame) == 'repeat cel':
                    self._draw_cel(context, layer_idx, frame, repeat=True)

    def _get_frame_from_point(self, x, y):
        return int((y - self._offset) / CEL_HEIGHT / self._zoom_factor)

    def _button_press_cb(self, widget, event):
        if event.button == 1:
            self._scrubbing = True
        elif event.button == 2:
            self._panning = True
            self._pan_start = event.y
        elif event.button == 3:
            self._zooming = True
            self._zoom_start = event.y
            self._zoom_start_factor = self._zoom_factor

    def _button_release_cb(self, widget, event):
        if not self._scrubbing and not self._panning and not self._zooming:
            frame = self._get_frame_from_point(event.x, event.y)
            self._xsheet.go_to_frame(frame)

        if self._scrubbing:
            self._scrubbing = False
        if self._panning:
            self._panning = False
            self._pan_start = 0
        if self._zooming:
            self._zooming = False
            self._zoom_start = 0
            self._zoom_start_factor = None

    def _motion_notify_cb(self, widget, event):
        x, y = event.x, event.y
        frame = self._get_frame_from_point(event.x, event.y)
        if self._scrubbing:
            self._xsheet.go_to_frame(frame)
        elif self._panning:
            dy = (self._pan_start - event.y) / self.virtual_height
            self._adjustment.props.value += dy
            self._pan_start = event.y
        elif self._zooming:
            self._zoom_by_offset(self._zoom_start - event.y)
            self._zoom_start = event.y

    def _zoom_by_direction(self, direction):
        new_factor = (self._zoom_factor +
                      ZOOM_STEP * self._zoom_factor * direction)
        self._set_zoom_factor(new_factor)

    def _zoom_by_offset(self, offset):
        if offset > 0:
            return self._zoom_by_direction(1)
        elif offset < 0:
            return self._zoom_by_direction(-1)

    def _set_zoom_factor(self, new_factor):
        if new_factor <= MIN_ZOOM or new_factor >= MAX_ZOOM:
            return False

        self._zoom_factor = new_factor
        self._configure()
        self._update_offset()
        self.queue_draw()

        return True

    def _scroll_cb(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self._zoom_by_direction(1)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self._zoom_by_direction(-1)

        else:
            increment = self._adjustment.props.step_increment
            if event.direction == Gdk.ScrollDirection.UP:
                self._adjustment.props.value -= increment
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self._adjustment.props.value += increment


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
