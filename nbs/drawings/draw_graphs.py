import networkx as nx
import matplotlib.pyplot as plt

# This file is used for debugging purposes

def write_to_file(obj) -> None:
    with open('./drawings/logs.txt', 'a') as f:
        f.write(obj)


def print_digraphs(parse_graph = None, term_graph = None):
    plt.figure(figsize=(20, 20))
    if parse_graph:
        options = {
        'node_color': 'yellow',     # color of node
        'node_size': 10000,          # size of node
        'width': 1,                 # line width of edges
        'arrowstyle': '-|>',        # array style for directed graph
        'arrowsize': 14,            # size of arrow
        'edge_color':'blue',        # edge color
        }

        labels = {
                    node: ("\n".join(parse_graph._get_node_string(node).split()[:3]) + "\n" +
                        " ".join(parse_graph._get_node_string(node).split()[3:]))
                    for node in parse_graph._graph.nodes()
                }

        nx.draw(parse_graph._graph, with_labels = True, arrows=True,labels = labels,**options)
        plt.savefig('./drawings/parse_graph.png')
        plt.clf()

    if term_graph:
        options = {
        'node_color': 'green',     # color of node
        'node_size': 10000,       # size of node
        'width': 1,                # line width of edges
        'arrowstyle': '-|>',       # arrow style for directed graph
        'arrowsize': 10,           # size of arrow
        'edge_color': 'blue',      # edge color
        'font_size': 20            # font size for labels
        }

        labels = {
            node: ("\n".join(term_graph._get_node_string(node).split()[:3]) + "\n" +
                " ".join(term_graph._get_node_string(node).split()[3:]))
            for node in term_graph._graph.nodes()
        }

        nx.draw(term_graph._graph, pos= nx.spectral_layout(term_graph._graph), with_labels=True, arrows=True, labels=labels, **options)
        plt.savefig('./drawings/term_graph_spectral.png')
        plt.clf()
        nx.draw(term_graph._graph, pos= nx.spiral_layout(term_graph._graph), with_labels=True, arrows=True, labels=labels, **options)
        plt.savefig('./drawings/term_graph_spiral.png')
        plt.clf()
        nx.draw(term_graph._graph, pos= nx.shell_layout(term_graph._graph,dim = 2), with_labels=True, arrows=True, labels=labels,**options)
        plt.savefig('./drawings/term_graph_shell.png')
        plt.clf()