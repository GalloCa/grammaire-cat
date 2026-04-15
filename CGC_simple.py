import time
import tracemalloc
import base64
import io
import matplotlib.pyplot as plt 

# def de classe pour gestion de l'objet 

class Categories :  
    """ 
    On veut ce qui est à gauche du slash = résultat attendu
    left = gauche du slash
    droite = argument attendu
    is_basic = catégorie basique S ou NP, X
    """
    def __init__(self, left, slash=None, right=None, word=None, origin=None):
        self.left = left    
        self.slash = slash  
        self.right = right  
        self.word = word    
        self.origin = origin 
        self.is_basic = slash is None

#  Gestion parenthèse de lecture pour que la machine isole l'item recherché
    def __str__(self):
        if self.is_basic: 
            return str(self.left)
        l_str = str(self.left) if isinstance(self.left, str) or getattr(self.left, 'is_basic', False) else f"({self.left})"
        r_str = str(self.right) if getattr(self.right, 'is_basic', False) else f"({self.right})"
        return f"{l_str}{self.slash}{r_str}"
    
# Fonction de gestion de la coordination X\X/X
    def matches(self, other):
        
        if isinstance(other, str):
            return str(self) == other
        
        # X (coordination)
        if (self.is_basic and self.left == "X") or (other.is_basic and other.left == "X"):
            return True
        
        # Rejet si l'un est basique et l'autre non -> Échec / si pas de correspondance
        if self.is_basic != other.is_basic: 
            return False
        
        # Comparaison des catégories basiques
        if self.is_basic:
            return self.left == other.left
        
        # comparaison récursive !!! boucle infinie si mal géré
        left_match = self.left.matches(other.left) if hasattr(self.left, 'matches') else (self.left == other.left)
        right_match = self.right.matches(other.right) if hasattr(self.right, 'matches') else (self.right == other.right)
        
        return self.slash == other.slash and left_match and right_match
    
# ------------ fin classe ------

def charger_phrases(filename):
    """
    Cette fonction permet de charger les phrases à analyser

    Entrée :
        filename (str) : nom du fichier en .txt
    
    Sortie : 
        phrases (liste) : 

    """
    phrases = []
    try:
        with open(filename, mode='r',encoding='utf-8') as f:
            for ligne in f:
                l = ligne.strip()
                if l and not ligne.startswith("#"):
                    phrases.append(l)
    except FileNotFoundError :
        print(f"Erreur : le fichier {filename} des phrases = non trouvé")
    return phrases


def charger_lexique(filename):
    """
    Cette fonction permet de charger le lexique

    Entrée : 
        filename (str) : nom du fichier en .txt
    Sortie:
        lexique (dictionnaire) :
    """
    lexique = {}
    with open(filename, 'r', encoding= 'utf-8') as f:
        lignes = f.readlines()
        print(len(lignes))
    try:
        with open(filename, mode='r',encoding='utf-8') as f:
            for ligne in f:
                l = ligne.strip()
                if l and not l.startswith("#"):
                    if ":" in ligne:
                        mot, cats = ligne.split(":",1)
                        listes_cats = [c.strip() for c in cats.split(",")]
                        lexique[mot.strip()] = listes_cats
    except FileNotFoundError :
        print(f"Erreur : le fichier {filename} des phrases = non trouvé")
    except Exception as e:
        print(f"erreur lecture du {filename}")
    print(lexique)
    return lexique


def clean_categories(s, word=None):
        r"""
        Cette fonction transforme une chaîne de caractères 
        en une structure arborescente d'objets 'Categories'.
                    
        Logique :
        1.  Supprime les parenthèses redondantes si y'en a (ex: '((S\NP))' -> 'S\NP')
        2. Identifie le connecteur principal (slash ou backslash) situé au niveau 0 
            de nesting (hors parenthèses)
        3. Divise la chaîne en deux et instancie les sous-catégories jusqu'à 
            atteindre les catégories atomiques (S, NP, N, etc.). Attention récursivité ici.
                    
        Entrée :
            s (str): La catégorie sous forme de texte (ex: "(S\NP)/NP").
            word (str, optional): Le mot associé pour la traçabilité dans l'arbre.
                        
        Sortie :
            Categories: Un objet CategoryCategorie (simple ou complexe)."""
        
        # Gestion des parenthèses
        s = s.strip()
        while s.startswith("(") and s.endswith(")"):
            depth, split = 0, True
            for char in s[1:-1]:
                if char == "(": depth += 1
                elif char == ")": depth -= 1
                if depth < 0: split = False; break
            if split: s = s[1:-1].strip()
            else: 
                break
        # Recherche catégorie simple (NP, S)
        if not any(c in s for c in ["/", "\\"]):
            return Categories(s, word=word)
        
        # Cherche le \ ou / principal pour trouver 1ère catégorie à droite
        depth, split_idx = 0, -1
        for i in range(len(s)-1, -1, -1):
            if s[i] == ")": depth += 1
            elif s[i] == "(": depth -= 1
            elif depth == 0 and s[i] in ["/", "\\"]:
                split_idx = i; 
                break
            
        # Construction récursive de l'objet, construit les sous-catégorie jusqu'à arriver à S ou NP
        if split_idx != -1:
            return Categories(clean_categories(s[:split_idx]), s[split_idx], clean_categories(s[split_idx+1:]), word=word)
        
        return Categories(s, word=word)

# REGLES

# moule pour essayer de gérer le "et" sans avoir 10k entrées dans le lexique 
def substitut_x(template, concrete):
    """
    Remplace X par la catégorie concrète lors d'une 
    coordination pour la recherche
    """
    if getattr(template, 'is_basic', isinstance(template, str)):
        t_val = template.left if hasattr(template, 'left') else template
        return concrete if t_val == "X" else Categories(t_val)
    return Categories(substitut_x(template.left, concrete), template.slash, substitut_x(template.right, concrete))

def appli_norm(l, r):
    """

    """
    if l.slash == "/" and l.right.matches(r):
        res = substitut_x(l.left, r) if "X" in str(l) else l.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, ">"))
    return None

def appli_inverse(l, r):
    """
    
    """
    if r.slash == "\\" and r.right.matches(l):
        res = substitut_x(r.left, l) if "X" in str(r) else r.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, "<"))
    return None

def compo_harmo(l, r):
    """
    
    """
    if l.slash == "/" and r.slash == "/" :
        if l.right.matches(r.left):
            return Categories(l.left, "/", r.right, origin=(l, r, "> B"))
    return None

def compo_inverse(l, r):
    """
    
    """
    if r.slash == "\\" and l.slash == "\\":
        if r.right.matches(l.left):
            return Categories(r.left, "\\", l.right, origin=(l, r, "< B"))
    return None

def type_raising(c):
    """

    """
    if c.is_basic and c.left == "NP":
        s = Categories("S")
        s_np = Categories(Categories("S"), "\\", Categories("NP"))
        return Categories(s, "/", s_np, origin=(c, None, "> T"))
    return None


# ALGORITHME PRINCIPAL
def prog_cat(sentence, lexicon, use_tr=True):
    r"""
    L'algorithme remplit une table de hachage (chart) 
    en combinant les catégories lexicales selon les règles d'application, de composition
    et type-raising
    

    Entrées :
        sentence (str): La phrase à analyser
        lexicon (dict): Le dictionnaire contenant les catégories associées aux mots
        use_tr (bool): Active ou désactive le Type-Raising (NP -> S/(S\NP))

    Sortie :
        tuple: (valid_sols, nb_comb, exec_time, full_chart, peak_memory)
    """

    # Mise en place d'un monitoring des performances (temps et mémoire)
    start_t = time.perf_counter() 
    tracemalloc.start() 

    words = sentence.split()
    n = len(words)
    stats_evolution = []
    
    # Initialisation de la matrice chart
        # Succes : catégories valides
        # Stop : quand et où le programme stop pour débug / sortie 
    chart = [[{"succes": [], "stop": []} for _ in range(n + 1)] for _ in range(n + 1)]
    nb_comb = 0

    # Remplissage de la matrice
    for i, word in enumerate(words):
        if word in lexicon:
            for cat_str in lexicon[word]:
                c = clean_categories(cat_str, word=word)
                chart[i][i+1]["succes"].append(c)
                # Gestion type-rasing
                if use_tr:
                    tr = type_raising(c)
                    if tr: chart[i][i+1]["succes"].append(tr)
        else:
            # Gestion des mots inconnus
            chart[i][i+1]["succes"].append(Categories("???", word=word))
            
    # DEBUT BOUCLE DE RECHERCHE 
    for span in range(2, n + 1):
        for i in range(n - span + 1):
            j = i + span
            for k in range(i + 1, j):

                # GESTION DU CAS DE LA COORDINATION
                if j - i >= 3:
                    for k2 in range(k + 1, j):
                        for c1 in chart[i][k]["succes"]:
                            for c2 in chart[k][k2]["succes"]:
                                if (c2.word or '').lower() == 'et':
                                    for c3 in chart[k2][j]["succes"]:
                                        nb_comb += 1
                                        if c1.matches(c3):
                                            res = Categories(c1.left, c1.slash, c1.right, origin=(c1, c2, c3, "<*>"))
                                            chart[i][j]["succes"].append(res)

                # cAS GENERAL / REGLES BINAIRES 
                for left in chart[i][k]["succes"]:
                    for right in chart[k][j]["succes"]:
                        if (left.word or '').lower() == 'et' or (right.word or '').lower() == 'et': 
                            continue

                        nb_comb += 1
                        found_rule = False

                        # Test séquentiel de nos règles combinatoires
                        for res in [appli_norm(left, right), 
                                    appli_inverse(left, right), 
                                    compo_harmo(left, right), 
                                    compo_inverse(left, right)]:
                            if res: 
                                chart[i][j]["succes"].append(res)
                                found_rule = True
                        
                        # Stockage des échecs pour l'affichage et analyse 
                        if not found_rule:
                            chart[i][j]["stop"].append((left, right))
        current_t = (time.perf_counter() - start_t) * 1000
        _, pic = tracemalloc.get_traced_memory()
        stats_evolution.append((span, current_t, nb_comb, pic / 1024))

    # Module de récupération du temps et de la mémoire                  
    exec_t = (time.perf_counter() - start_t) * 1000
    _, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    pic_kb = pic / 1024

    # Fitrage des résultats des succès : dérivation complète avec S en final
    valid = [s for s in chart[0][n]["succes"] if str(s) == "S"]

    return valid, nb_comb, exec_t, chart, pic_kb, stats_evolution


# RECUPERATION DES DONNEES PORU CONSTRUIRE LES ARBRES
def recup_frag_abandon(chart, n):
    """ 
    test fct pour récup en mémoire les fragments abandonnés

    """
    dp = {0: (0, [])} #  (nombre_de_morceaux, liste_des_categories)
    
    for j in range(1, n + 1):
        best = (float('inf'), [])
        for i in range(j):
            if i in dp and chart[i][j]["succes"]:
                cat = chart[i][j]["succes"][0]
                cand_cost = dp[i][0] + 1
                if cand_cost < best[0]:
                    best = (cand_cost, dp[i][1] + [cat])
        dp[j] = best
        
    return dp[n][1]


def recup_strc_arbre(cat):
    """
    récupère mémoire pour génération des arbres 
    attention récursif = faire gestion des erreurs 

    """
    if not cat.origin: 
        return {"word": cat.word, "cat": str(cat)}
    if len(cat.origin) == 4:
        c1, c2, c3, rule = cat.origin
        return {"result": str(cat), 
                "rule": rule, 
                "left": recup_strc_arbre(c1), 
                "mid": recup_strc_arbre(c2), 
                "right": recup_strc_arbre(c3)
                }
    
    l, r, rule = cat.origin
    if r is None: 
        return {"result": str(cat), 
                "rule": rule, 
                "left": recup_strc_arbre(l)
                }

    return {"result": str(cat), 
            "rule": rule, 
            "left": recup_strc_arbre(l), 
            "right": recup_strc_arbre(r)
            }

# GESTION DES ARBRES DE DERIVATION EN HTML
def tree_to_html(tree, title, **kwargs):
    if not tree:
        return ""

    # CONFIGURATION & STYLE
    cfg = {
        "col_w": 150,        
        "row_h": 70,         
        "lex_h": 60,         
        "word_y": 30,        
        "bar_width": 2.5,    
        "colors": {
            "stem": "#636e72",
            "bar": "#2d3436",
            "rule": "#d63031",
            "word": "#2d3436",
            "cat": "#2d3436",
            "final": "#0984e3" #  bleu pour le S final ?
        },
        "dash": "4,4"
    }

    
    def get_leaves(node):
        """
        """
        if "word" in node: return [node]
        leaves = []
        for k in ("left", "mid", "right"):
            if node.get(k): leaves += get_leaves(node[k])
        return leaves

    leaves = get_leaves(tree)
    n = len(leaves)
    # Map l'ID de l'objet vers son index de colonne
    leaf_col = {id(lf): i for i, lf in enumerate(leaves)}

    # ── 2. CALCUL DU LAYOUT (Récursif) ──
    cells = []

    def layout(node):
        """
        """
        if "word" in node:
            col = leaf_col[id(node)]
            return 0, col, 1, (col + 0.5) * cfg["col_w"], cfg["word_y"] + cfg["lex_h"]  # row, col, span, cx, bottom_y # row, col, span, x_center

        # Calcul récursif des enfants
        children = [node[k] for k in ("left", "mid", "right") if node.get(k)]
        child_res = [layout(c) for c in children]

        # Logique de positionnement
        my_row = max(r for r, _, _, _, _ in child_res) + 1
        col_min = min(c for _, c, _, _, _ in child_res)
        col_max = max(c + w - 1 for _, c, w, _, _ in child_res)
        my_span = col_max - col_min + 1
        my_cx = (col_min + my_span / 2) * cfg["col_w"]

        my_bottom_y = cfg["word_y"] + cfg["lex_h"] + 10 + (my_row - 1) * cfg["row_h"] + 45

        cells.append({
            "row": my_row,
            "cx": my_cx,
            "span": my_span,
            "cat": node.get("result", "???"),
            "rule": node.get("rule", ""),
            "stems": [(cx, by) for _, _, _, cx, by in child_res],
            "is_final": (node.get("result") == "S") 
        })
        return my_row, col_min, my_span, my_cx, my_bottom_y

    max_row, _, _, _, _ = layout(tree)

    # GÉNÉRATION SVG 
    total_h = cfg["word_y"] + cfg["lex_h"] + (max_row * cfg["row_h"]) + 40
    total_w = n * cfg["col_w"] + 80
    
    elements = []
    
    # 
    def svg_text(x, y, text, size=14, weight="normal", color="#000", anchor="middle"):
        clean_txt = str(text).replace("<", "&lt;").replace(">", "&gt;")
        return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}">{clean_txt}</text>'

    # 
    def svg_line(x1, y1, x2, y2, color, width=1, dash=None):
        style = f'stroke:{color};stroke-width:{width}'
        if dash: style += f';stroke-dasharray:{dash}'
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="{style}" />'

    # Rendu des mots et catégories lexicales 
    lex_cat_y = cfg["word_y"] + cfg["lex_h"]
    for i, lf in enumerate(leaves):
        cx = (i + 0.5) * cfg["col_w"]
        # Mot
        elements.append(svg_text(cx, cfg["word_y"], lf.get("word", "?"), size=18, weight="bold", color=cfg["colors"]["word"]))
        # Pointillé lexical
        elements.append(svg_line(cx, cfg["word_y"]+10, cx, lex_cat_y-20, cfg["colors"]["stem"], dash=cfg["dash"]))
        # Catégorie lexicale
        cat = lf.get("cat", "???")
        if (lf.get("word") or "").lower() == "et": cat = r"X\X/X"
        elements.append(svg_text(cx, lex_cat_y, cat, size=13, color=cfg["colors"]["cat"]))

    # Rendu des dérivations 
    def get_y(row, part="bar"):
        base_y = lex_cat_y + 10 + (row - 1) * cfg["row_h"]
        return base_y + 20 if part == "bar" else base_y + 45

    for c in sorted(cells, key=lambda x: x["row"]):
        r_y_bar = get_y(c["row"], "bar")
        r_y_cat = get_y(c["row"], "cat")
        
        # Pointillés montants des enfants
        for sx, sy in c["stems"]:
            elements.append(svg_line(sx, sy, sx, r_y_bar, cfg["colors"]["stem"], dash=cfg["dash"]))

        x1, x2 = min(s[0] for s in c["stems"]), max(s[0] for s in c["stems"])

        # Barre de règle
        if x1 == x2: x1, x2 = x1 - 30, x2 + 30 # Type-raising
        elements.append(svg_line(x1, r_y_bar, x2, r_y_bar, cfg["colors"]["bar"], width=cfg["bar_width"]))
        
        # Étiquette de règle
        elements.append(svg_text(x2 + 8, r_y_bar + 5, c["rule"], size=11, weight="bold", color=cfg["colors"]["rule"], anchor="start"))

        # Pointillé vers le résultat
        elements.append(svg_line(c["cx"], r_y_bar, c["cx"], r_y_cat - 15, cfg["colors"]["stem"], dash=cfg["dash"]))

        # Texte Résultat
        is_final = (c["cat"] == "S" and c["row"] == max_row)
        color = cfg["colors"]["final"] if is_final else cfg["colors"]["cat"]
        weight = "bold" if is_final else "normal"
        elements.append(svg_text(c["cx"], r_y_cat, c["cat"], size=14, weight=weight, color=color))

    # Assemblage final
    svg_content = "\n  ".join(elements)
    svg_tag = f'<svg width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg" style="background:white; display:block; margin:auto;">\n  {svg_content}\n</svg>'
    
    return f"<div class='derivation'><h3>{title}</h3>{svg_tag}</div><hr>"

def get_phrase_line_graph(stats_evolution):
    """
    
    """
    if not stats_evolution: return ""
    
    # Extraction des données
    spans, temps, combs, mems = zip(*stats_evolution)
    
    # Création de la figure 
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4))
    
    # Graph 1 : Temps
    ax1.plot(spans, temps, color='#d63031', marker='o', linewidth=2)
    ax1.set_title("Évolution Temps (ms)")
    ax1.set_xlabel("Longueur du span")
    ax1.grid(True, alpha=0.3)

    # Graph 2 : Unifications 
    ax2.plot(spans, combs, color='#0984e3', marker='s', linewidth=2)
    ax2.set_title("Nombre de résolution")
    ax2.set_xlabel("Longueur du span")
    ax2.grid(True, alpha=0.3)

    # Graph 3 : Mémoire 
    ax3.plot(spans, mems, color='#00b894', marker='^', linewidth=2)
    ax3.set_title("Pic Mémoire (KB)")
    ax3.set_xlabel("Longueur du span")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    
    # Encodage Base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f'<div style="text-align:center; margin: 20px 0;"><img src="data:image/png;base64,{img_str}" style="width:100%; max-width:1100px; border:1px solid #eee;"></div>'

# MAIN
lexique_test= charger_lexique("data/base_lexicale_simple.txt")
phrases_test = charger_phrases("data/phrases_simple.txt")


# DEFINITION DU CSS DE NOTRE SORTIE HTML
global_style = r"""
<style>
    body { font-family: sans-serif; background: #ffffff; padding: 40px; color: #2d3436; }
h1 { border-bottom: 2px solid #2d3436; padding-bottom: 10px; margin-bottom: 30px; }
.phrase-container { margin-bottom: 30px; border: 1px solid #ccc; border-radius: 4px; }
summary { padding: 15px; cursor: pointer; font-weight: bold; background: #f8f9fa; border-bottom: 1px solid #ccc; font-size: 1.2em; }
.content { padding: 20px; }
.stats-text { font-weight: normal; color: #636e72; margin-left: 20px; font-size: 0.8em; }

/* ── Table CCG ── */
table.ccg { border-collapse: collapse; margin: 32px 0; }

/* Mots */
td.word {
  font-weight: bold;
  font-size: 1.4em;
  text-align: center;
  padding: 16px 18px 0 18px;
  vertical-align: bottom;
}

/* Rangée lexicale */
td.lex {
  text-align: center;
  vertical-align: top;
  padding: 0 12px;
}

/* Rangée de dérivation */
td.deriv {
  text-align: center;
  vertical-align: top;
  padding: 0 4px;
}

/* Pointillé vertical (connexion mot→catégorie et catégorie→barre) */
.stem {
  width: 1px;
  height: 28px;
  margin: 0 auto;
  background: repeating-linear-gradient(
    to bottom,
    #636e72 0, #636e72 4px,
    transparent 4px, transparent 8px
  );
}

/* Barre horizontale de règle */
.rule-bar {
  border-top: 2.5px solid #2d3436;
  margin: 0 auto;
  position: relative;
  height: 0;
}

/* Étiquette de règle (>, <B, …) */
.rule-label {
  position: absolute;
  right: -30px;
  top: -12px;
  font-size: 0.95em;
  font-weight: bold;
  color: #d63031;
  background: #fff;
  padding: 0 4px;
  white-space: nowrap;
}

/* Catégorie */
.cat {
  font-family: monospace;
  font-size: 1.1em;
  padding: 6px 12px 4px;
  white-space: nowrap;
  display: inline-block;
}
</style>
"""

# CREATION DU FICHIER HTML DE SORTIE
rapport = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{global_style}</head><body>"
rapport += "<h1>Sortie ok - Style MEEEEEH</h1>"

for p in phrases_test:
    p_clean = p.replace(".", "").strip()
    words = p_clean.split()
    n = len(words)
    
    valid_sols, nb, t, chart, pic_kb, evolution = prog_cat(p_clean, lexique_test)
    line_graph_html = get_phrase_line_graph(evolution)
    
    rapport += f"""
    <details  class="phrase-container">
        <summary>« {p} »
            <span class="stats-text">{t:.2f} ms | {nb} combinaisons | {pic_kb:.2f} KB</span>
        </summary>
        <div class="content">
            {line_graph_html}  <div class="tech-card"> ... </div>
    """

    # Affichage des arbres de dérivation réussis
    rapport += "<h3>DERIVATIONS : Phrases complètes (S)</h3>"
    if valid_sols:
        for i, sol in enumerate(valid_sols):
            rapport += tree_to_html(recup_strc_arbre(sol), f"Dérivation n°{i+1}")
    else:
        rapport += "<p>Aucune dérivation en S trouvée.</p>"

    # Affichage des échecs : ne trouve pas S à la fin de la dérivation complète
    echecs_finaux = [c for c in chart[0][n]["succes"] if str(c) != "S"]
    rapport += "<h3>ECHECS : Structures complètes finales mais non-S</h3>"
    if echecs_finaux:
        for i, sol in enumerate(echecs_finaux):
            rapport += tree_to_html(recup_strc_arbre(sol), f"Structure finale n°{i+1} (Catégorie: {str(sol)})")
    else:
        rapport += "<p>Structure de dérivation complète mais n'aboutissant pas à S.</p>"

    # Affichage des segments intermédiaire qui ont conduit à un arrêt
    rapport += "<h3>SEGMENTS : Constituants intermédiaires abandonnés</h3>"
    found_abandon = False
    for span in range(n - 1, 1, -1):
        for i_idx in range(n - span + 1):
            j_idx = i_idx + span
            for cat in chart[i_idx][j_idx]["succes"]:
                mots_segment = " ".join(words[i_idx:j_idx])
                rapport += tree_to_html(recup_strc_arbre(cat), f"Segment : « {mots_segment} »")
                found_abandon = True
                
    if not found_abandon:
        rapport += "<p>Aucun segment intermédiaire construit.</p>"

    rapport += "</div></details>"
                    
rapport += "</body></html>"

# Enregistrement final
with open("sortie_CGC_simple.html", "w", encoding="utf-8") as f:
    f.write(rapport)

# Trace succès génération de fichier 
print("Succès, le rapport généré : 'sortie_CGC_simple.html'")
