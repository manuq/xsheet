import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository import MyPaint

from applicationwindow import ApplicationWindow
from xsheet import XSheet
from canvasgraph import CanvasGraph
from canvaswidget import CanvasWidget
from xsheetwidget import XSheetWidget
from metronome import Metronome
from settings import get_settings
from settingsdialog import SettingsDialog
from giutils import set_base_value, get_base_value, set_base_color

_settings = get_settings()


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self)
        self.connect("activate", self._activate_cb)

    def setup(self):
        self._set_default_settings()

        self._xsheet = XSheet()

        self._canvas_graph = CanvasGraph(self._xsheet)
        self._metronome = Metronome(self._xsheet)

        self._canvas_widget = None
        self._xsheet_widget = None

        self._setup_icons()
        self._init_ui()

        if os.path.exists('test.zip'):
            self._xsheet.load('test.zip')

    def _activate_cb(self, app):
        self.setup()
        self._main_window.present()

    def _about_cb(self, action, state):
        print("About")

    def _quit_cb(self, action, state):
        self._quit()

    def _new_cb(self, action, state):
        self._xsheet.new()

    def _cut_cb(self, action, state):
        print("Cut")

    def _copy_cb(self, action, state):
        print("Copy")

    def _paste_cb(self, action, state):
        print("Paste")

    def _activate_toggle_cb(window, action, data=None):
        action.change_state(GLib.Variant('b', not action.get_state()))

    def _change_fullscreen_cb(self, action, state):
        if state.unpack():
            self._main_window.fullscreen()
        else:
            self._main_window.unfullscreen()
        action.set_state(state)

    def _change_timeline_cb(self, action, state):
        if state.unpack():
            self._xsheet_widget.show()
        else:
            self._xsheet_widget.hide()
        action.set_state(state)

    def _change_play_cb(self, action, state):
        if state.unpack():
            self._xsheet.play()
        else:
            self._xsheet.stop()
        action.set_state(state)

    def _change_onionskin_cb(self, action, state):
        if state.unpack():
            self._canvas_graph.set_onionskin_enabled(True)
        else:
            self._canvas_graph.set_onionskin_enabled(False)
        action.set_state(state)

    def _change_eraser_cb(self, action, state):
        if state.unpack():
            self._set_eraser_enabled(True)
        else:
            self._set_eraser_enabled(False)
        action.set_state(state)

    def _change_metronome_cb(self, action, state):
        if state.unpack():
            self._metronome.activate()
        else:
            self._metronome.deactivate()
        action.set_state(state)

    def _quit(self):
        self._xsheet.save('test.zip')
        Gtk.Application.quit(self)

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
        self._main_window = ApplicationWindow(self)

        def add_simple_actions(obj, actions):
            for action_name, action_cb in actions:
                action = Gio.SimpleAction(name=action_name)
                action.connect("activate", action_cb)
                obj.add_action(action)

        def add_toggle_actions(obj, actions):
            for action_name, activate_cb, change_cb, enabled in actions:
                action = Gio.SimpleAction.new_stateful(action_name, None,
                                                       GLib.Variant('b', enabled))
                action.connect("activate", activate_cb)
                action.connect("change-state", change_cb)
                obj.add_action(action)

        app_actions = (
            ("about", self._about_cb),
            ("quit", self._quit_cb),
        )
        add_simple_actions(self, app_actions)

        win_actions = (
            ("new", self._new_cb),
            ("cut", self._cut_cb),
            ("copy", self._copy_cb),
            ("paste", self._paste_cb),
        )
        add_simple_actions(self._main_window, win_actions)

        toggle_actions = (
            ("fullscreen", self._activate_toggle_cb, self._change_fullscreen_cb, False),
            ("timeline", self._activate_toggle_cb, self._change_timeline_cb, True),
            ("play", self._activate_toggle_cb, self._change_play_cb, False),
            ("onionskin", self._activate_toggle_cb, self._change_onionskin_cb, True),
            ("eraser", self._activate_toggle_cb, self._change_eraser_cb, False),
            ("metronome", self._activate_toggle_cb, self._change_metronome_cb, False),
        )
        add_toggle_actions(self._main_window, toggle_actions)

        non_menu_accels = (
            ("o", "win.onionskin", None),
            ("e", "win.eraser", None),
        )
        for accel, action_name, parameter in non_menu_accels:
            self.add_accelerator(accel, action_name, parameter)

        builder = Gtk.Builder()
        builder.add_from_file("menu.ui")
        self.set_app_menu(builder.get_object("app-menu"))
        self.set_menubar(builder.get_object("menubar"))

        self._main_window.connect("destroy", self._destroy_cb)
        self._main_window.connect("key-press-event", self._key_press_cb)
        self._main_window.connect("key-release-event", self._key_release_cb)
        self._main_window.show()

        top_box = Gtk.Grid()
        self._main_window.add(top_box)
        top_box.show()

        toolbar = Gtk.Toolbar()
        top_box.attach(toolbar, 0, 0, 2, 1)
        toolbar.show()

        play_button = Gtk.ToggleToolButton()
        play_button.set_action_name("win.play")
        play_button.set_stock_id("xsheet-play")
        toolbar.insert(play_button, -1)
        play_button.show()

        onionskin_button = Gtk.ToggleToolButton()
        onionskin_button.set_action_name("win.onionskin")
        onionskin_button.set_stock_id("xsheet-onionskin")
        toolbar.insert(onionskin_button, -1)
        onionskin_button.show()

        eraser_button = Gtk.ToggleToolButton()
        eraser_button.set_action_name("win.eraser")
        eraser_button.set_stock_id("xsheet-eraser")
        toolbar.insert(eraser_button, -1)
        eraser_button.show()

        remove_clear_button = Gtk.ToolButton()
        remove_clear_button.set_stock_id("xsheet-clear")
        remove_clear_button.connect("clicked", self._remove_clear_click_cb)
        toolbar.insert(remove_clear_button, -1)
        remove_clear_button.show()

        metronome_button = Gtk.ToggleToolButton()
        metronome_button.set_action_name("win.metronome")
        metronome_button.set_stock_id("xsheet-metronome")
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

        self._xsheet_widget = XSheetWidget(self._xsheet)
        top_box.attach(self._xsheet_widget, 1, 1, 1, 1)
        self._xsheet_widget.show()

    def _destroy_cb(self, *ignored):
        self._quit()

    def _set_eraser_enabled(self, enabled):
        _settings['eraser']['on'] = enabled

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
        if event.keyval == Gdk.KEY_BackSpace:
            self._xsheet.remove_clear()
        elif event.keyval == Gdk.KEY_Left:
            self._xsheet.previous_layer()
        elif event.keyval == Gdk.KEY_Right:
            self._xsheet.next_layer()
        elif event.keyval == Gdk.KEY_n:
            self._canvas_widget.view.props.scale -= 0.1
        elif event.keyval == Gdk.KEY_m:
            self._canvas_widget.view.props.scale += 0.1
