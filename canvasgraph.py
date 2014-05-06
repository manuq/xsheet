from gi.repository import Gegl
from settings import get_settings

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


class CanvasGraph(object):
    def __init__(self, xsheet):
        self._xsheet = xsheet
        self._xsheet.connect('frame-changed', self._xsheet_changed_cb)
        self._xsheet.connect('layer-changed', self._xsheet_changed_cb)

        self._graph = None
        self._nodes = {}
        self._create_graph()

    @property
    def nodes(self):
        return self._nodes

    @property
    def root_node(self):
        return self._nodes['root_node']

    def _create_graph(self):
        self._graph = Gegl.Node()

        root_node = self._graph.create_child("gegl:nop")
        self._nodes['root_node'] = root_node

        layer_overs = []
        for l in range(self._xsheet.layers_length):
            over = self._graph.create_child("gegl:over")
            layer_overs.append(over)

        self._nodes['layer_overs'] = layer_overs

        layer_overs[0].connect_to("output", root_node, "input")

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
        # print_connections(self._nodes['root_node'])

    def toggle_onionskin(self):
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

    def _xsheet_changed_cb(self, xsheet):
        self._update_graph()
