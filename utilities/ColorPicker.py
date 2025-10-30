import webcolors

# Trova il nome del colore più vicino per un dato valore RGB
def closest_color(requested_colour):
    min_dist = float("inf")
    closest_name = None
    for name in webcolors.names("css3"):
        # ottieni RGB per il nome
        r_c, g_c, b_c = webcolors.name_to_rgb(name, spec="css3")
        # calcola la distanza (euclidea quadratica)
        d = (r_c - requested_colour[0])**2 + (g_c - requested_colour[1])**2 + (b_c - requested_colour[2])**2
        if d < min_dist:
            min_dist = d
            closest_name = name
    return closest_name

# Ottieni il nome del colore per una tupla RGB
def color_pick(rgb_tuple):
    try:
        # prova un nome esatto
        return webcolors.rgb_to_name(rgb_tuple, spec="css3")
    except ValueError:
        # se non esiste un nome esatto, prendi il più vicino
        return closest_color(rgb_tuple)
