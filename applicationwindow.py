from gettext import gettext as _

from gi.repository import Gtk

from canvaswidget import CanvasWidget
from xsheetwidget import XSheetWidget
from settingsdialog import SettingsDialog


class ApplicationWindow(Gtk.ApplicationWindow):
    def __init__(self, application, xsheet, canvas_graph):
        Gtk.ApplicationWindow.__init__(self, application=application,
                                       default_width=640, default_height=480,
                                       title=_("xsheet"))
        self._xsheet = xsheet
        self._canvas_graph = canvas_graph

    def create_widgets(self):
        top_box = Gtk.Grid()
        self.add(top_box)
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
        remove_clear_button.set_action_name("win.remove_clear")
        remove_clear_button.set_stock_id("xsheet-clear")
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
        prev_layer_button.set_action_name("win.previous_layer")
        prev_layer_button.set_stock_id("xsheet-prev-layer")
        toolbar.insert(prev_layer_button, -1)
        prev_layer_button.show()

        next_layer_button = Gtk.ToolButton()
        next_layer_button.set_action_name("win.next_layer")
        next_layer_button.set_stock_id("xsheet-next-layer")
        toolbar.insert(next_layer_button, -1)
        next_layer_button.show()

        self._canvas_widget = CanvasWidget(
            self._xsheet, root_node=self._canvas_graph.root_node)
        top_box.attach(self._canvas_widget, 0, 1, 1, 1)
        self._canvas_widget.show()

        self._xsheet_widget = XSheetWidget(self._xsheet)
        top_box.attach(self._xsheet_widget, 1, 1, 1, 1)
        self._xsheet_widget.show()

    def get_canvas_widget(self):
        return self._canvas_widget

    def get_xsheet_widget(self):
        return self._xsheet_widget

    def _settings_click_cb(self, widget):
        dialog = SettingsDialog(widget.get_toplevel())
        dialog.show()
