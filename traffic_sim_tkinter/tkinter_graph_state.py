import tkinter as tk
from tkinter import simpledialog, messagebox
import networkx as nx
import math
import random
from utilities.Debug import debug

class StateDialog(simpledialog.Dialog):
    def __init__(self, parent, title, edge):
        self.u, self.v = edge
        super().__init__(parent, title)
    def body(self, master):
        tk.Label(master, text=f"Seleziona lo stato di ({self.u}, {self.v}):").pack(pady=5)
        self.var = tk.StringVar(value="aperto")  # Valore di default
        opzioni = ["aperto", "chiuso"]
        tk.OptionMenu(master, self.var, *opzioni).pack(pady=5)
    
    def apply(self):
        self.result = self.var.get()

class GraphApp:
    def __init__(self, root, shared_data, lock):
        self.lock = lock
        self.shared_data = shared_data

        self.root = root
        self.root.title("Interazione con archi del grafo")

        # Canvas
        self.canvas = tk.Canvas(root, width=800, height=600, bg="white")
        self.canvas.pack(fill="both", expand=True)

        self.G = None
        self.pos = None

        # Grafo iniziale
        with lock:
            if shared_data['graph_generated']:
                self.G = shared_data['graph']
                self.pos = shared_data['pos']
        # self.pos = nx.spring_layout(self.G, seed=42)

        self.edge_to_id = {}
        self.id_to_edge = {}
        self.hover_edge = None
        self.selected_edge = None

        self.draw_graph()

        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_click)

    def draw_graph(self):
        """Disegna nodi e archi"""
        self.canvas.delete("all")
        self.edge_to_id.clear()
        self.id_to_edge.clear()

        # Disegna archi
        for (u, v) in self.G.edges():
            x1, y1 = self.pos[u]
            x2, y2 = self.pos[v]
            x1, y1 = 400 + x1 * 200, 300 + y1 * 200
            x2, y2 = 400 + x2 * 200, 300 + y2 * 200
            color = "black" if self.G[u][v]['is_open'] else "red"
            line_id = self.canvas.create_line(x1, y1, x2, y2, width=2, fill=color)
            self.edge_to_id[(u, v)] = line_id
            self.edge_to_id[(v, u)] = line_id
            self.id_to_edge[line_id] = (u, v)

        # Disegna nodi
        for n in self.G.nodes():
            x, y = self.pos[n]
            x, y = 400 + x * 200, 300 + y * 200
            r = 15
            fill_color = "lightblue" if self.G.nodes[n].get("is_reachable", True) else "gray"
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=fill_color, outline="black")
            self.canvas.create_text(x, y, text=str(n))

    def on_mouse_move(self, event):
        edge = self.find_edge_near(event.x, event.y)
        if edge != self.hover_edge:
            self.reset_highlight()
            if edge:
                line_id = self.edge_to_id[edge]
                self.canvas.itemconfig(line_id, fill="green", width=4)
            self.hover_edge = edge

    def on_click(self, event):
        edge = self.find_edge_near(event.x, event.y)
        if edge:
            self.selected_edge = edge
            self.edit_edge_attributes(edge)

    def reset_highlight(self):
        if self.hover_edge:
            u, v = self.hover_edge
            line_id = self.edge_to_id[self.hover_edge]
            color = "black" if self.G[u][v]["is_open"] else "red"
            self.canvas.itemconfig(line_id, fill=color, width=2)
            self.hover_edge = None

    def find_edge_near(self, x, y, threshold=10):
        for (u, v), line_id in self.edge_to_id.items():
            x1, y1, x2, y2 = self.canvas.coords(line_id)
            dist = self.point_line_distance(x, y, x1, y1, x2, y2)
            if dist < threshold:
                return (u, v)
        return None

    @staticmethod
    def point_line_distance(px, py, x1, y1, x2, y2):
        line_mag = math.hypot(x2 - x1, y2 - y1)
        if line_mag < 1e-6:
            return math.hypot(px - x1, py - y1)
        u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
        u = max(min(u, 1), 0)
        ix = x1 + u * (x2 - x1)
        iy = y1 + u * (y2 - y1)
        return math.hypot(px - ix, py - iy)

    def edit_edge_attributes(self, edge):
        """Permette di modificare l’attributo is_open e aggiorna il colore"""
        u, v = edge
        stateDialog = StateDialog(self.root, title="Seleziona stato", edge=edge)
        value = stateDialog.result
        if value is None:
            return

        is_open = (value == "aperto")
        self.G[u][v]["is_open"] = is_open

        # Aggiorna colore dell’arco
        line_id = self.edge_to_id[edge]
        new_color = "black" if is_open else "red"
        self.canvas.itemconfig(line_id, fill=new_color)

        # Aggiorna raggiungibilità dei nodi
        self.update_reachability()
        self.draw_graph()

        messagebox.showinfo("Attributo aggiornato", f"is_open = {is_open}")

    def update_reachability(self):
        """Aggiorna l’attributo is_reachable dei nodi"""
        # Crea sottografo con soli archi aperti
        open_edges = [(u, v) for u, v, d in self.G.edges(data=True) if d["is_open"]]
        G_open = nx.Graph()
        G_open.add_nodes_from(self.G.nodes())
        G_open.add_edges_from(open_edges)

        # Calcola le componenti connesse
        reachable_nodes = set()
        for comp in nx.connected_components(G_open):
            if len(comp) > 1:  # almeno un collegamento
                reachable_nodes.update(comp)

        # Aggiorna attributi
        for n in self.G.nodes():
            self.G.nodes[n]["is_reachable"] = (n in reachable_nodes)
        
        with self.lock:
            debug("self.shared_data before update:", self.shared_data['graph_changed'])
            self.shared_data['graph'] = self.G
            self.shared_data['graph_changed'] = True
        


def tk_edge_state_window(shared_data, lock):
    with lock:
        if not shared_data['graph_generated']:
            debug("Grafo non generato")
            return
    root = tk.Tk()
    app = GraphApp(root, shared_data, lock)
    root.mainloop()
    with lock:
        shared_data['edge_state_win_is_open'] = False
