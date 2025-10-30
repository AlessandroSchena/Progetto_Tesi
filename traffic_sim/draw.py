import pygame
import math

def draw_grid(camera, sim_surface, sim_rect):
    # disegna griglia (sul sim_surface, convertendo in coordinate locali)
    grid_spacing_world = 50
    top_left_world = camera.screen_to_world((sim_rect.left, sim_rect.top))
    bottom_right_world = camera.screen_to_world((sim_rect.right, sim_rect.bottom))
    x0 = math.floor(top_left_world.x / grid_spacing_world) * grid_spacing_world
    x1 = math.ceil(bottom_right_world.x / grid_spacing_world) * grid_spacing_world
    y0 = math.floor(top_left_world.y / grid_spacing_world) * grid_spacing_world
    y1 = math.ceil(bottom_right_world.y / grid_spacing_world) * grid_spacing_world

    for gx in range(int(x0), int(x1) + 1, grid_spacing_world):
        p1 = camera.world_to_screen((gx, y0))
        p2 = camera.world_to_screen((gx, y1))
        p1_local = (int(p1.x - sim_rect.left), int(p1.y - sim_rect.top))
        p2_local = (int(p2.x - sim_rect.left), int(p2.y - sim_rect.top))
        pygame.draw.line(sim_surface, (50, 50, 50), p1_local, p2_local, 1)

    for gy in range(int(y0), int(y1) + 1, grid_spacing_world):
        p1 = camera.world_to_screen((x0, gy))
        p2 = camera.world_to_screen((x1, gy))
        p1_local = (int(p1.x - sim_rect.left), int(p1.y - sim_rect.top))
        p2_local = (int(p2.x - sim_rect.left), int(p2.y - sim_rect.top))
        pygame.draw.line(sim_surface, (50, 50, 50), p1_local, p2_local, 1)

# Funzione per disegnare il grafo centrato
def draw_graph_centered(G, pos, mode, show_labels, traffic_lights, sim_surface, graph_box, screen, myfont, camera):
    #pygame.draw.rect(sim_surface, (30, 33, 39), sim_rect_coord)
    sim_surface.fill((30, 33, 39))
    draw_grid(camera, sim_surface, sim_surface.get_rect(topleft=(10, 10)))

    if mode == 'grid':
        # disegna archi
        for u, v in G.edges():
            pygame.draw.line(sim_surface, (100,100,100), pos[u], pos[v], 2)
            # mostra labels key event
            if show_labels:
                mx = (pos[u][0] + pos[v][0]) / 2
                my = (pos[u][1] + pos[v][1]) / 2
                lbl_edge = myfont.render(f"{u}-{v}", True, (150, 150, 150))
                screen.blit(lbl_edge, (mx, my))
        # disegna nodi
        for n, attr in G.nodes(data=True):
            # print("nodo:", n, "attributi:", attr)
            x, y = pos[n]
            if attr['tipo'] == "POI":
                pygame.draw.circle(sim_surface, (255, 165, 0), (int(x), int(y)), 10) # arancione per POI
            elif attr['tipo'] == "incrocio":
                pygame.draw.circle(sim_surface, (0, 0, 255), (int(x), int(y)), 10) # verde per incroci
                pygame.draw.circle(sim_surface, (0, 255, 0), (int(x)+5, int(y)+5), 5)
                if n in traffic_lights:
                    tl = traffic_lights[n]
                    for i, (u, v) in enumerate(tl.incoming_edges):
                        x1, y1 = pos[u]
                        x2, y2 = pos[v]
                        dx, dy = x2 - x1, y2 - y1
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            continue
                        # piccolo offset dal nodo verso l’arco entrante
                        sx = x2 - dx / dist * 20
                        sy = y2 - dy / dist * 20
                        color = (0, 255, 0) if tl.is_green((u, v)) else (255, 0, 0)
                        pygame.draw.circle(sim_surface, color, (int(sx), int(sy)), 6)

            else:
                pygame.draw.circle(sim_surface, (200, 200, 200), (int(x), int(y)), 7)
            # mostra labels key event
            if show_labels:
                lbl_node = myfont.render(f"{n}", True, (255, 0, 0))
                screen.blit(lbl_node, (int(x)+8, int(y)-20))
    else:
        x_pos = [p[0] for p in pos.values()]
        y_pos = [p[1] for p in pos.values()]
        min_x, max_x = min(x_pos), max(x_pos)
        min_y, max_y = min(y_pos), max(y_pos)

        width = max_x - min_x
        height = max_y - min_y
        scaled_pos = {}
        # ridimensiona e centra le posizioni
        for node, (x, y) in pos.items():
            scaled_x = (graph_box.left) + ((x - min_x) / width) * graph_box.width
            scaled_y = (graph_box.top) + ((y - min_y) / height) * graph_box.height
            scaled_pos[node] = (scaled_x, scaled_y)
            


        # disegna archi
        for u, v in G.edges:
            pygame.draw.line(sim_surface, (100,100,100), scaled_pos[u], scaled_pos[v], 2)
            if show_labels:
                mx = (scaled_pos[u][0] + scaled_pos[v][0]) / 2
                my = (scaled_pos[u][1] + scaled_pos[v][1]) / 2
                lbl_edge = myfont.render(f"{u}-{v}", True, (150, 150, 150))
                sim_surface.blit(lbl_edge, (mx, my))
        # disegna nodi
        for node, (x, y) in scaled_pos.items():
            if G.nodes[node]['tipo'] == "POI":
                pygame.draw.circle(sim_surface, (255, 165, 0), (int(x), int(y)), 10) # arancione per POI
            elif G.nodes[node]['tipo'] == "incrocio":
                pygame.draw.circle(sim_surface, (0, 0, 255), (int(x), int(y)), 10) # verde per incroci
                if node in traffic_lights:
                    tl = traffic_lights[node]
                    for i, (u, v) in enumerate(tl.incoming_edges):
                        x1, y1 = scaled_pos[u]
                        x2, y2 = scaled_pos[v]
                        dx, dy = x2 - x1, y2 - y1
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            continue
                        # piccolo offset dal nodo verso l’arco entrante
                        sx = x2 - dx / dist * 20
                        sy = y2 - dy / dist * 20
                        color = (0, 255, 0) if tl.is_green((u, v)) else (255, 0, 0)
                        pygame.draw.circle(sim_surface, color, (int(sx), int(sy)), 6)
            else:
                pygame.draw.circle(sim_surface, (200, 200, 200), (int(x), int(y)), 7)
            if show_labels:
                if G.nodes[node]['tipo'] == "POI":
                    lbl_node = myfont.render(f"{G.nodes[node]['nome']}", True, (255, 0, 0))
                else:
                    lbl_node = myfont.render(f"{node}", True, (255, 0, 0))
                sim_surface.blit(lbl_node, (int(x)+8, int(y)-20))

# Funzione per disegnare il grafo
def draw_graph(G, pos, show_labels, traffic_lights, sim_surface, camera, myfont):
    sim_surface.fill((30, 33, 39))
    draw_grid(camera, sim_surface, sim_surface.get_rect(topleft=(10, 10)))
    for u, v in G.edges:
        p1 = camera.world_to_screen(pos[u])
        p2 = camera.world_to_screen(pos[v])
        # disegna solo se almeno parzialmente visibile sullo schermo (controllo veloce)
        pygame.draw.line(sim_surface, (200, 200, 200), p1, p2, 2)
        if show_labels:
                mx = (camera.world_to_screen(pos[u])[0] + camera.world_to_screen(pos[v])[0]) / 2
                my = (camera.world_to_screen(pos[u])[1] + camera.world_to_screen(pos[v])[1]) / 2
                lbl_edge = myfont.render(f"{u}-{v}", True, (150, 150, 150))
                sim_surface.blit(lbl_edge, (mx, my))

    for node, attr in G.nodes(data = True):
        p = camera.world_to_screen(pos[node])
        r = max(5, int(10 * camera.scale))  # raggio scalabile con lo zoom
        
        if G.nodes[node]['tipo'] == "POI":
                pygame.draw.circle(sim_surface, (255, 165, 0), (int(p.x), int(p.y)), r) # arancione per POI
        elif G.nodes[node]['tipo'] == "incrocio":
            pygame.draw.circle(sim_surface, (0, 0, 255), (int(p.x), int(p.y)), r) # blu per incroci
            if node in traffic_lights:
                tl = traffic_lights[node]
                
                if show_labels:
                    r1 = int(tl.detection_radius * camera.scale)  # raggio scalabile con lo zoom per incroci
                    pygame.draw.circle(sim_surface, (88, 88, 252), (int(p.x), int(p.y)), r1, 3) 

                for i, (u, v) in enumerate(tl.incoming_edges):
                    x1, y1 = camera.world_to_screen(pos[u])
                    x2, y2 = camera.world_to_screen(pos[v])
                    dx, dy = x2 - x1, y2 - y1
                    dist = math.hypot(dx, dy)
                    if dist == 0:
                        continue
                    # piccolo offset dal nodo verso l’arco entrante
                    dir_x = dx / dist
                    dir_y = dy / dist

                    offset_dist = r + 6

                    sx = x2 - dir_x * offset_dist
                    sy = y2 - dir_y * offset_dist
                    color = (0, 255, 0) if tl.is_green((u, v)) else (255, 0, 0)
                    pygame.draw.circle(sim_surface, color, (int(sx), int(sy)), max(3, int(4 * camera.scale)))
        else:
            pygame.draw.circle(sim_surface, (200, 200, 200), (int(p.x), int(p.y)), r)
        if show_labels:
                lbl_node = myfont.render(f"{node}", True, (255, 0, 0))
                sim_surface.blit(lbl_node, (int(p.x)+8, int(p.y)-20))
