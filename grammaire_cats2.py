import time
import tracemalloc

# def de classe pour gestion de l'objet 

class Categories : 

    # constructeur de l'objet 
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

#  parenthèse de lecture 
    def __str__(self):
        if self.is_basic: 
            return str(self.left)
        l_str = str(self.left) if isinstance(self.left, str) or getattr(self.left, 'is_basic', False) else f"({self.left})"
        r_str = str(self.right) if getattr(self.right, 'is_basic', False) else f"({self.right})"
        return f"{l_str}{self.slash}{r_str}"
    
# pour coordination
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
        
        # comparaison récursive !!! boucle infinie
        left_match = self.left.matches(other.left) if hasattr(self.left, 'matches') else (self.left == other.left)
        right_match = self.right.matches(other.right) if hasattr(self.right, 'matches') else (self.right == other.right)
        
        return self.slash == other.slash and left_match and right_match
    
# ------------ fin classe ------

def charger_phrases(filename):
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
    lexique = {}
    with open(filename, 'r', encoding= 'utf-8') as f:
        lignes = f.readline()
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
    return lexique

# nettoyage du lexique + gestion parenthèse inutle (comme fichier séparé maintenant plus besoin ??)
def clean_categories(s, word=None):
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
        
        if not any(c in s for c in ["/", "\\"]):
            return Categories(s, word=word)
        
    # lecture pour trouver 1er item à droite par recherche de slash
        depth, split_idx = 0, -1
        for i in range(len(s)-1, -1, -1):
            if s[i] == ")": depth += 1
            elif s[i] == "(": depth -= 1
            elif depth == 0 and s[i] in ["/", "\\"]:
                split_idx = i; 
                break
            
    # refait tout jusqu'à avoir plus rien (attention récursif mettre gestion erreur)
        if split_idx != -1:
            return Categories(clean_categories(s[:split_idx]), s[split_idx], clean_categories(s[split_idx+1:]), word=word)
        return Categories(s, word=word)

# Règles 
# moule pour essayer de gérer le "et" sans avoir 10k entrées dans le lexique 
def substitute_x(template, concrete):
    """
    Remplace X par la catégorie concrète lors d'une 
    coordination pour la recherche
    """
    if getattr(template, 'is_basic', isinstance(template, str)):
        t_val = template.left if hasattr(template, 'left') else template
        return concrete if t_val == "X" else Categories(t_val)
    return Categories(substitute_x(template.left, concrete), template.slash, substitute_x(template.right, concrete))

def appli_norm(l, r):
    if l.slash == "/" and l.right.matches(r):
        res = substitute_x(l.left, r) if "X" in str(l) else l.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, ">"))
    return None

def appli_inverse(l, r):
    if r.slash == "\\" and r.right.matches(l):
        res = substitute_x(r.left, l) if "X" in str(r) else r.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, "<"))
    return None

def compo_harmo(l, r):
    if l.slash == "/" and r.slash == "/" :
        if l.right.matches(r.left):
            return Categories(l.left, "/", r.right, origin=(l, r, "> B"))
    return None

def compo_inverse(l, r):
    if r.slash == "\\" and l.slash == "\\":
        if r.right.matches(l.left):
            return Categories(r.left, "\\", l.left, origin=(l, r, "< B"))
    return None

def type_raising(c):
    if c.is_basic and c.left == "NP":
        s = Categories("S")
        s_np = Categories(Categories("S"), "\\", Categories("NP"))
        return Categories(s, "/", s_np, origin=(c, None, "> T"))
    return None

# Algo principal

def prog_cat(sentence, lexicon, use_tr=True):
    start_t = time.perf_counter() # prépare pour calcul temps
    tracemalloc.start() # impact mémoire
    words = sentence.split()
    n = len(words)
    
    # crée liste avec succes et 
    chart = [[{"succes": [], "stop": []} for _ in range(n + 1)] for _ in range(n + 1)]
    nb_comb = 0

    # chargement lexique
    for i, word in enumerate(words):
        if word in lexicon:
            for cat_str in lexicon[word]:
                c = clean_categories(cat_str, word=word)
                chart[i][i+1]["succes"].append(c)
                if use_tr:
                    tr = type_raising(c)
                    if tr: chart[i][i+1]["succes"].append(tr)
        else:
            chart[i][i+1]["succes"].append(Categories("???", word=word))
            
    # boucle de recherche
    for span in range(2, n + 1):
        for i in range(n - span + 1):
            j = i + span
            for k in range(i + 1, j):

                # COORDINATION
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

                # BINAIRE
                for left in chart[i][k]["succes"]:
                    for right in chart[k][j]["succes"]:
                        if (left.word or '').lower() == 'et' or (right.word or '').lower() == 'et': 
                            continue

                        nb_comb += 1
                        found_rule = False

                        # On teste les règles
                        for res in [appli_norm(left, right), appli_inverse(left, right), 
                                     compo_harmo(left, right), compo_inverse(left, right)]:
                            if res: 
                                chart[i][j]["succes"].append(res)
                                found_rule = True
                        
                        # SI RIEN NE MARCHE -> Stop = trouve pas de règles/combinaison à appliquer 
                        if not found_rule:
                            chart[i][j]["stop"].append((left, right))

    # récupération tps / mémoire                     
    exec_t = (time.perf_counter() - start_t) * 1000
    courant, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    pic_kb = pic / 1024
    # On cherche les succès finaux
    valid = [s for s in chart[0][n]["succes"] if str(s) in ["S", "NP"]]

    return valid, nb_comb, exec_t, chart, pic_kb

# gestion dessin arbre 
def recup_frag_abandon(chart, n):
    """ 
    test fct pour récup en mémoire les fragments abandonnés

    """
    dp = {0: (0, [])} #  = (nombre_de_morceaux, liste_des_categories)
    
    for j in range(1, n + 1):
        best = (float('inf'), [])
        for i in range(j):
            if i in dp and chart[i][j]["succes"]:
                # pour le visuel
                cat = chart[i][j]["succes"][0]
                cand_cost = dp[i][0] + 1
                if cand_cost < best[0]:
                    best = (cand_cost, dp[i][1] + [cat])
        dp[j] = best
        
    return dp[n][1]

# on garde les échecs - construction ?
def arbre_echec(fragments):
    """ 
    génère arbre de rupture 
    
    """
    if not fragments: 
        return None
    
    trees = [recup_strc_arbre(cat) for cat in fragments]
    while len(trees) > 1:
        left = trees.pop(0)
        right = trees.pop(0)
        # visuel quand marche pas 
        fake_node = {
            "result": "<span style='color:#d63031; font-weight:bold;'>RUPTURE</span>", 
            "rule": "NOPE", 
            "left": left, 
            "right": right
        }
        trees.insert(0, fake_node)
    return trees[0]


# Construction arbres 

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

def tree_to_html(tree, title, nb_tests=0, extra_class_cat="cat-with-bar"):
    if not tree:
        return ""

    def get_words(node):
        if "word" in node: return [node]
        words = []
        for k in ["left", "mid", "right"]:
            if k in node and node[k] is not None: words += get_words(node[k])
        return words

    words_list = get_words(tree)
    n = len(words_list)
    grid, max_row = {}, 0

    for i, w in enumerate(words_list):
        cat_disp = w["cat"]
        if w.get("word", "").lower().strip() == "et":
            cat_disp = r"X\X/X"
        grid[(0, i)] = {"cat": cat_disp, "width": 1, "rule": None}

    def fill_grid(node):
        nonlocal max_row
        if "word" in node: 
            return 0, next(i for i, w in enumerate(words_list) if w == node), 1
        
        # Gestion récursive pour remplir la grille (identique à ton code actuel)
        if "left" in node and "right" not in node and "mid" not in node:
            r1, c1, w1 = fill_grid(node["left"])
            row = r1 + 1
            grid[(row, c1)] = {"cat": node["result"], "width": w1, "rule": node["rule"]}
            max_row = max(max_row, row)
            return row, c1, w1
        
        if "mid" in node: 
            r1, c1, w1 = fill_grid(node["left"])
            r2, c2, w2 = fill_grid(node["mid"])
            r3, c3, w3 = fill_grid(node["right"])
            row = max(r1, r2, r3) + 1
            grid[(row, c1)] = {"cat": node["result"], "width": w1+w2+w3, "rule": node["rule"]}
            max_row = max(max_row, row)
            return row, c1, w1+w2+w3
        
        r1, c1, w1 = fill_grid(node["left"])
        r2, c2, w2 = fill_grid(node["right"])
        row = max(r1, r2) + 1
        grid[(row, c1)] = {"cat": node["result"], "width": w1+w2, "rule": node["rule"]}
        max_row = max(max_row, row)
        return row, c1, w1+w2

    fill_grid(tree)
    
    html = f"<h3>{title}</h3><table class='ccg'><tr>"
    
    # Ligne des mots
    for w in words_list: 
        html += f'<td class="word">{w["word"]}</td>'
    html += '</tr>'
    
    # Lignes de dérivation
    for r in range(max_row + 1):
        html += '<tr>'
        c = 0
        while c < n:
            if (r, c) in grid:
                cell = grid[(r, c)]
                label = (cell["rule"] or "").replace("<", "&lt;").replace(">", "&gt;")
                
                # Pas de pointillé sous le S final (dernière ligne)
                current_class = extra_class_cat if r < max_row else ""
                
                html += f'<td colspan="{cell["width"]}" class="{current_class}">'
                if cell["rule"]: 
                    html += f'<div class="line"><span class="rule">{label}</span></div>'
                html += f'<div class="cat">{cell["cat"]}</div></td>'
                c += cell["width"]
            else: 
                # Cellule vide : on prolonge le pointillé si on n'est pas tout en bas
                html += '<td class="empty-cell"></td>'
                c += 1
        html += '</tr>'
    return html + '</table><hr>'


# TEST => mettre dans un autre fichier à ouvrir ?
lexique_test= charger_lexique("base_lexicale.txt")
phrases_test = charger_phrases("phrases.txt")


# def du CSS à intégrer dans le html 



global_style = r"""
<style>
    body { font-family: sans-serif; background: #ffffff; padding: 40px; color:#2d3436; line-height: 1.5; }
    h1 { border-bottom: 2px solid #2d3436; padding-bottom: 10px; margin-bottom: 30px; }
    
    .phrase-container { margin-bottom: 30px; border: 1px solid #ccc; border-radius: 4px; }
    summary { padding: 15px; cursor: pointer; font-weight: bold; background: #f8f9fa; border-bottom: 1px solid #ccc; font-size: 1.2em; }
    .content { padding: 20px; }

    .stats-text { font-weight: normal; color: #636e72; margin-left: 20px; font-size: 0.8em; }

    /* --- REGLAGES DE L'ARBRE --- */
    .ccg { border-collapse: collapse; margin: 40px 0; }
    
    .ccg td { 
        text-align: center; 
        vertical-align: top; 
        padding: 0; 
        min-width: 150px; 
        background-image: none !important; 
    }

    /* ESPACEMENT DES MOTS : On donne de l'air ici */
    .word { 
        font-weight: bold; 
        font-size: 1.5em; 
        padding: 20px 10px 50px 10px !important; /* 50px de vide sous les mots */
        background: white;
        position: relative;
        z-index: 10;
    }

    .cat { 
        font-family: monospace; 
        font-size: 1.2em; 
        margin-bottom: 35px; 
        padding: 8px 15px;
        background: white;
        position: relative;
        z-index: 10;
        display: inline-block;
    }

    /* Pointillé vertical */
    .cat-with-bar .cat::after {
        content: "";
        position: absolute;
        bottom: -35px; 
        left: 50%;
        transform: translateX(-50%);
        width: 3px;
        height: 35px;
        background-image: linear-gradient(to bottom, #2d3436 50%, transparent 50%);
        background-size: 3px 12px;
        display: block;
    }

    .empty-cell {
        background-image: linear-gradient(to bottom, #2d3436 50%, transparent 50%) !important;
        background-size: 3px 12px;
        background-position: center top;
        background-repeat: repeat-y;
    }

    /* LA LIGNE HORIZONTALE */
    .line { 
        border-top: 3px solid #2d3436; 
        position: relative; 
        z-index: 20; 
        margin: 0 10px; 
        height: 15px; 
    }

    /* LES RÈGLES (FLÈCHES) */
    .rule { 
        position: absolute; 
        right: -25px; 
        top: -16px; 
        background: white; 
        padding: 0 6px; 
        font-size: 1.1em; 
        font-weight: bold;
        color: #d63031; /* Un rouge discret pour les règles */
    }
</style>
"""

# sortie
rapport = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{global_style}</head><body>"
rapport += "<h1>Sortie ok - Style MEEEEEH</h1>"

for p in phrases_test:
    p_clean = p.replace(".", "").strip()
    words = p_clean.split()
    n = len(words)
    
    valid_sols, nb, t, chart, pic_kb = prog_cat(p_clean, lexique_test)
    
    
    rapport += f"""
    <details  class="phrase-container">
        <summary>« {p} »
            <span class="stats-text">{t:.2f} ms | {nb} combinaisons | {pic_kb:.2f} KB</span>
        </summary>
        <div class="content">
    """

    # gestion arbre succes
    rapport += "<h3>DERIVATIONS : CLAP CLAP</h3>"
    if valid_sols:
        for i, sol in enumerate(valid_sols):
            rapport += tree_to_html(recup_strc_arbre(sol), f"Dérivation {i+1}")
    else:
        rapport += "<p>Aucune solution complète trouvée.</p>"

    # gestion echec finaux
    echecs_finaux = [c for c in chart[0][n]["succes"] if str(c) not in ["S", "NP"]]
    rapport += "<h3>RIP : Structures complètes non-S</h3>"
    if echecs_finaux:
        for i, sol in enumerate(echecs_finaux):
            rapport += tree_to_html(recup_strc_arbre(sol), f"Structure finale {i+1} (Catégorie: {str(sol)})")
    else:
        rapport += "<p>Aucune structure couvrant toute la phrase n'a abouti à une catégorie autre que S ou NP.</p>"

    # gestion arrêt intermédiare
    rapport += "<h3>NOPE : a quitté le navire</h3>"
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
with open("test_sortie.html", "w", encoding="utf-8") as f:
    f.write(rapport)

print("CLAP CLAP : Rapport généré dans 'test_sortie.html'")