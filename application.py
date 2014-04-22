import os
from gettext import gettext as _

from gi.repository import Gegl
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import GeglGtk3 as GeglGtk
from gi.repository import MyPaint

from xsheet import XSheet
from xsheetwidget import XSheetWidget
from metronome import Metronome
from settingsdialog import SettingsDialog
from giutils import set_base_value, get_base_value
from giutils import set_base_color


def print_connections(node):
    def print_node(node, i=0, pad=''):
        print("  " * i + ' ' + pad + ' ' + node.get_operation())
        # FIMXE use gegl_operation_list_properties if that is in the
        # introspection bindings
        for input_pad in ['input', 'aux']:
            connected_node = node.get_producer(input_pad, None)
            if connected_node is not None:
                print_node(connected_node, i+1, input_pad)

    print_node(node)
    print("")


class Application(GObject.GObject):
    def __init__(self):
        GObject.GObject.__init__(self)

        self._brush = MyPaint.Brush()
        brush_def = open('../mypaint/brushes/classic/charcoal.myb').read()
        self._brush.from_string(brush_def)
        set_base_color(self._brush, (0.0, 0.0, 0.0))
        self._default_eraser = get_base_value(self._brush, "eraser")
        self._default_radius = get_base_value(self._brush, "radius_logarithmic")

        self._drawing = False
        self._panning = False
        self._last_event = None
        self._last_view_event = (0.0, 0.0, 0.0)  # (x, y, time)

        self._onionskin_on = True
        self._onionskin_by_cels = True
        self._onionskin_length = 3
        self._onionskin_falloff = 0.5

        self._view_widget = None

        self._eraser_on = False

        self._surface = None
        self._surface_node = None

        self._xsheet = XSheet(24 * 60)
        self._xsheet.connect('frame-changed', self._xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self._xsheet_changed_cb)

        self._metronome = Metronome(self._xsheet)

        self._update_surface()

        self._graph = None
        self._nodes = {}
        self._create_graph()
        self._init_ui()

    def run(self):
        return Gtk.main()

    def _create_graph(self):
        self._graph = Gegl.Node()

        main_over = self._graph.create_child("gegl:over")
        self._nodes['main_over'] = main_over

        layer_overs = []
        for l in range(self._xsheet.layers_length):
            over = self._graph.create_child("gegl:over")
            layer_overs.append(over)

        self._nodes['layer_overs'] = layer_overs

        layer_overs[0].connect_to("output", main_over, "input")

        for over, next_over in zip(layer_overs, layer_overs[1:]):
            next_over.connect_to("output", over, "input")

        background_node = self._graph.create_child("gegl:rectangle")
        background_node.set_property('color', Gegl.Color.new("#fff"))
        background_node.connect_to("output", layer_overs[-1], "input")
        self._nodes['background'] = background_node

        layer_nodes = []
        for l in range(self._xsheet.layers_length):
            nodes = {}
            current_cel_over = self._graph.create_child("gegl:over")
            current_cel_over.connect_to("output", layer_overs[l], "aux")
            nodes['current_cel_over'] = current_cel_over

            onionskin_overs = []
            onionskin_opacities = []
            for i in range(self._onionskin_length):
                over = self._graph.create_child("gegl:over")
                onionskin_overs.append(over)

                opacity = self._graph.create_child("gegl:opacity")
                opacity.set_property('value', 1 - self._onionskin_falloff)
                onionskin_opacities.append(opacity)

                over.connect_to("output", opacity, "input")

                for over, next_opacity in zip(onionskin_overs,
                                              onionskin_opacities[1:]):
                    next_opacity.connect_to("output", over, "aux")

                onionskin_opacities[0].connect_to("output", current_cel_over,
                                                  "aux")

            nodes['onionskin'] = {}
            nodes['onionskin']['overs'] = onionskin_overs
            nodes['onionskin']['opacities'] = onionskin_opacities
            layer_nodes.append(nodes)

        self._nodes['layer_nodes'] = layer_nodes

        self._update_graph()

    def _update_graph(self):
        get_cel = None
        if self._onionskin_by_cels:
            get_cel = self._xsheet.get_cel_relative_by_cels
        else:
            get_cel = self._xsheet.get_cel_relative

        for layer_idx in range(self._xsheet.layers_length):
            layer_nodes = self._nodes['layer_nodes'][layer_idx]
            cur_cel = self._xsheet.get_cel(layer_idx=layer_idx)

            if cur_cel is not None:
                cur_cel.surface_node.connect_to(
                    "output", layer_nodes['current_cel_over'], "input")
            else:
                layer_nodes['current_cel_over'].disconnect("input")

            if not self._onionskin_on:
                continue

            layer_diff = layer_idx - self._xsheet.layer_idx
            for i in range(self._onionskin_length):
                prev_cel = get_cel(-(i+1), layer_diff=layer_diff)
                over = layer_nodes['onionskin']['overs'][i]

                if prev_cel is not None:
                    prev_cel.surface_node.connect_to("output", over, "input")
                else:
                    over.disconnect("input")

        # debug
        # print_connections(self._nodes['main_over'])

    def _init_ui(self):
        window = Gtk.Window()
        window.props.title = _("XSheet")
        window.connect("destroy", self._destroy_cb)
        window.connect("key-press-event", self._key_press_cb)
        window.connect("key-release-event", self._key_release_cb)
        window.show()

        top_box = Gtk.Grid()
        window.add(top_box)
        top_box.show()

        toolbar = Gtk.Toolbar()
        top_box.attach(toolbar, 0, 0, 2, 1)
        toolbar.show()

        factory = Gtk.IconFactory()
        icon_names = ['xsheet-onionskin', 'xsheet-play', 'xsheet-eraser',
                      'xsheet-clear', 'xsheet-metronome', 'xsheet-settings',
                      'xsheet-prev-layer', 'xsheet-next-layer']
        for name in icon_names:
            filename = os.path.join('data', 'icons', name + '.svg')
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            iconset = Gtk.IconSet.new_from_pixbuf(pixbuf)
            factory.add(name, iconset)
            factory.add_default()

        play_button = Gtk.ToggleToolButton()
        play_button.set_stock_id("xsheet-play")
        play_button.connect("toggled", self._toggle_play_cb)
        toolbar.insert(play_button, -1)
        play_button.show()

        onionskin_button = Gtk.ToggleToolButton()
        onionskin_button.set_stock_id("xsheet-onionskin")
        onionskin_button.set_active(True)
        onionskin_button.connect("toggled", self._toggle_onionskin_cb)
        toolbar.insert(onionskin_button, -1)
        onionskin_button.show()

        eraser_button = Gtk.ToggleToolButton()
        eraser_button.set_stock_id("xsheet-eraser")
        eraser_button.connect("toggled", self._toggle_eraser_cb)
        toolbar.insert(eraser_button, -1)
        eraser_button.show()

        clear_button = Gtk.ToolButton()
        clear_button.set_stock_id("xsheet-clear")
        clear_button.connect("clicked", self._clear_click_cb)
        toolbar.insert(clear_button, -1)
        clear_button.show()

        metronome_button = Gtk.ToggleToolButton()
        metronome_button.set_stock_id("xsheet-metronome")
        metronome_button.connect("toggled", self._toggle_metronome_cb)
        toolbar.insert(metronome_button, -1)
        metronome_button.show()

        settings_button = Gtk.ToolButton()
        settings_button.set_stock_id("xsheet-settings")
        settings_button.connect("clicked", self._settings_click_cb)
        toolbar.insert(settings_button, -1)
        settings_button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar.insert(separator, -1)
        separator.show()

        prev_layer_button = Gtk.ToolButton()
        prev_layer_button.set_stock_id("xsheet-prev-layer")
        prev_layer_button.connect("clicked", self._prev_layer_click_cb)
        toolbar.insert(prev_layer_button, -1)
        prev_layer_button.show()

        next_layer_button = Gtk.ToolButton()
        next_layer_button.set_stock_id("xsheet-next-layer")
        next_layer_button.connect("clicked", self._next_layer_click_cb)
        toolbar.insert(next_layer_button, -1)
        next_layer_button.show()

        event_box = Gtk.EventBox()
        event_box.connect("motion-notify-event", self._motion_to_cb)
        event_box.connect("button-press-event", self._button_press_cb)
        event_box.connect("button-release-event", self._button_release_cb)
        top_box.attach(event_box, 0, 1, 1, 1)
        event_box.props.expand = True
        event_box.show()

        self._view_widget = GeglGtk.View()
        self._view_widget.set_node(self._nodes['main_over'])
        self._view_widget.set_autoscale_policy(GeglGtk.ViewAutoscale.DISABLED)
        self._view_widget.set_size_request(800, 400)
        self._view_widget.connect("size-allocate", self._size_allocate_cb)
        event_box.add(self._view_widget)
        self._view_widget.show()

        xsheet_widget = XSheetWidget(self._xsheet)
        top_box.attach(xsheet_widget, 1, 1, 1, 1)
        xsheet_widget.show()

    def _destroy_cb(self, *ignored):
        Gtk.main_quit()

    def _size_allocate_cb(self, widget, allocation):
        background_node = self._nodes['background']
        background_node.set_property("width", allocation.width)
        background_node.set_property("height", allocation.height)

    def _motion_to_cb(self, widget, event):
        (x, y, time) = event.x, event.y, event.time

        view_x = ((x + self._view_widget.props.x) /
                  self._view_widget.props.scale)
        view_y = ((y + self._view_widget.props.y) /
                  self._view_widget.props.scale)

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
            self._brush.stroke_to(self._surface, view_x, view_y,
                                  pressure, xtilt, ytilt, dtime)
            self._surface.end_atomic()

        elif self._panning:
            if self._last_event is not None:
                self._view_widget.props.x -= x - self._last_event[0]
                self._view_widget.props.y -= y - self._last_event[1]

            self._last_event = (x, y, time)

        self._last_view_event = (view_x, view_y, time)

    def _button_press_cb(self, widget, event):
        if event.button == 1:
            self._drawing = True

            if not self._xsheet.has_cel():
                self._xsheet.add_cel(self._graph)

        elif event.button == 2:
            self._panning = True

    def _button_release_cb(self, widget, event):
        if event.button == 1:
            self._drawing = False
            self._brush.reset()

        elif event.button == 2:
            self._panning = False
            self._last_event = None

    def _xsheet_changed_cb(self, xsheet):
        self._update_surface()
        self._update_graph()

    def _update_surface(self):
        cel = self._xsheet.get_cel()
        if cel is not None:
            self._surface = cel.surface
            self._surface_node = cel.surface_node
        else:
            self._surface = None
            self._surface_node = None

    def _toggle_play_stop(self):
        if self._xsheet.is_playing:
            self._xsheet.stop()
        else:
            self._xsheet.play()

    def _toggle_play_cb(self, widget):
        self._toggle_play_stop()

    def _toggle_onionskin(self):
        self._onionskin_on = not self._onionskin_on

        for layer_idx in range(self._xsheet.layers_length):
            layer_nodes = self._nodes['layer_nodes'][layer_idx]
            onionskin_opacities = layer_nodes['onionskin']['opacities']
            current_cel_over = layer_nodes['current_cel_over']
            if self._onionskin_on:
                onionskin_opacities[0].connect_to("output", current_cel_over,
                                                  "aux")
            else:
                current_cel_over.disconnect("aux")

        self._update_graph()

    def _toggle_onionskin_cb(self, widget):
        self._toggle_onionskin()

    def _toggle_eraser(self):
        self._eraser_on = not self._eraser_on

        eraser_setting = MyPaint.BrushSetting.SETTING_ERASER
        radius_setting = MyPaint.BrushSetting.SETTING_RADIUS_LOGARITHMIC
        if self._eraser_on:
            set_base_value(self._brush, "eraser", 1.0)
            set_base_value(self._brush, "radius_logarithmic",
                           self._default_radius * 3)
        else:
            set_base_value(self._brush, "eraser", self._default_eraser)
            set_base_value(self._brush, "radius_logarithmic",
                           self._default_radius)

    def _toggle_eraser_cb(self, widget):
        self._toggle_eraser()

    def _clear_click_cb(self, widget):
        self._xsheet.clear_cel()

    def _toggle_metronome(self):
        if self._metronome.is_on():
            self._metronome.activate()
        else:
            self._metronome.deactivate()

    def _toggle_metronome_cb(self, widget):
        self._toggle_metronome()

    def _settings_click_cb(self, widget):
        dialog = SettingsDialog(widget.get_toplevel())
        dialog.show()

    def _prev_layer_click_cb(self, widget):
        self._xsheet.previous_layer()

    def _next_layer_click_cb(self, widget):
        self._xsheet.next_layer()

    def _key_press_cb(self, widget, event):
        scale = self._view_widget.props.scale

        if event.keyval == Gdk.KEY_Up:
            self._xsheet.previous_frame()
        elif event.keyval == Gdk.KEY_Down:
            self._xsheet.next_frame()
        elif event.keyval == Gdk.KEY_h:
            self._view_widget.props.x -= 10 * scale
        elif event.keyval == Gdk.KEY_l:
            self._view_widget.props.x += 10 * scale
        elif event.keyval == Gdk.KEY_k:
            self._view_widget.props.y -= 10 * scale
        elif event.keyval == Gdk.KEY_j:
            self._view_widget.props.y += 10 * scale

    def _key_release_cb(self, widget, event):
        if event.keyval == Gdk.KEY_p:
            self._toggle_play_stop()
        elif event.keyval == Gdk.KEY_o:
            self._toggle_onionskin()
        elif event.keyval == Gdk.KEY_e:
            self._toggle_eraser()
        elif event.keyval == Gdk.KEY_BackSpace:
            self._xsheet.clear_cel()
        elif event.keyval == Gdk.KEY_Left:
            self._xsheet.previous_layer()
        elif event.keyval == Gdk.KEY_Right:
            self._xsheet.next_layer()
        elif event.keyval == Gdk.KEY_n:
            self._view_widget.props.scale -= 0.1
        elif event.keyval == Gdk.KEY_m:
            self._view_widget.props.scale += 0.1
