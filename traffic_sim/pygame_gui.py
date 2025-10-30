import pygame
import pygame_gui
import threading
import math
import random
import networkx as nx
import numpy as np
from screeninfo import get_monitors

from traffic_sim.core import *
from traffic_sim.draw import *

from traffic_sim_tkinter.tkinter_data_vis import tk_info_node_window
from traffic_sim_tkinter.tkinter_graph_state import tk_edge_state_window

DEBUG = False

def normalize(value, min_val, max_val):
    return 2 * (value - min_val) / (max_val - min_val) - 1

def pygame_thread_main(shared_data, lock):
    for m in get_monitors():
        mw_inch = m.width_mm / 25.4
        mh_inch = m.height_mm / 25.4
        diag_inch = math.sqrt(mw_inch**2 + mh_inch**2)

    if diag_inch >= 20:
        WIDTH = 1400
    elif diag_inch >= 15:
        WIDTH = 900
    else:
        WIDTH = 700
    HEIGHT = int(WIDTH*(2/3))
    FPS = 60

    UI_WIDTH = int(WIDTH*(1/3))
    UI_HEIGHT = HEIGHT 
    

    SIM_WIDTH = WIDTH - UI_WIDTH
    SIM_HEIGHT = HEIGHT

    BTN_WIDTH = UI_WIDTH - 36
    BTN_HEIGHT = 32

    Y_PANEL = 10

    INIT_SCALE = 1.0

    if DEBUG:
        debug("Shared_data", shared_data)

    camera = Camera(offset=(0, 0), scale=INIT_SCALE) # inizializzazione della camera, initial_offset = (-300, -200)
    sim_rect_coord = (10, 10, SIM_WIDTH - 20, SIM_HEIGHT - 20) # area di simulazione
    graph_box_coord = (40, 40, SIM_WIDTH - 80, SIM_HEIGHT - 80)# area di generazione del grafo
    
    # inizializzazione di pygame e pygame_gui
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    pygame.display.set_caption("Pygame con GUI")

    theme = {
        "speed_label" : {
            "colors": {
                "normal_text": "#FF0000"
            }
        }
    }

    myfont = pygame.font.SysFont('Arial', 14)
    label_font = pygame.font.SysFont(None, 20)

    manager = pygame_gui.UIManager((WIDTH, HEIGHT), theme)

    traffic_lights = {}

    panel_rect = pygame.Rect((WIDTH - UI_WIDTH, 10), (UI_WIDTH - 10, HEIGHT - 20))

    # pannello UI
    panel = pygame_gui.elements.UIPanel(
        relative_rect=panel_rect,
        starting_height=1,
        manager=manager
    )

    # pulsante "Generate Graph"
    btn1 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, BTN_HEIGHT)),   # 430 per 1400, fattore di scala 0.3078
        text="Generate Graph",
        manager=manager,
        container=panel
    )
    # etichetta e slider per il numero di nodi
    Y_PANEL = Y_PANEL + BTN_HEIGHT
    lbl1 = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)),
        text="Numero nodi: 25",
        manager=manager,
        container=panel
    )
    Y_PANEL = Y_PANEL + 28
    sld1 = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)),
        start_value=25,
        value_range=(5, 100),
        manager=manager,
        container=panel
    )

    # pulsante "Spawn Agents"
    Y_PANEL = Y_PANEL + BTN_HEIGHT + 20
    btn2 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, BTN_HEIGHT)),
        text="Spawn agents",
        manager=manager,
        container=panel
    )

    # etichetta e slider per il numero di agenti
    Y_PANEL = Y_PANEL + BTN_HEIGHT
    lbl2 = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)),
        text="Numero agenti: 10",
        manager=manager,
        container=panel
    )
    Y_PANEL = Y_PANEL + 28
    sld2 = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)),
        start_value=10,
        value_range=(5, 20),
        manager=manager,
        container=panel
    )


    # pulsante "Pause/Resume"
    Y_PANEL = Y_PANEL + BTN_HEIGHT + 26
    btn3 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (int(UI_WIDTH*0.44), 32)),
        text="pause",
        manager=manager,
        container=panel
    )

    # pulsante "Step"
    btn4 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((int(UI_WIDTH/2), Y_PANEL), (int(UI_WIDTH*0.44), 32)),
        text="step",
        manager=manager,
        container=panel
    )


    # etichetta e menu a tendina per la forma del grafo
    Y_PANEL = Y_PANEL + BTN_HEIGHT + 13
    lbl3 = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 20)),
        text="tipo di grafo",
        manager=manager,
        container=panel
    )
    Y_PANEL = Y_PANEL + 23
    dd1 = pygame_gui.elements.UIDropDownMenu(
        options_list=['grid', 'random', 'pre_defined'],
        starting_option='random',
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)),
        manager=manager,
        container=panel
    )

    # pulsante "Enable Move"
    Y_PANEL = Y_PANEL + BTN_HEIGHT + 10
    btn5 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, BTN_HEIGHT)),
        text="Reset camera",
        manager=manager,
        container=panel
    )

    # pulsante "Enable Move"
    Y_PANEL = Y_PANEL + BTN_HEIGHT + 10
    btn6 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, BTN_HEIGHT)), # y=342
        text="mostra info agenti",
        manager=manager,
        container=panel
    )

    Y_PANEL = Y_PANEL + BTN_HEIGHT + 10
    btn7 = pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, BTN_HEIGHT)), # y=382
        text="apri gestione stato grafo",
        manager=manager,
        container=panel
    )

    Y_PANEL = Y_PANEL + BTN_HEIGHT + 16
    lbl_speed = pygame_gui.elements.UILabel(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 20)), # y=430
        text="simulation speed(x1.0)",
        manager=manager,    
        container=panel
    )
    Y_PANEL = Y_PANEL + 23
    sld_speed = pygame_gui.elements.UIHorizontalSlider(
        relative_rect=pygame.Rect((10, Y_PANEL), (BTN_WIDTH, 32)), # y=455
        start_value=1.0,
        value_range=(0.1, 10.0),
        manager=manager,
        container=panel
    )

    sim_surface = pygame.Surface((SIM_WIDTH - 20, SIM_HEIGHT - 20))
    sim_surface.fill((30, 33, 39))  # colore di sfondo iniziale
    sim_rect = sim_surface.get_rect(topleft=(10, 10))

    graph_box = pygame.draw.rect(screen, (30, 33, 39), graph_box_coord)

    running = True
    spawned = False
    paused = False
    show_labels = False
    graph_generated = False
    shift_view = False
    dragging = False
    is_tk_open = False

    last_mouse_pos = None

    graph_gen_mode = 'random'

    agents = [] # lista di agenti

    scaled_pos = {} # dizionario per le posizioni scalate

    traffic_lights = {} # dizionario per i semafori

    simulation_speed = 1.0

    btn2.disable()
    btn4.disable()
    sld2.disable()

    update_speed_label_timer = 0 # timer per aggiornare la label della velocità degli agenti

    

    while running:
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
        dt_ms = clock.tick_busy_loop(FPS)
        dt = dt_ms / 1000.0
        update_speed_label_timer += dt_ms

        dt_sim = dt * simulation_speed # tempo di simulazione moltiplicato per la velocità di simulazione

        # print("dt: ", dt, "\ndt_sim: ", dt_sim)
        
        for event in pygame.event.get():
            manager.process_events(event)

            if event.type == pygame.QUIT:
                running = False
                with lock:
                    shared_data['running'] = False

            elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: # Premere 'ESC' per uscire
                        running = False
                        with lock:
                            shared_data['running'] = False
                    elif event.key == pygame.K_l:  # Premere 'L' per mostrare/nascondere le label
                        show_labels = not show_labels
                        if DEBUG:
                            debug("show_labels: ", show_labels)
                        if graph_generated:
                            draw_graph_centered(G, pos, graph_gen_mode, show_labels, traffic_lights, sim_surface, graph_box, screen, myfont, camera)
                    elif event.key == pygame.K_SPACE: # Premere 'SPACE' per mettere in pausa la simulazione
                        paused = not paused
                        with lock:
                            shared_data['paused'] = paused
                        if paused:
                            btn3.set_text("resume")
                            btn4.enable()
                        else:
                            btn3.set_text("pause")
                            btn4.disable()

            elif event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                    if event.ui_element == sld1: # cambia numero nodi
                        lbl1.set_text(f"Numero nodi: {int(sld1.get_current_value())}")
                    elif event.ui_element == sld_speed: # cambia velocità simulazione
                        simulation_speed = sld_speed.get_current_value()
                        lbl_speed.set_text(f"simulation speed(x{simulation_speed:.1f})")
                    elif event.ui_element == sld2: # cambia numero agenti
                        lbl2.set_text(f"Numero agenti: {sld2.get_current_value()}")

                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == btn1: # genera grafo
                        sim_surface.fill((30, 33, 39))
                        draw_grid(camera, sim_surface, sim_surface.get_rect(topleft=(10, 10)))
                        if graph_gen_mode == 'grid':
                            G, pos = gen_graph(5, graph_gen_mode, traffic_lights)
                            with lock:
                                shared_data['graph'] = G
                                shared_data['graph_generated'] = True
                            draw_graph(G, pos, graph_gen_mode, show_labels, traffic_lights, sim_surface, graph_box, screen, myfont, camera)
                            scaled_pos = pos

                            debug("POS:", pos)

                            xs = np.array([v[0] for v in pos.values()])
                            ys = np.array([v[1] for v in pos.values()])

                            x_min, x_max = xs.min(), xs.max()
                            y_min, y_max = ys.min(), ys.max()

                            pos_norm = {
                                k: (normalize(v[0], x_min, x_max), normalize(v[1], y_min, y_max))
                                for k, v in pos.items()
                            }

                            with lock:
                                shared_data['pos'] = pos_norm

                        else:
                            G = gen_graph(int(sld1.get_current_value()), graph_gen_mode, traffic_lights)

                            if graph_gen_mode == 'random':
                                pos = nx.spring_layout(G, scale=(SIM_WIDTH)/2, center=((SIM_WIDTH-20)/2, (SIM_HEIGHT-60)/2))
                                pos = {n: (x*2, y*2) for n, (x, y) in pos.items()}  # scala le posizioni per una migliore visibilità
                            elif graph_gen_mode == 'pre_defined':
                                pos = {0: (np.float64(1184.4347090770966), np.float64(682.5497704741763)), 
                                       1: (np.float64(1383.8081567653837), np.float64(695.3533051162649)), 
                                       2: (np.float64(499.2379835080458), np.float64(1550.0471161298778)), 
                                       3: (np.float64(807.9030878074891), np.float64(1326.0124879230507)), 
                                       4: (np.float64(1064.323268027042), np.float64(155.70571582739183)), 
                                       5: (np.float64(-20.0), np.float64(79.56581681082923)), 
                                       6: (np.float64(1578.18644407733), np.float64(1513.5625463639808)), 
                                       7: (np.float64(1695.7584186815654), np.float64(947.1213535394141)), 
                                       8: (np.float64(580.6140292563205), np.float64(1374.4170723296706)), 
                                       9: (np.float64(458.6523590999161), np.float64(1175.0978557006601)), 
                                       10: (np.float64(1672.1841020147288), np.float64(1154.3810944689299)), 
                                       11: (np.float64(1534.3355120394015), np.float64(1321.632527188649)), 
                                       12: (np.float64(1290.8698989477768), np.float64(1265.383845487956)), 
                                       13: (np.float64(293.5202367859606), np.float64(1266.3206514666817)), 
                                       14: (np.float64(124.45900877598001), np.float64(178.69447597485237)), 
                                       15: (np.float64(118.35437205288531), np.float64(5.1750290217470365)), 
                                       16: (np.float64(1216.852204811691), np.float64(1369.0181422248809)), 
                                       17: (np.float64(1024.9282202317208), np.float64(1198.507180873981)), 
                                       18: (np.float64(221.40559748369571), np.float64(408.93150952583744)), 
                                       19: (np.float64(1611.7185127954453), np.float64(749.9353795888587)), 
                                       20: (np.float64(1003.4571510939005), np.float64(340.50322249117767)), 
                                       21: (np.float64(349.3038636987003), np.float64(651.8968011732497)), 
                                       22: (np.float64(516.7983886635782), np.float64(903.763595563013)), 
                                       23: (np.float64(832.5774532999345), np.float64(907.4609160983032)), 
                                       24: (np.float64(928.9015507871163), np.float64(599.0858066006342)), 
                                       26: (np.float64(348.14267896880915), np.float64(906.4062348971107)), 
                                       27: (np.float64(1014.0958489362621), np.float64(468.69892369322)), 
                                       28: (np.float64(1774.1919290025623), np.float64(656.1078017573541)), 
                                       29: (np.float64(1396.985013309661), np.float64(1465.6638216882443))
                                }

                            

                            if graph_gen_mode == 'pre_defined':
                                debug("Pre_defined pos: ", pos)

                            xs = np.array([v[0] for v in pos.values()])
                            ys = np.array([v[1] for v in pos.values()])

                            x_min, x_max = xs.min(), xs.max()
                            y_min, y_max = ys.min(), ys.max()

                            pos_norm = {
                                k: (normalize(v[0], x_min, x_max), normalize(v[1], y_min, y_max))
                                for k, v in pos.items()
                            }                           

                            with lock:
                                shared_data['pos'] = pos_norm # {n: (x*2, y*2) for n, (x, y) in pos_norm.items()}
                            draw_graph(G, pos, show_labels, camera=camera, sim_surface=sim_surface, traffic_lights=traffic_lights, myfont=myfont)
                            scaled_pos = pos
                            # scaled_pos = scaled_pos_calc(pos, graph_box)

                        with lock:
                            shared_data['graph'] = G

                        btn2.enable()
                        sld2.enable()
                        graph_generated = True
                        with lock:
                            shared_data['graph_generated'] = True
                        if spawned:
                            for agent in agents:
                                agent.new_path(G, scaled_pos)
                                agent.draw(sim_surface, camera=camera, show_labels=show_labels)
                    if event.ui_element == btn2: # spawn agents
                        if G.number_of_nodes() != 0 and not spawned:
                            num_agents = int(sld2.get_current_value()) - 4

                            colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]
                            for _ in range(num_agents):
                                colors.append((random.randint(0,255), random.randint(0,255), random.randint(0,255)))
                            
                            for color in colors:
                                agents.append(Agent(color, speed=random.randint(40, 120), radius=5, lock=lock, shared_data=shared_data, graph=G, pos=scaled_pos))

                            i = 0
                            line_spacing = 110
                            for agent in agents:
                                agent.draw(sim_surface, camera=camera, show_labels=show_labels)
                                
                                with lock:
                                    for agent in agents:
                                        shared_data["agents"][agent] = {
                                            'direction': round(math.degrees(agent.angle), 2),
                                            'speed': round(agent.actual_speed, 2),
                                            'current_edge': agent.current_edge(),
                                            'path': agent.path,
                                            'coords': (round(agent.x, 2), round(agent.y, 2)),
                                            'actual_speed': round(agent.actual_speed, 2)
                                        }                                

                                i += 1
                            
                            spawned = True
                            with lock:
                                shared_data['spawned'] = True
                        else:
                            if G.number_of_nodes() == 0:
                                if DEBUG:
                                    debug("Generate a graph first!")
                            if spawned:
                                if DEBUG:
                                    debug("Agents already spawned!")
                    if event.ui_element == btn3: # pause/resume
                        paused = not paused
                        with lock:
                            shared_data['paused'] = paused
                        if paused:
                            btn3.set_text("resume")
                            btn4.enable()
                        else:
                            btn3.set_text("pause")
                            btn4.disable()
                    if event.ui_element == btn4: # step
                        for agent in agents:
                            agent.update(G, scaled_pos, agents, dt * simulation_speed, traffic_lights)
                            agent.draw(sim_surface, camera=camera, show_labels=show_labels)
                    if event.ui_element == btn5: # attiva sposta
                        camera.scale = INIT_SCALE
                        camera.offset = pygame.Vector2(-300, -200)
                        shift_view = not shift_view
                        if shift_view:
                            if DEBUG:
                                debug("Attiva sposta")
                            btn5.set_text("disattiva sposta")
                        else:
                            if DEBUG:
                                debug("Disattiva sposta")
                            btn5.set_text("attiva sposta")
                    if event.ui_element == btn6: # mostra info agenti
                        debug("btn6 pressed: ", shared_data['info_win_is_open'])
                        with lock:
                            if not shared_data['info_win_is_open']:
                                tk_threading = threading.Thread(target=tk_info_node_window, args=(shared_data, lock), daemon=True)
                                tk_threading.start()
                                shared_data['info_win_is_open'] = True
                    if event.ui_element == btn7: # apre finestra per modificare lo stato degli archi
                        debug("btn7 pressed: ", shared_data['edge_state_win_is_open'])
                        with lock:
                            if not shared_data['edge_state_win_is_open']:
                                tk_graph_state_threading = threading.Thread(target=tk_edge_state_window, args=(shared_data, lock), daemon=True)
                                tk_graph_state_threading.start()
                                shared_data['edge_state_win_is_open'] = True

                if event.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                    if event.ui_element == dd1: # cambia forma agente
                        graph_gen_mode = event.text
                
                '''Eventi mouse per spostare la vista'''
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # click sinistro → inizio pan
                    if DEBUG:
                        debug("MOUSEBUTTONDOWN ")
                    mx, my = event.pos
                    
                    if not panel_rect.collidepoint((mx, my)):
                        dragging = True
                        last_mouse_pos = pygame.Vector2(mx, my)
                    # altrimenti: click dentro il pannello → lascia gestire alla GUI
                elif event.button == 4:  # rotella su → zoom in
                    if DEBUG:
                        debug("MOUSEWHEEL UP ")
                    mx, my = event.pos
                    if not panel_rect.collidepoint((mx, my)):
                        camera.zoom_at((mx, my), 1.12)
                elif event.button == 5:  # rotella giù → zoom out
                    if DEBUG:
                        debug("MOUSEWHEEL DOWN ")
                    mx, my = event.pos
                    if not panel_rect.collidepoint((mx, my)):
                        camera.zoom_at((mx, my), 1.0 / 1.12)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
                    last_mouse_pos = None

            elif event.type == pygame.MOUSEMOTION:
                if dragging:
                    if DEBUG:
                        debug("MOUSEMOTION ", event.pos)
                    mx, my = event.pos
                    curr = pygame.Vector2(mx, my)
                    delta = curr - last_mouse_pos
                    # muovi la telecamera con delta in pixel dello schermo
                    camera.pan_by_screen_delta(delta)
                    last_mouse_pos = curr

                    world_coords = camera.screen_to_world((mx, my))
                    if DEBUG:
                        debug(f"Mouse mondo: ({world_coords.x:.2f}, {world_coords.y:.2f})")

        
       
        # aggiorna lo stato del grafo
        with lock:
            if shared_data['graph_changed']:
                G = shared_data['graph']
                shared_data['graph_changed'] = False
            if shared_data['updated_edge_set']:
                for agent in agents:
                    for edge in shared_data['closed_edge_set']:
                        if edge in agent.path:
                            agent.update_if_closed_edge(G, scaled_pos, edge)


        if spawned and not paused:
            '''possiblità di cambiare tipo di disegno del grafo'''
            with lock:
                if DEBUG:
                    debug("closed_edge_set:", shared_data['closed_edge_set'])
            #draw_graph_centered(G, pos, graph_gen_mode, show_labels)
            draw_graph(G, pos, show_labels, camera=camera, sim_surface=sim_surface, traffic_lights=traffic_lights, myfont=myfont)
            for tl in traffic_lights.values():
                tl.update(dt, agents, pos)
            
            
                for agent in agents:
                    with lock:
                        shared_data["agents"][agent] = {
                            'direction': round(math.degrees(agent.angle), 2),
                            'speed': round(agent.actual_speed, 2),
                            'current_edge': agent.current_edge(),
                            'path': agent.path,
                            'coords': (round(agent.x, 2), round(agent.y, 2)),
                            'actual_speed': round(agent.actual_speed, 2)
                        }
                    agent.update(G, scaled_pos, agents, dt * simulation_speed, traffic_lights)
                    agent.draw(sim_surface, camera=camera, show_labels=show_labels)
            
        if spawned and paused:
            '''possiblità di cambiare tipo di disegno del grafo'''
            # draw_graph_centered(G, pos, graph_gen_mode, show_labels)
            draw_graph(G, pos, show_labels, camera=camera, sim_surface=sim_surface, traffic_lights=traffic_lights, myfont=myfont)
            
            # for tl in traffic_lights.values():
            #     tl.update(dt)
            
            
            for agent in agents:
                agent.draw(sim_surface, camera=camera, show_labels=show_labels)

                '''
                # aggiorna le label
                if agent in lbls_dir:
                    lbls_dir[agent].set_text(color_pick(agent.color) + " agent direction: " + str(round(math.degrees(agent.angle), 2)) + "°")
                else:
                    debug(f"Agent {color_pick(agent.color)} not found in labels dictionary!")
                if update_speed_label_timer >= 500: # aggiorna ogni 500 ms
                    if agent in lbls_spd:
                        lbls_spd[agent].set_text(color_pick(agent.color) + " agent speed: " + str(round(agent.actual_speed, 2)) + " px/s")
                        update_speed_label_timer = 0
                    else:
                        debug(f"Agent {color_pick(agent.color)} not found in speed labels dictionary or speed is equal to zero")
                        update_speed_label_timer = 0
                
                if agent in lbls_current_edge:
                    lbls_current_edge[agent].set_text(color_pick(agent.color) + " agent current edge: " + str(agent.current_edge()))
                else:
                    debug(f"Agent {color_pick(agent.color)} not found in current edge labels dictionary!")
                
                if agent in lbls_path:
                    lbls_path[agent].set_text(color_pick(agent.color) + " agent path: " + str(agent.path))
                else:
                    debug(f"Agent {color_pick(agent.color)} not found in path labels dictionary!")
                '''

        if not spawned and graph_generated:
            draw_graph(G, pos, show_labels, camera=camera, sim_surface=sim_surface, traffic_lights=traffic_lights, myfont=myfont)
        

        screen.blit(sim_surface, (10, 10))
        lbl_key_event_show = label_font.render("L mostra label • ESC chiudi simulazione", True, (150, 150, 150))
        screen.blit(lbl_key_event_show, (SIM_WIDTH / 2 - 130, HEIGHT - 30))
        manager.update(dt)
        manager.draw_ui(screen)

        pygame.display.flip()
