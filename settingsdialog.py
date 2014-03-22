from gettext import gettext as _

from gi.repository import Gtk


class SettingsDialog(Gtk.Dialog):
    SPACING = 5

    def __init__(self, top_window):
        Gtk.Dialog.__init__(self)
        self.set_transient_for(top_window)
        self.set_title(_("Settings"))
        self.props.modal = True

        notebook = Gtk.Notebook()
        notebook.set_size_request(400, 300)
        self.get_content_area().add(notebook)
        notebook.show()

        box = self._create_onionskin_settings()
        label = Gtk.Label()
        label.props.label = _("Onionskin")
        notebook.append_page(box, label)
        box.show()

        box = self._create_metronome_settings()
        label = Gtk.Label()
        label.props.label = _("Metronome")
        notebook.append_page(box, label)
        box.show()

    def _add_label(self, label_text, box, x, y, w=1, h=1):
        alignment = Gtk.Alignment.new(0.0, 0.0, 0.0, 1.0)
        alignment.props.hexpand = True
        alignment.set_padding(self.SPACING, self.SPACING,
                              self.SPACING, self.SPACING)
        box.attach(alignment, x, y, w, h)
        alignment.show()

        label = Gtk.Label()
        label.props.label = label_text
        alignment.add(label)
        label.show()

    def _add_control(self, widget, box, x, y, w=1, h=1, scale_x=0.0):
        alignment = Gtk.Alignment.new(0.0, 0.0, scale_x, 1.0)
        alignment.props.hexpand = True
        alignment.set_padding(self.SPACING, self.SPACING,
                              self.SPACING, self.SPACING)
        box.attach(alignment, x, y, w, h)
        alignment.show()

        alignment.add(widget)
        widget.show()

    def _create_onionskin_settings(self):

        grid = Gtk.Grid()
        grid.props.orientation = Gtk.Orientation.HORIZONTAL

        cur_row = 0

        self._add_label(_("Onionskin:"), grid, 0, cur_row)

        onionskin_switch = Gtk.Switch()
        onionskin_switch.props.active = True
        self._add_control(onionskin_switch, grid, 1, cur_row)

        cur_row += 1

        self._add_label(_("Type:"), grid, 0, cur_row)

        cels_radio = Gtk.RadioButton()
        cels_radio.props.label = _("By Cels")
        self._add_control(cels_radio, grid, 1, cur_row)

        cur_row += 1

        frames_radio = Gtk.RadioButton()
        frames_radio.props.label = _("By Frames")
        frames_radio.join_group(cels_radio)
        self._add_control(frames_radio, grid, 1, cur_row)

        cur_row += 1

        self._add_label(_("Previous range:"), grid, 0, cur_row)

        prev_adj = Gtk.Adjustment()
        prev_adj = Gtk.Adjustment(value=0, lower=0, upper=6,
                                  step_incr=1, page_incr=1, page_size=1)

        prev_scale = Gtk.Scale()
        prev_scale.set_adjustment(prev_adj)
        prev_scale.set_digits(0)
        prev_scale.props.orientation = Gtk.Orientation.HORIZONTAL
        self._add_control(prev_scale, grid, 1, cur_row, scale_x=1.0)

        cur_row += 1

        self._add_label(_("Nest range:"), grid, 0, cur_row)

        next_adj = Gtk.Adjustment()
        next_adj = Gtk.Adjustment(value=0, lower=0, upper=6,
                                  step_incr=1, page_incr=1, page_size=1)

        next_scale = Gtk.Scale()
        next_scale.set_adjustment(next_adj)
        next_scale.set_digits(0)
        next_scale.props.orientation = Gtk.Orientation.HORIZONTAL
        self._add_control(next_scale, grid, 1, cur_row, scale_x=1.0)

        cur_row += 1

        return grid

    def _create_metronome_settings(self):

        grid = Gtk.Grid()
        grid.props.orientation = Gtk.Orientation.HORIZONTAL

        cur_row = 0

        self._add_label(_("Metronome:"), grid, 0, cur_row)

        metronome_switch = Gtk.Switch()
        metronome_switch.props.active = True
        self._add_control(metronome_switch, grid, 1, cur_row)

        cur_row += 1

        self._add_label(_("Beats:"), grid, 0, cur_row)

        first_radio = None
        for i, beat in enumerate([_('6'), _('8'), _('12')]):
            radio = Gtk.RadioButton()
            radio.props.label = beat

            if i == 0:
                first_radio = radio
            else:
                radio.join_group(first_radio)

            self._add_control(radio, grid, 1, cur_row)

            cur_row += 1

        return grid
