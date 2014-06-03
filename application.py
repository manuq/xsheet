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
from metronome import Metronome
from settings import get_settings
from giutils import set_base_value, get_base_value, set_base_color

_settings = get_settings()


class Application(Gtk.Application):
    _INSTANCE = None

    def __init__(self):
        assert Application._INSTANCE is None
        Gtk.Application.__init__(self)
        Application._INSTANCE = self
        self.connect("activate", self._activate_cb)

    def setup(self):
        self._set_default_settings()

        self._xsheet = XSheet()
        self._canvas_graph = CanvasGraph(self._xsheet)
        self._metronome = Metronome(self._xsheet)

        self._setup_icons()
        self._init_ui()

        if os.path.exists('test.zip'):
            self._xsheet.load('test.zip')

    def _activate_cb(self, app):
        self.setup()
        self._main_window.present()

    def get_metronome(self):
        return self._metronome

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

    def _remove_clear_cb(self, action, state):
        self._xsheet.remove_clear()

    def _next_frame_cb(self, action, state):
        self._xsheet.next_frame()

    def _previous_frame_cb(self, action, state):
        self._xsheet.previous_frame()

    def _next_layer_cb(self, action, state):
        self._xsheet.next_layer()

    def _previous_layer_cb(self, action, state):
        self._xsheet.previous_layer()

    def _pan_view_up_cb(self, action, state):
        self._main_window.get_canvas_widget().pan_view("up")

    def _pan_view_down_cb(self, action, state):
        self._main_window.get_canvas_widget().pan_view("down")

    def _pan_view_left_cb(self, action, state):
        self._main_window.get_canvas_widget().pan_view("left")

    def _pan_view_right_cb(self, action, state):
        self._main_window.get_canvas_widget().pan_view("right")

    def _zoom_view_in_cb(self, action, state):
        self._main_window.get_canvas_widget().zoom_view(1)

    def _zoom_view_out_cb(self, action, state):
        self._main_window.get_canvas_widget().zoom_view(-1)

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
            self._main_window.get_xsheet_widget().show()
        else:
            self._main_window.get_xsheet_widget().hide()
        action.set_state(state)

    def _change_play_cb(self, action, state):
        if state.unpack():
            self._xsheet.play(_settings['play']['loop'])
        else:
            self._xsheet.stop()
        action.set_state(state)

    def _change_play_loop_cb(self, action, state):
        if state.unpack():
            _settings['play']['loop'] = True
        else:
            _settings['play']['loop'] = False
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

        _settings['play'] = {}
        _settings['play']['loop'] = False

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
        self._main_window = ApplicationWindow(self, self._xsheet,
                                              self._canvas_graph)

        def add_simple_actions(obj, actions):
            for action_name, action_cb in actions:
                action = Gio.SimpleAction(name=action_name)
                action.connect("activate", action_cb)
                obj.add_action(action)

        def add_toggle_actions(obj, actions):
            for action_name, change_cb, enabled in actions:
                action = Gio.SimpleAction.new_stateful(action_name, None,
                                                       GLib.Variant('b', enabled))
                action.connect("activate", self._activate_toggle_cb)
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
            ("remove_clear", self._remove_clear_cb),
            ("next_frame", self._next_frame_cb),
            ("previous_frame", self._previous_frame_cb),
            ("next_layer", self._next_layer_cb),
            ("previous_layer", self._previous_layer_cb),
            ("pan_view_up", self._pan_view_up_cb),
            ("pan_view_down", self._pan_view_down_cb),
            ("pan_view_left", self._pan_view_left_cb),
            ("pan_view_right", self._pan_view_right_cb),
            ("zoom_view_in", self._zoom_view_in_cb),
            ("zoom_view_out", self._zoom_view_out_cb),
        )
        add_simple_actions(self._main_window, win_actions)

        toggle_actions = (
            ("fullscreen", self._change_fullscreen_cb, False),
            ("timeline", self._change_timeline_cb, True),
            ("play", self._change_play_cb, False),
            ("play_loop", self._change_play_loop_cb, False),
            ("onionskin", self._change_onionskin_cb, True),
            ("eraser", self._change_eraser_cb, False),
            ("metronome", self._change_metronome_cb, False),
        )
        add_toggle_actions(self._main_window, toggle_actions)

        non_menu_accels = (
            ("o", "win.onionskin", None),
            ("e", "win.eraser", None),
            ("BackSpace", "win.remove_clear", None),
            ("<Control>Up", "win.previous_frame", None),
            ("<Control>Down", "win.next_frame", None),
            ("<Control>Left", "win.previous_layer", None),
            ("<Control>Right", "win.next_layer", None),
            ("<Control><Shift>Up", "win.pan_view_up", None),
            ("<Control><Shift>Down", "win.pan_view_down", None),
            ("<Control><Shift>Left", "win.pan_view_left", None),
            ("<Control><Shift>Right", "win.pan_view_right", None),
            ("comma", "win.zoom_view_out", None),
            ("period", "win.zoom_view_in", None),
        )
        for accel, action_name, parameter in non_menu_accels:
            self.add_accelerator(accel, action_name, parameter)

        builder = Gtk.Builder()
        builder.add_from_file("menu.ui")
        self.set_app_menu(builder.get_object("app-menu"))
        self.set_menubar(builder.get_object("menubar"))

        self._main_window.connect("destroy", self._destroy_cb)
        self._main_window.create_widgets()

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


def get_application():
    return Application._INSTANCE
