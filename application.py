import os
from gettext import gettext as _

from gi.repository import Gegl
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import MyPaint

from xsheet import XSheet
from canvaswidget import CanvasWidget
from xsheetwidget import XSheetWidget
from metronome import Metronome
from settings import get_settings
from settingsdialog import SettingsDialog
from giutils import set_base_value, get_base_value, set_base_color

_settings = get_settings()

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

        self._set_default_settings()

        self._canvas_widget = None
        self._xsheet_widget = None

        self._graph = None
        self._nodes = {}
        self._surface_node = None

        self._xsheet = XSheet(24 * 60)
        self._xsheet.connect('frame-changed', self._xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self._xsheet_changed_cb)

        self._metronome = Metronome(self._xsheet)

        self._create_graph()
        self._init_ui()
        self._update_surface()

    def run(self):
        return Gtk.main()

    def _set_default_settings(self):
        brush = MyPaint.Brush()
        brush_def = open('../mypaint/brushes/classic/charcoal.myb').read()
        brush.from_string(brush_def)
        set_base_color(brush, (0.0, 0.0, 0.0))
        self._default_eraser = get_base_value(brush, "eraser")
        self._default_radius = get_base_value(brush, "radius_logarithmic")
        _settings['brush'] = brush

        _settings['onionskin'] = {}
        _settings['onionskin']['on'] = True
        _settings['onionskin']['by_cels'] = True
        _settings['onionskin']['length'] = 3
        _settings['onionskin']['falloff'] = 0.5

        _settings['eraser'] = {}
        _settings['eraser']['on'] = False

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
            for i in range(_settings['onionskin']['length']):
                over = self._graph.create_child("gegl:over")
                onionskin_overs.append(over)

                opacity = self._graph.create_child("gegl:opacity")
                falloff = _settings['onionskin']['falloff']
                opacity.set_property('value', 1 - falloff)
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

        self._xsheet.set_graph(self._graph)
        self._update_graph()

    def _update_graph(self):
        get_cel = None
        if _settings['onionskin']['by_cels']:
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

            if not _settings['onionskin']['on']:
                continue

            layer_diff = layer_idx - self._xsheet.layer_idx
            for i in range(_settings['onionskin']['length']):
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

        remove_clear_button = Gtk.ToolButton()
        remove_clear_button.set_stock_id("xsheet-clear")
        remove_clear_button.connect("clicked", self._remove_clear_click_cb)
        toolbar.insert(remove_clear_button, -1)
        remove_clear_button.show()

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

        self._canvas_widget = CanvasWidget(
            self._xsheet, root_node=self._nodes['main_over'])
        top_box.attach(self._canvas_widget, 0, 1, 1, 1)
        self._canvas_widget.show()

        self._canvas_widget.view.connect("size-allocate", self._size_allocate_cb)

        self._xsheet_widget = XSheetWidget(self._xsheet)
        top_box.attach(self._xsheet_widget, 1, 1, 1, 1)
        self._xsheet_widget.show()

    def _destroy_cb(self, *ignored):
        Gtk.main_quit()

    def _size_allocate_cb(self, widget, allocation):
        background_node = self._nodes['background']
        background_node.set_property("width", allocation.width)
        background_node.set_property("height", allocation.height)

    def _xsheet_changed_cb(self, xsheet):
        self._update_surface()
        self._update_graph()

    def _update_surface(self):
        cel = self._xsheet.get_cel()
        if cel is not None:
            self._canvas_widget.set_surface(cel.surface)
            self._surface_node = cel.surface_node
        else:
            self._canvas_widget.set_surface(None)
            self._surface_node = None

    def _toggle_play_stop(self):
        if self._xsheet.is_playing:
            self._xsheet.stop()
        else:
            self._xsheet.play()

    def _toggle_play_cb(self, widget):
        self._toggle_play_stop()

    def _toggle_onionskin(self):
        _settings['onionskin']['on'] = not _settings['onionskin']['on']

        for layer_idx in range(self._xsheet.layers_length):
            layer_nodes = self._nodes['layer_nodes'][layer_idx]
            onionskin_opacities = layer_nodes['onionskin']['opacities']
            current_cel_over = layer_nodes['current_cel_over']
            if _settings['onionskin']['on']:
                onionskin_opacities[0].connect_to("output", current_cel_over,
                                                  "aux")
            else:
                current_cel_over.disconnect("aux")

        self._update_graph()

    def _toggle_onionskin_cb(self, widget):
        self._toggle_onionskin()

    def _toggle_eraser(self):
        _settings['eraser']['on'] = not _settings['eraser']['on']

        brush = _settings['brush']
        if _settings['eraser']['on']:
            set_base_value(brush, "eraser", 1.0)
            set_base_value(brush, "radius_logarithmic",
                           self._default_radius * 3)
        else:
            set_base_value(brush, "eraser", self._default_eraser)
            set_base_value(brush, "radius_logarithmic",
                           self._default_radius)

    def _toggle_eraser_cb(self, widget):
        self._toggle_eraser()

    def _remove_clear_click_cb(self, widget):
        self._xsheet.remove_clear()

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
        scale = self._canvas_widget.view.props.scale

        if event.keyval == Gdk.KEY_Up:
            self._xsheet.previous_frame()
        elif event.keyval == Gdk.KEY_Down:
            self._xsheet.next_frame()
        elif event.keyval == Gdk.KEY_h:
            self._canvas_widget.view.props.x -= 10 * scale
        elif event.keyval == Gdk.KEY_l:
            self._canvas_widget.view.props.x += 10 * scale
        elif event.keyval == Gdk.KEY_k:
            self._canvas_widget.view.props.y -= 10 * scale
        elif event.keyval == Gdk.KEY_j:
            self._canvas_widget.view.props.y += 10 * scale

    def _key_release_cb(self, widget, event):
        if event.keyval == Gdk.KEY_p:
            self._toggle_play_stop()
        elif event.keyval == Gdk.KEY_o:
            self._toggle_onionskin()
        elif event.keyval == Gdk.KEY_e:
            self._toggle_eraser()
        elif event.keyval == Gdk.KEY_BackSpace:
            self._xsheet.remove_clear()
        elif event.keyval == Gdk.KEY_Left:
            self._xsheet.previous_layer()
        elif event.keyval == Gdk.KEY_Right:
            self._xsheet.next_layer()
        elif event.keyval == Gdk.KEY_n:
            self._canvas_widget.view.props.scale -= 0.1
        elif event.keyval == Gdk.KEY_m:
            self._canvas_widget.view.props.scale += 0.1
        elif event.keyval == Gdk.KEY_Tab:
            if self._xsheet_widget.is_visible():
                self._xsheet_widget.hide()
            else:
                self._xsheet_widget.show()
