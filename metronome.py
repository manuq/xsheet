import os
from gi.repository import Gst

class Metronome(object):
    def __init__(self, xsheet):
        Gst.init([])
        self._xsheet = xsheet
        self._frame_changed_hid = None

        self._player = Gst.ElementFactory.make("playbin", "tick")
        fakesink = Gst.ElementFactory.make("fakesink", "fake")
        self._player.props.video_sink = fakesink
        self._player.get_bus().add_signal_watch()

        directory = os.path.dirname(os.path.abspath(__file__))
        self._soft_tick_sound_path = os.path.join(directory, 'data', 'sounds', 'soft_tick.wav')
        self._strong_tick_sound_path = os.path.join(directory, 'data', 'sounds', 'strong_tick.wav')

    def is_on(self):
        return self._frame_changed_hid is None

    def activate(self):
        if self._frame_changed_hid is not None:
            return False

        self._frame_changed_hid = self._xsheet.connect('frame-changed', self.xsheet_changed_cb)
        return True

    def deactivate(self):
        if self._frame_changed_hid is None:
            return False

        self._xsheet.disconnect(self._frame_changed_hid)
        self._frame_changed_hid = None
        return True

    def tick(self, sound_path):
        self._player.set_state(Gst.State.NULL)

        bus = self._player.get_bus()
        bus.connect('message::eos', self.eos_cb)
        bus.connect('message::error', self.error_cb)

        self._player.props.uri = 'file://' + sound_path
        self._player.set_state(Gst.State.PLAYING)

    def eos_cb(self, bus, message):
        bus.disconnect_by_func(self.eos_cb)
        self._player.set_state(Gst.State.NULL)

    def error_cb(bus, message):
        err, debug = message.parse_error()
        print('ERROR play_pipe: %s %s' % (err, debug))
        self._player.set_state(Gst.State.NULL)

    def xsheet_changed_cb(self, xsheet):
        if xsheet.frame_idx % 24 == 0:
            self.tick(self._strong_tick_sound_path)
        elif xsheet.frame_idx % xsheet.frames_separation == 0:
            self.tick(self._soft_tick_sound_path)
