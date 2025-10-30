import threading

from traffic_sim.pygame_gui import pygame_thread_main

from utilities.Debug import debug


if __name__ == "__main__":
    shared_data = {
        "paused": False,
        "spawned": False,
        "graph_generated": False,
        "running": True,
        "agents": {},
        "info_win_is_open": False,
        "edge_state_win_is_open": False,
        "graph": None,
        "pos": None,
        "graph_changed": False,
        "closed_edge_set": set(),
        "updated_edge_set": False,
    }

    lock = threading.Lock()
    pygame_thread_main(shared_data, lock)
