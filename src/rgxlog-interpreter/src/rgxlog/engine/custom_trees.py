import networkx as nx


class NetxTree(nx.OrderedDiGraph):

    def __init__(self, root=0):
        super().__init__()
        self.__root = root

    def set_root(self, root):
        self.__root = root

    def get_root(self):
        return self.__root

    def pretty(self, indent_str='  '):
        return ''.join(self._pretty(self.__root, 0, indent_str))

    def _pretty(self, node, level, indent_str):
        children = list(self.successors(node))
        data_attr = nx.get_node_attributes(self, "data")
        value_attr = nx.get_node_attributes(self, "value")
        if len(children) == 1 and children[0] not in data_attr:
            return [indent_str * level, data_attr[node], '\t', '%s' % (value_attr[children[0]],), '\n']

        ret = [indent_str * level, data_attr[node], '\n']
        for child_node in children:
            if child_node in data_attr:
                ret += self._pretty(child_node, level + 1, indent_str)
            else:
                assert child_node in value_attr
                ret += [indent_str * (level + 1), '%s' % (value_attr[child_node],), '\n']

        return ret
