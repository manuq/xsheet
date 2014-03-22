from gi.repository import GObject

from lib import tiledsurface

from cellist import CelList


class Cel(object):
    def __init__(self):
        self.surface = tiledsurface.GeglSurface()
        self.surface_node = self.surface.get_node()


class XSheet(GObject.GObject):
    __gsignals__ = {
        "frame-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
        "layer-changed": (GObject.SignalFlags.RUN_FIRST, None, []),
    }

    def __init__(self, frames_length=24, layers_length=3):
        GObject.GObject.__init__(self)

        self._frames_length = frames_length
        self.frame_idx = 0
        self.layer_idx = 0
        self.layers = [CelList() for x in range(layers_length)]
        self._play_hid = None

    def get_layers(self):
        return self.layers

    def go_to_frame(self, frame_idx):
        if frame_idx < 0 or frame_idx > self.frames_length-1 or frame_idx == self.frame_idx:
            return False

        self.frame_idx = frame_idx

        self.emit("frame-changed")
        return True

    def previous_frame(self, loop=False):
        if not loop:
            if self.frame_idx == 0:
                return False
        else:
            if self.frame_idx == 0:
                self.frame_idx = self.frames_length-1
                return True

        self.frame_idx -= 1

        self.emit("frame-changed")
        return True

    def next_frame(self, loop=False):
        if not loop:
            if self.frame_idx == self.frames_length-1:
                return False
        else:
            if self.frame_idx == self.frames_length-1:
                self.frame_idx = 0
                return True

        self.frame_idx += 1

        self.emit("frame-changed")
        return True

    def play(self):
        if self._play_hid != None:
            return False

        self._play_hid = GObject.timeout_add(42, self.next_frame, True)
        return True

    def stop(self):
        if self._play_hid == None:
            return False

        GObject.source_remove(self._play_hid)
        self._play_hid = None
        return True

    @property
    def is_playing(self):
        return self._play_hid != None

    def previous_layer(self):
        if self.layer_idx == 0:
            return False

        self.layer_idx -= 1

        self.emit("layer-changed")
        return True

    def next_layer(self):
        if self.layer_idx == self.layers_length-1:
            return False

        self.layer_idx += 1

        self.emit("layer-changed")
        return True

    def get_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        return self.layers[layer_idx][frame_idx]

    def get_cel_relative(self, frame_diff=0, layer_diff=0):
        frame_idx = self.frame_idx + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx][frame_idx]

    def get_cel_relative_by_cels(self, cel_diff, frame_diff=0, layer_diff=0):
        frame_idx = self.frame_idx + frame_diff
        layer_idx = self.layer_idx + layer_diff
        return self.layers[layer_idx].get_relative(frame_idx, cel_diff)

    def add_cel(self, frame_idx=None, layer_idx=None):
        if frame_idx is None:
            frame_idx = self.frame_idx

        if layer_idx is None:
            layer_idx = self.layer_idx

        if self.layers[layer_idx].is_unset_at(frame_idx):
            self.layers[layer_idx][frame_idx] = Cel()
            self.emit("frame-changed")

    @property
    def frames_length(self):
        return self._frames_length

    @property
    def layers_length(self):
        return len(self.layers)

    @property
    def frames_separation(self):
        return 6
