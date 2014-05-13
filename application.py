import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import MyPaint

from xsheet import XSheet
from canvasgraph import CanvasGraph
from canvaswidget import CanvasWidget
from xsheetwidget import XSheetWidget
from metronome import Metronome
from settings import get_settings
from settingsdialog import SettingsDialog
from giutils import set_base_value, get_base_value, set_base_color

_settings = get_settings()


class Application(GObject.GObject):
    def __init__(self):
        GObject.GObject.__init__(self)

        self._set_default_settings()

        self._xsheet = XSheet(24 * 60)

        self._canvas_graph = CanvasGraph(self._xsheet)
        self._metronome = Metronome(self._xsheet)

        self._canvas_widget = None
        self._xsheet_widget = None

        self._setup_icons()
        self._init_ui()

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

    def _setup_icons(self):
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
            self._xsheet, root_node=self._canvas_graph.root_node)
        top_box.attach(self._canvas_widget, 0, 1, 1, 1)
        self._canvas_widget.show()

        self._canvas_widget.view.connect("size-allocate",
                                         self._size_allocate_cb)

        self._xsheet_widget = XSheetWidget(self._xsheet)
        top_box.attach(self._xsheet_widget, 1, 1, 1, 1)
        self._xsheet_widget.show()

    def _destroy_cb(self, *ignored):
        Gtk.main_quit()

    def _size_allocate_cb(self, widget, allocation):
        background_node = self._canvas_graph.nodes['background']
        background_node.set_property("width", allocation.width)
        background_node.set_property("height", allocation.height)

    def _toggle_play_stop(self):
        if self._xsheet.is_playing:
            self._xsheet.stop()
        else:
            self._xsheet.play()

    def _toggle_play_cb(self, widget):
        self._toggle_play_stop()

    def _toggle_onionskin_cb(self, widget):
        self._canvas_graph.toggle_onionskin()

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
        elif event.keyval == Gdk.KEY_s:
            self._xsheet.save()
        elif event.keyval == Gdk.KEY_o:
            self._xsheet.load()
        elif event.keyval == Gdk.KEY_q:
            Gtk.main_quit()
        elif event.keyval == Gdk.KEY_o:
            self._canvas_graph.toggle_onionskin()
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
