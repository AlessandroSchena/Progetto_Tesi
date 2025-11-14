import random
import math
import networkx as nx
import pygame
from utilities.Debug import debug
from utilities.ColorPicker import color_pick
from utilities.euclidean_distance import distanza_euclidea



MIN_SCALE = 0.1
MAX_SCALE = 10.0

DEBUG = False

# Classe per la gestione della telecamera (pan e zoom)
class Camera:
    def __init__(self, offset=(0, 0), scale=1.0):
        # offset è la coordinata nello spazio del mondo che sarà sullo schermo in (0,0)
        # cioè: screen_pos = (world_pos - offset) * scale
        self.offset = pygame.Vector2(offset)
        self.scale = scale

    def world_to_screen(self, world_pos):
        return (pygame.Vector2(world_pos) - self.offset) * self.scale

    def screen_to_world(self, screen_pos):
        return pygame.Vector2(screen_pos) / self.scale + self.offset

    def zoom_at(self, screen_pos, scale_factor):
        """
        Zoom mantenendo fisso il punto del mondo sotto screen_pos.
        scale_factor: moltiplicativo (es. 1.1 per zoom in, 0.9 per zoom out)
        """
        # limita lo zoom tra minimo e massimo
        new_scale = max(MIN_SCALE, min(MAX_SCALE, self.scale * scale_factor))
        if new_scale == self.scale:
            return  # nessun cambiamento (raggiunto il limite)
        # punto del mondo sotto il cursore prima dello zoom
        world_before = self.screen_to_world(screen_pos)
        # aggiorna lo zoom
        self.scale = new_scale
        # calcola nuovo offset in modo che world_before resti nello stesso screen_pos
        self.offset = world_before - pygame.Vector2(screen_pos) / self.scale

    def pan_by_screen_delta(self, delta_screen):
        """
        Pan in base a uno spostamento misurato in pixel sullo schermo.
        Dato che l’offset è in coordinate del mondo,
        converte il delta schermo in delta mondo (dividendo per lo scale).
        """
        self.offset -= pygame.Vector2(delta_screen) / self.scale

# Classe per rappresentare un agente che si muove nel grafo
class Agent:
    _id_agent = 0
    def __init__(self, color, graph, pos, lock=None, shared_data=None, speed=1, radius=5):
        self.id = Agent._id_agent
        Agent._id_agent += 1
        self.color = color # colore dell'agente
        self.speed = speed # velocità pixel per frame
        self.radius = radius # raggio di collisione
        self.path = [] # lista di nodi del percorso
        self.path_index = 0 # indice del nodo attuale nel percorso
        self.x, self.y = 0, 0 # posizione attuale
        self.prev_x, self.prev_y = 0, 0 # posizione precedente
        self.actual_speed = 0 # velocità attuale
        self.dir_x, self.dir_y = 0, 0 # direzione attuale
        self.angle = 0 # angolo di direzione in radianti
        self.side = "right" # lato su cui percorrere l'arco
        self.current_target = None # target corrente
        self.current_edge_nodes = None # arco e corsia attuali

        self.lock = lock
        self.shared_data = shared_data
        self.edge_closed = set()

        self.new_path(graph, pos) # inizializza con un percorso

    # Sceglie un nuovo percorso casuale nel grafo
    def new_path(self, graph, pos):
        if DEBUG:
            debug("Genera nuovo percorso per agente di colore", color_pick(self.color))

        temp_graph = graph.copy()
        if self.edge_closed:
            for edge in self.edge_closed:
                u, v = edge
                debug("graph edge is_open attribute", graph[u][v]['is_open'])
                if temp_graph.has_edge(u, v) and graph[u][v].get("is_open", True) == False:
                    temp_graph.remove_edge(u, v)
        while True:
            if DEBUG:
                debug("Tentativo di generazione percorso...")
            start, end = random.sample(list(temp_graph.nodes), 2)
            try:
                self.path = nx.shortest_path(temp_graph, source=start, target=end)
                if DEBUG:
                    debug("Percorso trovato:", start, "→", end)
                break
            except nx.NetworkXNoPath:
                if DEBUG:
                    debug("No path between", start, "and", end, "- retrying")
        self.path_index = 0

        # Inizializzazione delle coordinate dell'agente per iniziare il percorso sulla corsia di destra
        if len(self.path) > 1:
            u, v = self.path[0], self.path[1]
            p1, p2 = pos[u], pos[v]
            p1_off, p2_off = offset_position(p1, p2, side=self.side)
            self.x, self.y = p1_off
            self.current_target = p2_off
            self.current_edge_nodes = (u, v, self.side)

    # Muove l'agente verso il target, evitando collisioni con altri agenti
    def move_towards(self, target, others, traffic_lights, dt=1.0):
        tx, ty = target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)

        # velocità desiderata (quanto vorrei muovermi)
        desired_speed = self.speed * 0.5  # default: metà velocità

        # Controlla se agent sta entrando in un incrocio con semaforo
        if self.current_edge_nodes is not None:
            u, v, side = self.current_edge_nodes
            if v in traffic_lights:  # nodo di arrivo è incrocio
                tl = traffic_lights[v]
                edge = (u, v)  # arco entrante verso l'incrocio
                if edge in tl.lights:  # <-- controllo aggiuntivo
                    if dist < 40:  # vicino al nodo
                        if not tl.is_green(edge):
                            desired_speed = 0
                            # debug("Incoming TL @", v, "edges:", tl.lights.keys())
                            # debug("Agent approaching:", edge, "green?", tl.is_green(edge))


        if dist == 0:
            return True

        # direzione normalizzata verso il target
        dir_x, dir_y = dx / dist, dy / dist


        # cerco l'agente più vicino davanti a me sulla stessa corsia
        leader = None
        min_ahead = float('inf')

        for other in others:
            if other is self:
                continue
            if other.current_edge_nodes != self.current_edge_nodes:
                continue  # corsie diverse → no interazione

            # vettore relativo verso l’altro
            rel_x = other.x - self.x
            rel_y = other.y - self.y
            ahead = rel_x * dir_x + rel_y * dir_y  # distanza lungo direzione marcia

            if ahead > 0 and ahead < min_ahead:  # è davanti e più vicino degli altri
                min_ahead = ahead
                leader = other

        if leader is not None:
            dist_to_leader = math.hypot(leader.x - self.x, leader.y - self.y)
            safe_dist = self.radius * 3 + self.actual_speed * 0.5

            if dist_to_leader < safe_dist:
                # rallento: non supero mai la posizione del leader
                desired_speed = min(self.speed, leader.actual_speed)
                # se sono troppo vicino, riduco ancora
                if dist_to_leader < self.radius * 4:
                    desired_speed = 0  

                # Debug
                if DEBUG:
                    debug(f"[{color_pick(self.color)} x: {round(self.x,2)}, y: {round(self.y,2)}] segue [{color_pick(leader.color)} x: {round(leader.x,2)}, y: {round(leader.y,2)}] "
                      f"Dist={round(dist_to_leader,2)} Speed={round(desired_speed,2)}")

        # calcolo il passo massimo possibile senza superare il target
        step = min(desired_speed * dt, dist)

        # aggiorno posizione
        self.x += dir_x * step
        self.y += dir_y * step

        self.dir_x = dir_x
        self.dir_y = dir_y
        self.angle = math.atan2(dy, dx)

        return step == dist  # True se sono arrivato al target

    # Controlla se l'agente può muoversi sull'arco corrente (u, v)
    def can_reach_next_node(self, graph, u, v):
        """
        Verifica se l'arco (u, v) è aperto (attributo 'is_open' == True).
        Ritorna True se l'agente può percorrerlo, False altrimenti.
        """
        if graph.has_edge(u, v):
            edge_data = graph[u][v]
            return edge_data.get("is_open", True)
        return False

    def update_if_closed_edge(self, graph, pos, edge):
        target = self.path[-1]
        u, v = edge

        # crea una copia del grafo senza l’arco chiuso
        temp_graph = graph.copy()
        if temp_graph.has_edge(u, v):
            temp_graph.remove_edge(u, v)
        
        with self.lock:
            self.edge_closed = self.shared_data['closed_edge_set'].copy()

        try:
            new_path = nx.shortest_path(temp_graph, u, target)
            debug("New path: ", new_path)
            self.path = new_path
            self.path_index = 0

        except nx.NetworkXNoPath:
            self.new_path(graph, pos)

    # Aggiorna la posizione dell'agente lungo il percorso
    def update(self, graph, pos, agents, dt, traffic_lights):
        self.prev_x, self.prev_y = self.x, self.y

        if self.path_index < len(self.path) - 1:
            u = self.path[self.path_index] # nodo attuale
            v = self.path[self.path_index + 1] # nodo successivo
            # if not graph[v]['is_reachable']:

            # Verifica se l'arco (u, v) é aperto
            if not self.can_reach_next_node(graph, u, v):
                # comunica al server che l'arco (u, v) é chiuso
                with self.lock:
                    self.shared_data["closed_edge_set"].add((u, v))
                    self.shared_data["closed_edge_set"].add((v, u))
                    self.shared_data["updated_edge_set"] = True
                self.update_if_closed_edge(graph, pos, (u, v))
                return
            else:
                with self.lock:
                    if (u,v) in self.shared_data["closed_edge_set"]:
                        self.shared_data["closed_edge_set"].remove((u,v))
                        self.shared_data["closed_edge_set"].remove((v,u)) 

            p1, p2 = pos[u], pos[v]  # posizioni schermo

            p1_off, p2_off = offset_position(p1, p2, side=self.side)

            if self.current_target is None:
                self.x, self.y = p1_off
                self.current_target = p2_off
                self.current_edge_nodes = (u, v, self.side)

            arrived = self.move_towards(self.current_target, agents, traffic_lights, dt)

            if arrived:
                self.path_index += 1
                self.current_target = None  # forza ricalcolo prossimo arco
        else:
            self.new_path(graph, pos)

        if math.hypot(self.x - self.prev_x, self.y - self.prev_y) < 0.001:
            self.actual_speed = 0
        else:
            self.actual_speed = math.hypot(self.x - self.prev_x, self.y - self.prev_y) / dt

    # Disegna l'agente sullo schermo
    def draw(self, screen, camera, show_labels=False):
        radius_scaled = max(4, int(self.radius * camera.scale))
        base_shape = [(radius_scaled*2, 0),
                      (-radius_scaled, radius_scaled),
                      (-radius_scaled, -radius_scaled)]

        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        screen_pos = camera.world_to_screen((self.x, self.y))
        
        rotated = []
        for (x, y) in base_shape:
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            rotated.append((rx + screen_pos[0], ry + screen_pos[1]))

        pygame.draw.polygon(screen, self.color, rotated)

        # Disegna la label con l'ID
        if show_labels:
            font = pygame.font.Font(None, int(16 * camera.scale))  # dimensione proporzionale allo zoom
            text_surface = font.render(str(self.id), True, (255, 255, 255))  # colore bianco
            text_rect = text_surface.get_rect(center=(screen_pos[0], screen_pos[1] - radius_scaled*2))
            screen.blit(text_surface, text_rect)

    def current_edge(self):
        return self.current_edge_nodes
    
    def get_id(self):
        return self.id
    
    def get_color(self):
        return self.color

# Classe per il controllo dei semafori agli incroci
class TrafficLightController:
    def __init__(self, node, incoming_edges, green_time=5, red_time=5, detection_radius=50, type="normal"):
        self.node = node
        self.incoming_edges = incoming_edges  # lista di archi entranti (u → node)
        self.green_time = green_time
        self.red_time = red_time
        self.timer = 0
        self.current_green_index = 0  # quale arco ha il verde
        self.lights = {edge: "red" for edge in incoming_edges}
        self.type_accepted = ["normal", "sensor_based"]
        self.type = type  # tipo di semaforo: "normal" o "sensor_based"
        if self.incoming_edges:
            self.lights[self.incoming_edges[0]] = "green"
        

        self.detection_radius = detection_radius # raggio di rilevamento agenti
        self.priority_edge = None # ultimo edge che ha richiesto priorità
    
    def detect_agent(self, agents, pos):
        detected = {edge: False for edge in self.incoming_edges}
        for agent in agents:
            if agent.current_edge_nodes is None:
                continue
            u, v, side = agent.current_edge_nodes
            if v == self.node and (u, v) in detected:
                ax, ay = agent.x, agent.y
                nx_, ny_ = pos[v]
                dist = math.hypot(nx_ - ax, ny_ - ay)
                if dist < self.detection_radius:
                    detected[(u, v)] = True
        return detected

    def update(self, dt, agents, pos):
        detected = self.detect_agent(agents, pos)
        edge_whith_traffic = [edge for edge, is_detected in detected.items() if is_detected]
        # Se c'è un solo arco con traffico, assegna priorità
        if len(edge_whith_traffic) == 1:
            self.priority_edge = edge_whith_traffic[0]
            # imposta verde prioritario
            for e in self.lights:
                self.lights[e] = "red"
            self.lights[self.priority_edge] = "green"
            self.timer = 0
            return
        # elif len(edge_whith_traffic) > 1:
            # debug(f"Edge with traffic in node {self.node}: ", edge_whith_traffic)
    
        self.timer += dt
        if self.timer >= self.green_time:  # cambio verde
            # rimetti a rosso quello attuale
            current_edge = self.incoming_edges[self.current_green_index]
            self.lights[current_edge] = "red"

            # passo al prossimo
            self.current_green_index = (self.current_green_index + 1) % len(self.incoming_edges)
            next_edge = self.incoming_edges[self.current_green_index]
            self.lights[next_edge] = "green"

            self.timer = 0
        
    def is_green(self, edge):
        return self.lights.get(edge, "red") == "green"

# Funzione per spostare una coppia di punti a destra o sinistra dell'arco del grafo
def offset_position(p1, p2, side="right", lane_width=12):
    """
    Restituisce una coppia di punti (p1_off, p2_off) spostati lateralmente
    a destra o sinistra rispetto al segmento p1->p2.
    """
    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)

    if dist == 0:
        return p1, p2

    # direzione normalizzata
    dir_x, dir_y = dx / dist, dy / dist

    # normale a destra (ruotata -90°)
    nx, ny = dir_y, -dir_x

    if side == "right":
        nx, ny = -nx, -ny

    offset = (nx * lane_width / 2, ny * lane_width / 2)

    p1_off = (x1 + offset[0], y1 + offset[1])
    p2_off = (x2 + offset[0], y2 + offset[1])

    return p1_off, p2_off

# Funzione per creare un grafo a griglia
def build_grid_graph(rows, cols, area_rect, padding=60):
    """
    Crea un grafo a griglia e calcola posizioni centrate nel rettangolo area_rect
    con un padding interno.
    area_rect = (x, y, w, h)
    """
    G = nx.grid_2d_graph(rows, cols)
    
    # add_POI_to_graph(G, ["Museo", "Parco", "Teatro", "Biblioteca"])

    rect_x, rect_y, rect_w, rect_h = area_rect

    # area effettiva interna (dopo padding)
    inner_x = rect_x + padding
    inner_y = rect_y + padding
    inner_w = rect_w - 2 * padding
    inner_h = rect_h - 2 * padding

    # spaziatura tra nodi
    x_spacing = inner_w / (cols - 1) * 2 if cols > 1 else 0
    y_spacing = inner_h / (rows - 1) * 2 if rows > 1 else 0

    pos = {}
    if DEBUG:
        debug(G.nodes)
    for n in G.nodes():
        # nodi della griglia (r, c)
        r, c = n
        if r == 'POI':
            neigh_node = list(G.neighbors(n))
            if DEBUG:
                debug(f"neigh_node of {n} is {neigh_node}")
        else:
            x = inner_x + c * x_spacing
            y = inner_y + r * y_spacing
            pos[n] = (x, y)
        # POI: mettili al centro oppure in una posizione fittizia
        
        #pos[n] = (rect_x + rect_w / 2, rect_y + rect_h / 2)
    nx.set_node_attributes(G, True, "is_reachable")
    nx.set_edge_attributes(G, True, "is_open")

    return G, pos

# Funzione per generare un grafo connesso
def gen_graph(num_nodes:int, mode, traffic_lights):
    if mode == 'grid': # grid
        rows = int(num_nodes)
        cols = int(num_nodes)
        G, pos = build_grid_graph(rows, cols, (0, 0, 1000, 800))
        for n in G.nodes():
            if G.degree[n] > 2:
                G.nodes[n]["tipo"] = "incrocio"
                incoming_edges = [(u, n) for u in G.neighbors(n)]
                traffic_lights[n] = TrafficLightController(n, incoming_edges, green_time=2, red_time=2, detection_radius=80, type="sensor_based")
            else:
                G.nodes[n]["tipo"] = ""
        return G, pos
    elif mode == 'random': # random
        seed = random.randint(0, 1000)
        G = nx.connected_watts_strogatz_graph(num_nodes, 3, 0.5, seed)
        nx.set_node_attributes(G, "", "tipo")
        
        for n in G.nodes():
            if G.degree[n] > 2:
                G.nodes[n]["tipo"] = "incrocio"
                incoming_edges = [(u, n) for u in G.neighbors(n)]
                traffic_lights[n] = TrafficLightController(n, incoming_edges, green_time=2, red_time=2, detection_radius=80, type="sensor_based")
                if DEBUG:
                    debug("nodo incrocio:", n)
        
        add_POI_to_graph(G, ["Museo", "Parco", "Teatro", "Biblioteca"])

        nx.set_node_attributes(G, True, "is_reachable")
        nx.set_edge_attributes(G, True, "is_open")
        return G
    elif mode == 'pre_defined': # pre_defined
        G = nx.Graph()
                            
        nodes = [(0, {'tipo': '', 'is_reachable': True}), (1, {'tipo': '', 'is_reachable': True}), 
                    (2, {'tipo': '', 'is_reachable': True}), (3, {'tipo': '', 'is_reachable': True}), 
                    (4, {'tipo': '', 'is_reachable': True}), (5, {'tipo': '', 'is_reachable': True}), 
                    (6, {'tipo': '', 'is_reachable': True}), (7, {'tipo': '', 'is_reachable': True}), 
                    (8, {'tipo': 'incrocio', 'is_reachable': True}), (9, {'tipo': 'incrocio', 'is_reachable': True}), 
                    (10, {'tipo': '', 'is_reachable': True}), (11, {'tipo': 'incrocio', 'is_reachable': True}), 
                    (12, {'tipo': '', 'is_reachable': True}), (13, {'tipo': '', 'is_reachable': True}), 
                    (14, {'tipo': 'incrocio', 'is_reachable': True}), (15, {'tipo': '', 'is_reachable': True}), 
                    (16, {'tipo': '', 'is_reachable': True}), (17, {'tipo': 'incrocio', 'is_reachable': True}), 
                    (18, {'tipo': '', 'is_reachable': True}), (19, {'tipo': '', 'is_reachable': True}), 
                    (20, {'tipo': '', 'is_reachable': True}), (21, {'tipo': '', 'is_reachable': True}), 
                    (22, {'tipo': 'incrocio', 'is_reachable': True}), (23, {'tipo': 'incrocio', 'is_reachable': True}), 
                    (24, {'tipo': '', 'is_reachable': True}), (26, {'tipo': 'POI', 'nome': 'Museo', 'is_reachable': True}), 
                    (27, {'tipo': 'POI', 'nome': 'Parco', 'is_reachable': True}), (28, {'tipo': 'POI', 'nome': 'Teatro', 'is_reachable': True}), 
                    (29, {'tipo': 'POI', 'nome': 'Biblioteca', 'is_reachable': True})
            ]
        
        edges = [(0, 1, {'is_open': True}), (1, 19, {'is_open': True}), 
                    (2, 8, {'is_open': True}), (3, 8, {'is_open': True}), 
                    (3, 17, {'is_open': True}), (4, 20, {'is_open': True}), 
                    (5, 14, {'is_open': True}), (6, 11, {'is_open': True}), 
                    (7, 10, {'is_open': True}), (7, 19, {'is_open': True}), 
                    (8, 9, {'is_open': True}), (9, 22, {'is_open': True}), 
                    (9, 13, {'is_open': True}), (10, 11, {'is_open': True}), 
                    (11, 12, {'is_open': True}), (12, 17, {'is_open': True}), 
                    (14, 18, {'is_open': True}), (14, 15, {'is_open': True}), 
                    (16, 17, {'is_open': True}), (16, 29, {'is_open': True}), 
                    (17, 23, {'is_open': True}), (18, 21, {'is_open': True}), 
                    (19, 28, {'is_open': True}), (20, 24, {'is_open': True}), 
                    (21, 22, {'is_open': True}), (22, 23, {'is_open': True}), 
                    (22, 26, {'is_open': True}), (23, 24, {'is_open': True}), 
                    (24, 27, {'is_open': True})
                ]
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)

        for n in G.nodes():
            if G.nodes[n]["tipo"] == "incrocio":
                incoming_edges = [(u, n) for u in G.neighbors(n)]
                traffic_lights[n] = TrafficLightController(n, incoming_edges, green_time=2, red_time=2)
                if DEBUG:
                    debug("nodo incrocio:", n)
        return G
    elif mode == 'ring_road': # ring_road
        seed = random.randint(0, 1000)
        G1 = nx.connected_watts_strogatz_graph(num_nodes, 3, 0.5, seed)
        nx.set_node_attributes(G1, "", "tipo")
        debug("G1 nodes:", G1.nodes())
        for n in G1.nodes():
            if G1.degree[n] > 2:
                G1.nodes[n]["tipo"] = "incrocio"
                incoming_edges = [(u, n) for u in G1.neighbors(n)]
                traffic_lights[n] = TrafficLightController(n, incoming_edges, green_time=2, red_time=2)
                debug("nodo incrocio:", n)

        scale_pos = 950

        # add_POI_to_graph(G1, ["Museo", "Parco", "Teatro", "Biblioteca"])
        pos1 = nx.spring_layout(G1, scale=(scale_pos)/2, center=((scale_pos-20)/2, (scale_pos-60)/2))
        debug("nodi grado 1: ", [(node) for node, num_edge in G1.degree() if num_edge == 1])

        G2 = nx.cycle_graph(int(num_nodes/2))
        G2 = nx.relabel_nodes(G2, lambda x: x + len(G1.nodes))
        nx.set_node_attributes(G2, "", "tipo")
        pos2 = nx.circular_layout(G2, scale=(2*scale_pos/3), center=((scale_pos-20)/2, (scale_pos-60)/2))
        # pos2 = {n + len(G1.nodes): p for n, p in pos2.items()}
        pos = {**pos1, **pos2}
        debug("pos: ", pos.keys())
        G = nx.Graph()
        G.add_nodes_from(G2.nodes(data=True))
        G.add_edges_from(G2.edges(data=True))
        G.add_nodes_from(G1.nodes(data=True))
        G.add_edges_from(G1.edges(data=True))

        n_collegamenti = 3

        min_dist = float('inf')
        best_pair_list = []
        for int_node, int_pos in pos1.items():
            for est_node, est_pos in pos2.items():
                dist = distanza_euclidea(int_pos, est_pos)
                if dist < min_dist:
                    min_dist = dist
                    best_pair_list.append((dist, int_node, est_node))
            min_dist = float('inf')
        best_pair_list.sort(key=lambda x: x[0])

        selected_inner = set()
        selected_outer = set()
        edges_to_add = []

        for dist, nodo_interno, nodo_esterno in best_pair_list:
            if len(edges_to_add) >= n_collegamenti:
                break
            if nodo_interno not in selected_inner and nodo_esterno not in selected_outer:
                edges_to_add.append((nodo_esterno, nodo_interno))
                selected_inner.add(nodo_interno)
                selected_outer.add(nodo_esterno)

        G.add_edges_from(edges_to_add)

        debug("grafo nodi: ", G.nodes)
        return G, pos


# aggiungi punti di interesse(POI) al grafo
def add_POI_to_graph(G, POI_list):
    G_num_nodes = len(G.nodes)

    for i, poi in enumerate(POI_list):
        # Capire che tipo di nodo ha il grafo
        esempio_nodo = next(iter(G.nodes))  # prendo un nodo qualunque
        
        if isinstance(esempio_nodo, int):
            # caso: nodi interi -> aggiungo un nuovo intero
            nuovo_nodo = G_num_nodes + i + 1
        elif isinstance(esempio_nodo, tuple):
            # caso: nodi tuple -> creo una tupla fittizia unica
            nuovo_nodo = ("POI", G_num_nodes + i + 1)
        else:
            # fallback: se i nodi hanno tipo diverso (stringhe, ecc.)
            nuovo_nodo = f"POI_{G_num_nodes + i + 1}"

        # aggiungo nodo con attributi
        G.add_node(nuovo_nodo, tipo="POI", nome=poi)

        # collego a un nodo esistente casuale
        nodo_random = random.choice(list(G.nodes))
        while nodo_random == nuovo_nodo:  # evito self-loop
            nodo_random = random.choice(list(G.nodes))

        G.add_edge(nuovo_nodo, nodo_random)
