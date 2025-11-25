traffic_on_graph = {}

def init_traffic_dir(G):
    global traffic_on_graph
    for u, v in G.edges():
        traffic_on_graph[(u,v)] = 0
        traffic_on_graph[(v,u)] = 0

def add_traffic_edge(edge):
    """Incrementa il numero di agenti su un arco diretto (u, v)."""
    global traffic_on_graph
    if edge is None:
        return
    if edge not in traffic_on_graph:
        traffic_on_graph[edge] = 0
    traffic_on_graph[edge] += 1

def remove_traffic_edge(edge):
    """Decrementa il numero di agenti su un arco diretto (u, v). Se arriva a 0 rimuove la chiave."""
    global traffic_on_graph
    if edge is None:
        return
    if edge in traffic_on_graph:
        traffic_on_graph[edge] -= 1
        # protezione: non permettere conteggi negativi
        if traffic_on_graph[edge] <= 0:
            traffic_on_graph[edge] = 0

def get_traffic(u, v):
    """Ritorna il conteggio di traffico su u->v."""
    global traffic_on_graph
    return traffic_on_graph.get((u, v), 0)
