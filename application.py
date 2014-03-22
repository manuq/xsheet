import os
from gettext import gettext as _

from gi.repository import Gegl
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import GeglGtk3 as GeglGtk

from lib import brush

from xsheet import XSheet
from xsheetwidget import XSheetWidget
from metronome import Metronome
from settingsdialog import SettingsDialog

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

        brush_file = open('../mypaint/brushes/classic/charcoal.myb')
        brush_info = brush.BrushInfo(brush_file.read())
        brush_info.set_color_rgb((0.0, 0.0, 0.0))
        self.default_eraser = brush_info.get_base_value("eraser")
        self.default_radius = brush_info.get_base_value("radius_logarithmic")
        self.brush = brush.Brush(brush_info)

        self.button_pressed = False
        self.last_event = (0.0, 0.0, 0.0) # (x, y, time)

        self.onionskin_on = True
        self.onionskin_by_cels = True
        self.onionskin_length = 3
        self.onionskin_falloff = 0.5

        self.eraser_on = False
        self.force_add_cel = True

        self.surface = None
        self.surface_node = None

        self.xsheet = XSheet(24 * 60)
        self.xsheet.connect('frame-changed', self.xsheet_changed_cb)
        self.xsheet.connect('layer-changed', self.xsheet_changed_cb)

        self.metronome = Metronome(self.xsheet)

        self.update_surface()

        self.nodes = {}
        self.create_graph()
        self.init_ui()


    def create_graph(self):
        self.graph = Gegl.Node()

        main_over = self.graph.create_child("gegl:over")
        self.nodes['main_over'] = main_over

        layer_overs = []
        for l in range(self.xsheet.layers_length):
            over = self.graph.create_child("gegl:over")
            layer_overs.append(over)

        self.nodes['layer_overs'] = layer_overs

        layer_overs[0].connect_to("output", main_over, "input")

        for over, next_over in zip(layer_overs, layer_overs[1:]):
            next_over.connect_to("output", over, "input")

        background_node = self.graph.create_child("gegl:rectangle")
        background_node.set_property('color', Gegl.Color.new("#fff"))
        background_node.connect_to("output", layer_overs[-1], "input")
        self.nodes['background'] = background_node

        layer_nodes = []
        for l in range(self.xsheet.layers_length):
            nodes = {}
            current_cel_over = self.graph.create_child("gegl:over")
            current_cel_over.connect_to("output", layer_overs[l], "aux")
            nodes['current_cel_over'] = current_cel_over

            onionskin_overs = []
            onionskin_opacities = []
            for i in range(self.onionskin_length):
                over = self.graph.create_child("gegl:over")
                onionskin_overs.append(over)

                opacity = self.graph.create_child("gegl:opacity")
                opacity.set_property('value', 1 - self.onionskin_falloff)
                onionskin_opacities.append(opacity)

                over.connect_to("output", opacity, "input")

                for over, next_opacity in zip(onionskin_overs, onionskin_opacities[1:]):
                    next_opacity.connect_to("output", over, "aux")

                onionskin_opacities[0].connect_to("output", current_cel_over, "aux")

            nodes['onionskin'] = {}
            nodes['onionskin']['overs'] = onionskin_overs
            nodes['onionskin']['opacities'] = onionskin_opacities
            layer_nodes.append(nodes)

        self.nodes['layer_nodes'] = layer_nodes

        self.update_graph()

    def update_graph(self):
        get_cel = None
        if self.onionskin_by_cels:
            get_cel = self.xsheet.get_cel_relative_by_cels
        else:
            get_cel = self.xsheet.get_cel_relative

        for layer_idx in range(self.xsheet.layers_length):
            layer_nodes = self.nodes['layer_nodes'][layer_idx]
            cur_cel = self.xsheet.get_cel(layer_idx=layer_idx)

            if cur_cel is not None:
                cur_cel.surface_node.connect_to("output", layer_nodes['current_cel_over'], "input")
            else:
                layer_nodes['current_cel_over'].disconnect("input")

            if not self.onionskin_on:
                continue

            layer_diff = layer_idx - self.xsheet.layer_idx
            for i in range(self.onionskin_length):
                prev_cel = get_cel(-(i+1), layer_diff=layer_diff)
                over = layer_nodes['onionskin']['overs'][i]

                if prev_cel is not None:
                    prev_cel.surface_node.connect_to("output", over, "input")
                else:
                    over.disconnect("input")

        # debug
        # print_connections(self.nodes['main_over'])

    def init_ui(self):
        window = Gtk.Window()
        window.props.title = _("XSheet")
        window.connect("destroy", self.destroy_cb)
        window.connect("size-allocate", self.size_allocate_cb)
        window.connect("key-press-event", self.key_press_cb)
        window.connect("key-release-event", self.key_release_cb)
        window.show()

        top_box = Gtk.Grid()
        window.add(top_box)
        top_box.show()

        toolbar = Gtk.Toolbar()
        top_box.attach(toolbar, 0, 0, 2, 1)
        toolbar.show()

        factory = Gtk.IconFactory()
        icon_names = ['xsheet-onionskin', 'xsheet-play', 'xsheet-eraser',
                      'xsheet-metronome', 'xsheet-settings']
        for name in icon_names:
            filename = os.path.join('data', 'icons', name + '.svg')
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            iconset = Gtk.IconSet.new_from_pixbuf(pixbuf)
            factory.add(name, iconset)
            factory.add_default()

        play_button = Gtk.ToggleToolButton()
        play_button.set_stock_id("xsheet-play")
        play_button.connect("toggled", self.toggle_play_cb)
        toolbar.insert(play_button, -1)
        play_button.show()

        onionskin_button = Gtk.ToggleToolButton()
        onionskin_button.set_stock_id("xsheet-onionskin")
        onionskin_button.set_active(True)
        onionskin_button.connect("toggled", self.toggle_onionskin_cb)
        toolbar.insert(onionskin_button, -1)
        onionskin_button.show()

        eraser_button = Gtk.ToggleToolButton()
        eraser_button.set_stock_id("xsheet-eraser")
        eraser_button.connect("toggled", self.toggle_eraser_cb)
        toolbar.insert(eraser_button, -1)
        eraser_button.show()

        metronome_button = Gtk.ToggleToolButton()
        metronome_button.set_stock_id("xsheet-metronome")
        metronome_button.connect("toggled", self.toggle_metronome_cb)
        toolbar.insert(metronome_button, -1)
        metronome_button.show()

        settings_button = Gtk.ToolButton()
        settings_button.set_stock_id("xsheet-settings")
        settings_button.connect("clicked", self.settings_click_cb)
        toolbar.insert(settings_button, -1)
        settings_button.show()

        event_box = Gtk.EventBox()
        event_box.connect("motion-notify-event", self.motion_to_cb)
        event_box.connect("button-press-event", self.button_press_cb)
        event_box.connect("button-release-event", self.button_release_cb)
        top_box.attach(event_box, 0, 1, 1, 1)
        event_box.props.expand = True
        event_box.show()

        view_widget = GeglGtk.View()
        view_widget.set_node(self.nodes['main_over'])
        view_widget.set_autoscale_policy(GeglGtk.ViewAutoscale.DISABLED)
        view_widget.set_size_request(800, 400)
        event_box.add(view_widget)
        view_widget.show()

        xsheet_widget = XSheetWidget(self.xsheet)
        top_box.attach(xsheet_widget, 1, 1, 1, 1)
        xsheet_widget.show()

    def run(self):
        return Gtk.main()

    def destroy_cb(self, *ignored):
        Gtk.main_quit()

    def size_allocate_cb(self, widget, allocation):
        background_node = self.nodes['background']
        background_node.set_property("width", allocation.width)
        background_node.set_property("height", allocation.height)

    def motion_to_cb(self, widget, event):
        # FIXME, better disconnect
        if self.surface is None:
            return

        (x, y, time) = event.x, event.y, event.time

        pressure = event.get_axis(Gdk.AxisUse.PRESSURE)
        if pressure is None:
            pressure = 0.5

        xtilt = event.get_axis(Gdk.AxisUse.XTILT)
        ytilt = event.get_axis(Gdk.AxisUse.YTILT)
        if xtilt is None or ytilt is None:
            xtilt = 0
            ytilt = 0

        dtime = (time - self.last_event[2])/1000.0
        if self.button_pressed:
            self.surface.begin_atomic()
            self.brush.stroke_to(self.surface.backend, x, y, pressure, xtilt, ytilt, dtime)
            self.surface.end_atomic()

        self.last_event = (x, y, time)

    def button_press_cb(self, widget, event):
        if self.force_add_cel:
            self.xsheet.add_cel()

        self.button_pressed = True

    def button_release_cb(self, widget, event):
        self.button_pressed = False
        self.brush.reset()

    def xsheet_changed_cb(self, xsheet):
        self.update_surface()
        self.update_graph()

    def update_surface(self):
        cel = self.xsheet.get_cel()
        if cel is not None:
            self.surface = cel.surface
            self.surface_node = cel.surface_node
        else:
            self.surface = None
            self.surface_node = None

    def toggle_play_stop(self):
        if self.xsheet.is_playing:
            self.xsheet.stop()
        else:
            self.xsheet.play()

    def toggle_play_cb(self, widget):
        self.toggle_play_stop()

    def toggle_onionskin(self):
        self.onionskin_on = not self.onionskin_on

        for layer_idx in range(self.xsheet.layers_length):
            layer_nodes = self.nodes['layer_nodes'][layer_idx]
            onionskin_opacities = layer_nodes['onionskin']['opacities']
            current_cel_over = layer_nodes['current_cel_over']
            if self.onionskin_on:
                onionskin_opacities[0].connect_to("output", current_cel_over, "aux")
            else:
                current_cel_over.disconnect("aux")

        self.update_graph()

    def toggle_onionskin_cb(self, widget):
        self.toggle_onionskin()

    def toggle_eraser(self):
        self.eraser_on = not self.eraser_on

        if self.eraser_on:
            self.brush.brushinfo.set_base_value("eraser", 1.0)
            self.brush.brushinfo.set_base_value("radius_logarithmic",
                                                self.default_radius * 3)
        else:
            self.brush.brushinfo.set_base_value("eraser", self.default_eraser)
            self.brush.brushinfo.set_base_value("radius_logarithmic",
                                                self.default_radius)

    def toggle_eraser_cb(self, widget):
        self.toggle_eraser()

    def toggle_metronome(self):
        if self.metronome.is_on():
            self.metronome.activate()
        else:
            self.metronome.deactivate()

    def toggle_metronome_cb(self, widget):
        self.toggle_metronome()

    def settings_click_cb(self, widget):
        dialog = SettingsDialog(widget.get_toplevel())
        dialog.show()

    def key_press_cb(self, widget, event):
        if event.keyval == Gdk.KEY_Up:
            self.xsheet.previous_frame()
        elif event.keyval == Gdk.KEY_Down:
            self.xsheet.next_frame()

    def key_release_cb(self, widget, event):
        if event.keyval == Gdk.KEY_c:
            self.xsheet.add_cel()
        elif event.keyval == Gdk.KEY_p:
            self.toggle_play_stop()
        elif event.keyval == Gdk.KEY_o:
            self.toggle_onionskin()
        elif event.keyval == Gdk.KEY_e:
            self.toggle_eraser()
        elif event.keyval == Gdk.KEY_BackSpace:
            # FIXME, needs to be done in gegl backend
            if self.surface is not None:
                self.surface.clear()
        elif event.keyval == Gdk.KEY_Left:
            self.xsheet.previous_layer()
        elif event.keyval == Gdk.KEY_Right:
            self.xsheet.next_layer()
