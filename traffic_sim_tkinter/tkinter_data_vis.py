import tkinter as tk
from tkinter import ttk
from collections import OrderedDict
import random
import threading

from traffic_sim.core import color_pick
from utilities.Debug import debug

lock = threading.Lock()

DEBUG = False

# ScrollableFrame class
class ScrollableFrame(ttk.Frame):
    """Frame scrollable basato su Canvas."""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.vscroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.hscroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.inner = ttk.Frame(self.canvas)

        self.inner_id = self.canvas.create_window((0,0), window=self.inner, anchor="nw")

        self.canvas.configure(yscrollcommand=self.vscroll.set, xscrollcommand=self.hscroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Bind events to update scroll region
        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel support (Windows / Mac / Linux differences)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_windows)   # Windows / Mac
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)       # Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)       # Linux scroll down

    def _on_frame_configure(self, event):
        # update scrollregion to fit inner frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # keep inner frame width matching canvas (optional)
        canvas_width = event.width
        self.canvas.itemconfig(self.inner_id, width=canvas_width)

    def _on_mousewheel_windows(self, event):
        # On Windows and Mac, delta is used
        if event.delta:
            self.canvas.yview_scroll(int(-(event.delta/120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

# AgentBlock class  
class AgentBlock(ttk.Frame):
    """Rappresenta il blocco visivo di un singolo agente."""
    def __init__(self, parent, agent_id, data=None, *args, **kwargs):
        super().__init__(parent, relief="raised", borderwidth=1, padding=(6,6))
        self.agent_id = agent_id
        if DEBUG:
            debug("type agent_id:", type(agent_id))
        self.expanded = True

        # Header con nome agente e bottone collapse
        header = ttk.Frame(self)
        header.pack(fill="x", expand=True)
        self.title_label = ttk.Label(header, text="Agent " + str(agent_id.id) + " (" + str(color_pick(agent_id.get_color())) + ")", font=("TkDefaultFont", 11, "bold"))
        self.title_label.pack(side="left", anchor="w")
        self.toggle_btn = ttk.Button(header, text="–", width=2, command=self.toggle)
        self.toggle_btn.pack(side="right")

        # Contenitore dettagli
        self.details = ttk.Frame(self)
        self.details.pack(fill="both", expand=True, pady=(6,0))

        # Field labels e value labels (non tabella: usa grid per layout interno)
        fields = ["direzione", "velocità", "vertice attuale", "percorso", "coordinate attuali", "actual speed"]
        self.value_vars = {}
        for r, f in enumerate(fields):
            label = ttk.Label(self.details, text=f + ":")
            label.grid(row=r, column=0, sticky="w", padx=(0,6))
            v = tk.StringVar(value="—")
            val_label = ttk.Label(self.details, textvariable=v)
            val_label.grid(row=r, column=1, sticky="w")
            self.value_vars[f] = v

        # inizializza con dati se forniti
        if data:
            self.set_data(data)

    def set_data(self, data: dict):
        # data keys expected (case-insensitive): direction, speed, vertex, path, coords
        mapping = {
            "direzione": ["direction", "direzione"],
            "velocità": ["speed", "velocita", "velocità"],
            "vertice attuale": ["vertex", "vertice", "current_vertex", "current_edge"],
            "percorso": ["path", "percorso"],
            "coordinate attuali": ["coords", "coordinate", "position"],
            "actual speed": ["actual_speed", "actual speed"]
        }
        # fill variables from data
        for field, keys in mapping.items():
            value = "—"
            for k in keys:
                if k in data:
                    value = data[k]
                    break
            # format lists nicely
            if isinstance(value, (list, tuple)):
                value = ", ".join(map(str, value))
            self.value_vars[field].set(str(value))

    def toggle(self):
        if self.expanded:
            self.details.forget()
            self.toggle_btn.configure(text="+")
            self.expanded = False
        else:
            self.details.pack(fill="both", expand=True, pady=(6,0))
            self.toggle_btn.configure(text="–")
            self.expanded = True

# AgentGridGUI class
class AgentGridGUI:
    """Main GUI che gestisce più AgentBlock disposti in una griglia scrollabile."""
    def __init__(self, root, shared_data, lock,columns=2, update_interval_ms=100):
        self.root = root
        self.lock = lock
        self.shared_data = shared_data
        self.root.title("Agent Grid Monitor")
        self.columns = max(1, columns)
        self.update_interval_ms = update_interval_ms

        debug("Shared data", self.shared_data)

        # Top toolbar con pulsanti demo e contatori
        toolbar = ttk.Frame(root, padding=(4,4))
        toolbar.pack(side="top", fill="x")
    
        self.status_label = ttk.Label(toolbar, text="Agenti: 0")
        self.status_label.pack(side="right")

        # Scrollable frame per contenuti
        self.scrollable = ScrollableFrame(root)
        self.scrollable.pack(fill="both", expand=True)

        # contenitore degli agenti: mantenuto in ordine insert
        self.agent_blocks = OrderedDict()

        # Start periodic updater (per demo e per integrazione)
        self._running = True
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # avvia loop di aggiornamento UI (demo uses random updates)
        self.root.after(self.update_interval_ms, self._periodic_update)

    # ---------- API: aggiungi/rimuovi/aggiorna ----------
    def add_agent(self, agent_id, data=None):
        if agent_id in self.agent_blocks:
            # già presente -> aggiorna info
            self.update_agent(agent_id, data or {})
            return

        block = AgentBlock(self.scrollable.inner, agent_id, data or {})
        self.agent_blocks[agent_id] = block
        self._reflow_grid()
        self._update_status()

    def remove_agent(self, agent_id):
        if agent_id in self.agent_blocks:
            block = self.agent_blocks.pop(agent_id)
            block.destroy()
            self._reflow_grid()
            self._update_status()

    def update_agent(self, agent_id, data):
        if agent_id in self.agent_blocks:
            block = self.agent_blocks[agent_id]
            block.set_data(data)
        else:
            # Se l'agente non esiste, lo aggiungiamo (utile per integrazione diretta da simulazione)
            self.add_agent(agent_id, data)

    def update_agents_from_pygame(self, agents_dict):
        """
        Integrazione: agents_dict = { agent_id: { 'direction':..., 'speed':..., ... }, ... }
        Chiamare questa funzione dal thread principale Tk o schedulare la chiamata con after.
        Se la tua simulazione gira in un altro thread/processo, usa queue o struttura condivisa.
        """
        for aid, info in agents_dict.items():
            self.update_agent(aid, info)

    # ---------- gestione layout ----------
    def _reflow_grid(self):
        # posiziona i blocchi in griglia (self.columns colonne)
        for widget in self.scrollable.inner.grid_slaves():
            widget.grid_forget()

        for idx, (aid, block) in enumerate(self.agent_blocks.items()):
            row = idx // self.columns
            col = idx % self.columns
            block.grid(row=row, column=col, padx=6, pady=6, sticky="nwes")
            # rendi la colonna espandibile orizzontalmente
            self.scrollable.inner.grid_columnconfigure(col, weight=1)
    
    def _update_status(self):
        self.status_label.configure(text=f"Agenti: {len(self.agent_blocks)}")

    # ---------- demo / aggiornamenti periodici ----------
    def _periodic_update(self):
        if not self._running:
            return
        
        with self.lock:
            agents_data = dict(self.shared_data['agents'])
            if self.shared_data['running'] is False:
                debug("Shared data running is False")
                self._on_close()
            '''
            debug("Periodic update")
            debug("\tpaused:", self.shared_data['paused'])
            debug("\tspawned:", self.shared_data['spawned'])
            debug("\tgraph_generated:", self.shared_data['graph_generated'])
            debug("\trunning:", self.shared_data['running'])
            '''
        for aid, data in agents_data.items():
            self.update_agent(aid, data)
        self.root.after(self.update_interval_ms, self._periodic_update)
    
        '''
        # Demo: aggiorna dati casuali se ci sono agenti
        for aid in list(self.agent_blocks.keys()):
            # genera dati casuali per demo
            d = {
                "direction": random.choice(["N","S","E","W","NE","NW","SE","SW"]),
                "speed": round(random.uniform(0, 5), 2),
                "vertex": random.randint(0, 20),
                "path": [(random.randint(0,50), random.randint(0,50)) for _ in range(random.randint(1,5))],
                "coords": (round(random.uniform(0,100),2), round(random.uniform(0,100),2))
            }
            self.update_agent(aid, d)

        # ri-schedula
        self.root.after(self.update_interval_ms, self._periodic_update)
        '''
    def _on_close(self):
        self.shared_data['info_win_is_open'] = False
        self._running = False
        self.root.destroy()

def tk_info_node_window(shared_data, lock):
    root = tk.Tk()
    app = AgentGridGUI(root, shared_data=shared_data, lock=lock, columns=2, update_interval_ms=100)
    root.geometry("900x600")
    root.mainloop()
