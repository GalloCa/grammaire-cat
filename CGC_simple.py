




import time
import tracemalloc
import base64
import io
import matplotlib.pyplot as plt 

# CLASSE CATEGORIE

class Categories :  
    """ 
    Représente une catégorie syntaxique en Grammaire Catégorielle.

    Une catégorie est : 
            - Basique : S ou NO
            - Complexe : deux catégorie reliées pas un slash
                         de la forme résultat / argument 
                         ou résultat \\ argument
    
    Attributs : 

    left (str) : la catégorie résultante
    slash (str) : le connecteur ; None pour une catégorie basique
    right (str) : la catégorie argument
    word (str) : le mot du lexique auquel cette catégorie est attachée (sert pour la trace)
    origine (tuple) : décrit la règle qui a produit cette catégorie
    is_basic (bool) : True si la catégorie est basique
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
        """
        Retroune la représentation textuelle de la catégorie
        Les catégories complexes sont parenthésées pour faciliter la lecture du moteur.
        """
        if self.is_basic: 
            return str(self.left)
        l_str = str(self.left) if isinstance(self.left, str) or getattr(self.left, 'is_basic', False) else f"({self.left})"
        r_str = str(self.right) if getattr(self.right, 'is_basic', False) else f"({self.right})"
        return f"{l_str}{self.slash}{r_str}"
    
# Fonction de gestion de la coordination X\X/X
    def matches(self, other):
        r"""
        Cette fonction vérifie si deux catégories sont compatibles pour être unifiées
        La variable X sert de joker pour la coordination : X\X/X
        Toute catégorie concrète est compatible avec X

        Entrées :
            other (str) : la catégorie à comparer
        Sortie :
            bool : True si les deux catégories sont unifiables, False sinon
        """
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
        
        # Comparaison récursive des catégories complexes -- attention
        left_match = self.left.matches(other.left) if hasattr(self.left, 'matches') else (self.left == other.left)
        right_match = self.right.matches(other.right) if hasattr(self.right, 'matches') else (self.right == other.right)
        
        return self.slash == other.slash and left_match and right_match

# CHARGEMENT DES DONNEES
def charger_phrases(filename):
    """
    Cette fonction permet de charger les phrases à analyser

    Entrée :
        filename (str) : nom du fichier en .txt
    
    Sortie : 
        phrases (liste) : liste des phrases chargées, retourne liste vide si fichier introuvable

    """
    phrases = []
    try:
        with open(filename, mode='r',encoding='utf-8') as f:
            for ligne in f:
                l = ligne.strip()
                if l and not ligne.startswith("#"):
                    phrases.append(l)
        print(f"{len(phrases)} phrases chargées depuis {filename}")
    except FileNotFoundError :
        print(f"Erreur : le fichier {filename} des phrases est introuvable")
    except OSError as e :
        print(f"Erreur de lecture du ficher {filename}, erreur : {e}")
    return phrases

def charger_lexique(filename):
    """
    Cette fonction permet de charger le lexique depuis un fichier texte

    Entrée : 
        filename (str) : nom du fichier en .txt
    Sortie:
        lexique (dict) : dictionnaire de forme : {mot1 : [catégorie1, catégorie2,...],
                                                  mot2 : [...],..}
    """
    lexique = {}
    try:
        with open(filename, mode='r',encoding='utf-8') as f:
            for num_ligne, ligne in enumerate(f, start=1):
                l = ligne.strip()
                if not l and l.startswith("#"):
                    continue
                if ":"not in l:
                    print(f"Ligne {num_ligne} ignorée : format invalide")
                    continue
                mot, cats = ligne.split(":",1)
                mot = mot.strip()
                if not mot :
                    print(f"Ligne {num_ligne} ignorée : mot vide ignoré")
                    continue
                listes_cats = [c.strip() for c in cats.split(",") if c.strip()]
                if not listes_cats : 
                    print(f"Ligne {num_ligne} aucune catégorie pour : {mot}")
                    continue
                lexique[mot] = listes_cats
        print(f"{num_ligne} entrée(s) lexicale(s) chargée(s) depuis '{filename}'.")
        
    except FileNotFoundError :
        print(f"Erreur : le fichier {filename} des phrases est introuvable")
    except OSError as e :
        print(f"Erreur de lecture du ficher {filename}")
   
    return lexique

def clean_categories(s, word=None):
        r"""
        Cette fonction transforme une chaîne de caractères 
        en une structure arborescente d'objets 'Categories'.
                    
        Logique :
        1.  Supprime les parenthèses redondantes si y'en a (ex: '((S\NP))' -> 'S\NP')
        2. Cherche le slash princiapl de droite à gauche.
        3. Construite récursivement les sous-catégories : divise la chaîne en deux et 
            instancie les sous-catégories jusqu'à atteindre les catégories basiques (S, NP). 
            Attention récursivité ici.
                    
        Entrée :
            s (str): la catégorie sous forme de texte (ex: "(S\NP)/NP").
            word (str, optional): le mot associé pour la traçabilité dans l'arbre.
                        
        Sortie :
            Categories : l'objet Catégories correspondant
        """
       
        s = s.strip()
        if not s :
            raise ValueError("Impossible de traiter une catégorie vide.")
            # Etape 1 : suppression des parenthèses externes redondantes - si y'en a -
        while s.startswith("(") and s.endswith(")"):
            depth, split = 0, True
            for char in s[1:-1] :
                if char == "(" : 
                    depth += 1
                elif char == ")" : 
                    depth -= 1
                if depth < 0 : 
                    split = False
                    break
            if split : 
                s = s[1:-1].strip()
            else : 
                break
        # Etape 2 : recherche des catégories simples (NP, S)
        if not any(c in s for c in ["/", "\\"]):
            return Categories(s, word=word)
        
        # Etape 3 : cherche le \ ou / principal pour trouver 1ère catégorie à droite
        depth, split_idx = 0, -1
        for i in range(len(s)-1, -1, -1) :
            if s[i] == ")" : 
                depth += 1
            elif s[i] == "(" : 
                depth -= 1
            elif depth == 0 and s[i] in ["/", "\\"] :
                split_idx = i; 
                break
            
        # Etape 4 : construction récursive de l'objet
        if split_idx != -1:
            return Categories(clean_categories(s[:split_idx]), 
                              s[split_idx], 
                              clean_categories(s[split_idx+1:]),
                              word=word)
        
        return Categories(s, word=word)

# REGLES COMBINATOIRES

def substitut_x(template, concrete):
    """
    Remplace X par la catégorie concrète lors d'une 
    coordination pour la recherche.

    Entrées : 
        template (str) : catégorie contenant éventuellement la variable X
        concrete (str) : catégorie concrète qui remplace X
    Sortie :
        Retourne la catégorie X remplacé par concrete
    """
    if getattr(template, 'is_basic', isinstance(template, str)) :
        t_val = template.left if hasattr(template, 'left') else template
        return concrete if t_val == "X" else Categories(t_val)
    return Categories(substitut_x(template.left, concrete), 
                      template.slash, 
                      substitut_x(template.right, concrete))

def appli_norm(l, r):
    """
    Règle d'application (>) : X / Y  Y -> X
    Si la catégorie gauche cherche un argument Y à droite et que 
    la catégorie droite est compatible avec Y, on retourne X

    Entrées : 
        l (Categories) : catégorie gauche
        r (Categories) : catégorie droite
    Sortie :
        La catégorie résultante ou None si la règle ne s'applique pas
    """
    if not l.is_basic and l.slash == "/" and l.right.matches(r) :
        res = substitut_x(l.left, r) if "X" in str(l) else l.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, ">"))
    return None

def appli_inverse(l, r):
    """
    Règle d'application inverse (<) : Y  X\\Y -> X
    Si la catégorie droite cherche un argument Y à gauche et que 
    la catégorie gauche est compatible avec Y, on retourne X

    Entrées : 
        l (Categories) : catégorie gauche
        r (Categories) : catégorie droite
    Sortie :
        La catégorie résultante ou None si la règle ne s'applique pas
    """
    if not r.is_basic and r.slash == "\\" and r.right.matches(l) :
        res = substitut_x(r.left, l) if "X" in str(r) else r.left
        return Categories(res.left, res.slash, res.right, origin=(l, r, "<"))
    return None

def compo_harmo(l, r):
    r"""
    Règle de composition harmonique (>B) : X/Y  Y\Z -> X\Z

     Entrées : 
        l (Categories) : catégorie gauche
        r (Categories) : catégorie droite
    Sortie :
        La catégorie résultante ou None si la règle ne s'applique pas
    """
    if not l.is_basic and not r.is_basic :
        if l.slash == "/" and r.slash == "/" and l.right.matches(r.left) :
            return Categories(l.left, "/", r.right, origin=(l, r, "> B"))
    return None

def compo_inverse(l, r):
    """
    Règle de composition harmonique (<B) : Y\\Z  X\\Y -> X\\Z

     Entrées : 
        l (Categories) : catégorie gauche
        r (Categories) : catégorie droite
    Sortie :
        La catégorie résultante ou None si la règle ne s'applique pas
    """
    if not l.is_basic and not r.is_basic :
            if r.slash == "\\" and l.slash == "\\" and r.right.matches(l.left) :
                return Categories(r.left, "\\", l.right, origin=(l, r, "< B"))
    return None

def type_raising(c):
    r"""
    Règle de type-raising (>T) : NP -> S/ S \NP

    Transforme tout constituant dont la catégorie est NP
    
    Entrées : 
        c (Categories) : catégorie à élever (doit être un NP)
    Sorties :
        la nouvelle catégorie (S/ S\\NP), ou None si inapplicable
    """
    if str(c) == "NP" : 
        s = Categories("S")
        s_np = Categories(Categories("S"), "\\", Categories("NP"))
        return Categories(s, "/", s_np, origin=(c, None, "> T"))
    return None

# ALGORITHME PRINCIPAL
def prog_cat(sentence, lexicon, use_tr=True):
    r"""
    L'algorithme remplit une table de hachage (chart) 
    en combinant les catégories lexicales selon les règles d'application, 
    de composition et type-raising

    Entrées :
        sentence (str): la phrase à analyser
        lexicon (dict): le dictionnaire contenant les catégories associées aux mots
        use_tr (bool): active ou désactive le Type-Raising (NP -> S/(S\NP)), par défaut : True

    Sortie :
        tuple: (
            valid_sols (list[Categories]) : dérivations complètes aboutissant à S
            nb_comb (int) : nombre total de combinaisons testés
            exec_time (float) : temps d'exécution en millisecondes
            chart (list[list[dict]]) : la table complète
            pic_kb (float) : pic mémoire en kilooctets
            stats_evolution (list[tuple]) : évolution des stats par span 
    """

    if not sentence.strip() :
        raise ValueError("La phrase à analyser est vide")
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
                try :
                    c = clean_categories(cat_str, word=word)
                    chart[i][i+1]["succes"].append(c)
                    # Gestion type-rasing
                    if use_tr :
                        tr = type_raising(c)
                        if tr : 
                            chart[i][i+1]["succes"].append(tr)
                except ValueError as e :
                    print(f"Catégorie invalide {cat_str} pour le mot : {word}, erreur : {e}")
        else:
            # Gestion des mots inconnus
            print(f"Mot inconnu du lexique : '{word}'")
            chart[i][i+1]["succes"].append(Categories("???", word=word))
            
    # DEBUT BOUCLE DE RECHERCHE 
    for span in range(2, n + 1) :        # longueur du segment courant
        for i in range(n - span + 1) :   
            j = i + span
            
            for k in range(i + 1, j) :

               # GESTION DU CAS DE LA COORDINATION
                if j - i >= 3 :
                    for k2 in range(k + 1, j) :
                        for c1 in chart[i][k]["succes"] :
                            for c2 in chart[k][k2]["succes"] :
                                if (c2.word or '').lower() == 'et' :
                                    for c3 in chart[k2][j]["succes"] :
                                        nb_comb += 1
                                        if c1.matches(c3) :
                                            res = Categories(c1.left, c1.slash, c1.right, origin=(c1, c2, c3, "<*>"))
                                            chart[i][j]["succes"].append(res)

                # cAS GENERAL / REGLES BINAIRES 
                for left in chart[i][k]["succes"] :
                    for right in chart[k][j]["succes"] :

                        if (left.word or '').lower() == 'et' :
                            continue 
                        if (right.word or '').lower() == 'et' : 
                            continue

                        nb_comb += 1
                        found_rule = False

                        # Test séquentiel de nos règles combinatoires
                        for res in [appli_norm(left, right), 
                                    appli_inverse(left, right), 
                                    compo_harmo(left, right), 
                                    compo_inverse(left, right)] :
                            
                            if res is not None : 
                                chart[i][j]["succes"].append(res)
                                found_rule = True
                                # Gestion du type-raising sur tout NP
                                if use_tr :
                                    tr = type_raising(res)
                                    if tr :
                                        chart[i][j]["succes"].append(tr)
                                      
                        # Stockage des échecs pour l'affichage et analyse 
                        if not found_rule:
                            chart[i][j]["stop"].append((left, right))
        # Enregistrement des stats à la fin de chaque span
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

    print(f"Analyse de '{sentence}' : {len(valid)} solution(s), {nb_comb} combinaisons, {exec_t:.2f} ms, {pic_kb:.2f} KB")
    
    return valid, nb_comb, exec_t, chart, pic_kb, stats_evolution


# RECUPERATION DES DONNEES PORU CONSTRUIRE LES ARBRES
def recup_frag_abandon(chart, n):
    """ 
    Identifie les fragments maximaux construits en cas d'échec d'analyse

    Entrée : 
        chart (list[list[dict]]) : la table remplie par prog_cat()
        n (int) : nombre de mots dans la phrase
    
    Sortie :
        list[Categories] : les catégories couvrant la phrase avec les segments
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


def recup_strc_arbre(cat, _depth=0) :
    """
    Reconstruit récursivement la structure d'un arbre de dérivation
    Adapté pour un rendu SVG

    Entrées :  
        cat (Categories) : les catégories racine de l'arbre à reconstruire
        _depth (int) : profindeur courante  (usage interne, protection contre les cycles)
    Sorties : 
        dict : représentation arborescente du noeud et de ses descendants
    """
    # Gestion de la récursion
    if _depth > 200 : 
        print(f"Attention proifondeur maximale de récursion atteinte dans recup_strc_arbre")
        return {"word" : "...", "cat" : "?"}
    
    if not cat.origin: 
        return {"word": cat.word, "cat": str(cat)}
    
    if len(cat.origin) == 4:
        c1, c2, c3, rule = cat.origin
        return {"result": str(cat), 
                "rule": rule, 
                "left": recup_strc_arbre(c1,_depth + 1), 
                "mid": recup_strc_arbre(c2, _depth + 1), 
                "right": recup_strc_arbre(c3, _depth + 1),
                }
    
    l, r, rule = cat.origin
    if r is None: 
        return {"result": str(cat), 
                "rule": rule, 
                "left": recup_strc_arbre(l, _depth + 1)
                }

    return {"result": str(cat), 
            "rule": rule, 
            "left": recup_strc_arbre(l, _depth +1), 
            "right": recup_strc_arbre(r, _depth+1),
            }

# GESTION DES ARBRES DE DERIVATION EN HTML
def tree_to_html(tree, title) :
    """ 
    Génère le code html contenant un arbre de dérivation en SVG

    Entrées :
        tree (dict) : structure arborescente produite par recup_strc_arbre()
                      Si None ou vide, retourne une chaine vide
        title (str) : le titre afficher au dessus de l'arbre

    Sorties : 
        str : fragment html à inserer dans le rapport
    """
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
    # Helpers SVG
    def svg_text(x, y, text, size=14, weight="normal", color="#000", anchor="middle") :
        """ Génère une balise <text> SVG"""
        clean_txt = str(text).replace("<", "&lt;").replace(">", "&gt;")
        return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{color}">{clean_txt}</text>'

    def svg_line(x1, y1, x2, y2, color, width=1, dash=None):
        """Génère une balise <line> SVG"""
        style = f'stroke:{color};stroke-width:{width}'
        if dash: style += f';stroke-dasharray:{dash}'
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" style="{style}" />'
    
    def get_leaves(node):
        """
        Retourne la liste des feuilles d'un noeud"
        """
        if "word" in node : 
            return [node]
        leaves = []
        for k in ("left", "mid", "right"):
            if node.get(k) : 
                leaves += get_leaves(node[k])
        return leaves

    leaves = get_leaves(tree)
    n_leaves = len(leaves)
    # Map l'ID de l'objet vers son index de colonne
    leaf_col = {id(lf): i for i, lf in enumerate(leaves)}

    #  CALCUL DU LAYOUT (Récursif)
    cells = []

    def layout(node):
        """
        Calcul la position d'un noeud et de ses enfants

        Retourne un tuple (row, col, span, cx, bottom_y)
            row : niveau vertical
            col : colonne de départ
            span : nombre de colonnes couvertes
            cx : centre horizontal
            bottom_y : coordonnée y du bas du noeud pour relier au parent

        """
        if "word" in node:
            col = leaf_col[id(node)]
            return 0, col, 1, (col + 0.5) * cfg["col_w"], cfg["word_y"] + cfg["lex_h"]  

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
    total_w = n_leaves * cfg["col_w"] + 80
    elements = []
    
    lex_cat_y = cfg["word_y"] + cfg["lex_h"]
    # Rendu des mots et catégories lexicales 
    for i, lf in enumerate(leaves):
        cx = (i + 0.5) * cfg["col_w"]
        cat = lf.get("cat", "???")

        if (lf.get("word") or "").lower() == "et" :
            cat = r"X\X/X"
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
        """Calcul la coordonnée y d'un élément selon son niveau et sa partie"""
        base_y = lex_cat_y + 10 + (row - 1) * cfg["row_h"]
        return base_y + 20 if part == "bar" else base_y + 45

    for c in sorted(cells, key=lambda x: x["row"]):
        r_y_bar = get_y(c["row"], "bar")
        r_y_cat = get_y(c["row"], "cat")
        
        # Pointillés montants des enfants
        for sx, sy in c["stems"]:
            elements.append(svg_line(sx, sy, sx, r_y_bar, cfg["colors"]["stem"], dash=cfg["dash"]))

        x1 = min(s[0] for s in c["stems"])
        x2 = max(s[0] for s in c["stems"])

        # Barre de règle
        if x1 == x2 : 
            x1, x2 = x1 - 30, x2 + 30 # Type-raising
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
    Génère un graphique d'évolution des métrique de performance par span
    Produit trois courbes : Temps d'exécution, Nombre de combinaisons testées cumulées,
                            Pic mémoire

    Entrées :
        stats_evolution (list[tuple]) : la liste retournée par prog_cat()
    Sorties :
        str : balise <img> html ou chaine vide si stats_evolution est vide

    """
    if not stats_evolution : 
        return ""
    
    # Extraction des données
    spans, temps, combs, mems = zip(*stats_evolution)
    
    # Création de la figure 
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4))
    
    # Graph 1 : Temps
    ax1.plot(spans, temps, color='#d63031', marker='o', linewidth=2)
    ax1.set_title("Évolution Temps (ms)")
    ax1.set_xlabel("Longueur du span")
    ax1.grid(True, alpha=0.3)

    # Graph 2 : Combinaisons
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
    
    # Encodage Base64 pour intégration directe dans le HTML 
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return (f'<div style="text-align:center; margin: 20px 0;"><img src="data:image/png;base64,{img_str}" style="width:100%; max-width:1100px; border:1px solid #eee;"></div>')

# MAIN
def main():
    """
    Point d'entrée du script

    Charge le lexique et les phrases, lance l'analyse pour chaque phrase,
    puis génère le rapport HTML
    """

    lexique_test= charger_lexique("data/base_lexicale_simple.txt")
    phrases_test = charger_phrases("data/phrases_simple.txt")

    if not lexique_test : 
        print(f"Le lexique est vide. Arrêt du script")
        return
    if not phrases_test : 
        print(f"Aucune phrase à analyser. Arrêt du script")
        return


# DEFINITION DU CSS DE NOTRE SORTIE HTML
    css = """
    <style>
    body { font-family: sans-serif; background: #ffffff; padding: 40px; color: #2d3436; }
    h1   { border-bottom: 2px solid #2d3436; padding-bottom: 10px; margin-bottom: 30px; }
    .phrase-container { margin-bottom: 30px; border: 1px solid #ccc; border-radius: 4px; }
    summary   { padding: 15px; cursor: pointer; font-weight: bold; background: #f8f9fa;
                border-bottom: 1px solid #ccc; font-size: 1.2em; }
    .content  { padding: 20px; }
    .stats-text { font-weight: normal; color: #636e72; margin-left: 20px; font-size: 0.8em; }
    .cat { font-family: monospace; font-size: 1.1em; padding: 6px 12px 4px; white-space: nowrap; }
    </style>
    """

    # CREATION DU FICHIER HTML DE SORTIE
    rapport = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{css}</head><body>"
    rapport += "<h1>Visualisation des arbres de dérivation en Grammaire Catégorielle - Sortie phrases simples</h1>"

    for p in phrases_test:
        p_clean = p.replace(".", "").strip()
        words = p_clean.split()
        n = len(words)
        
        try : 
            valid_sols, nb, t, chart, pic_kb, evolution = prog_cat(p_clean, lexique_test)
        except ValueError as e :
            print(f"Erreur {e} d'analyse pour {p}")
            continue

        line_graph_html = get_phrase_line_graph(evolution)
        
        rapport += f"""
        <details  class="phrase-container">
            <summary>« {p} »
                <span class="stats-text">{t:.2f} ms | {nb} combinaisons | {pic_kb:.2f} KB</span>
            </summary>
            <div class="content">
                {line_graph_html}  <div class="tech-card"> ... </div>
        """

        # Affichage des arbres de dérivation complet S
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
            rapport += "<p>Aucune structure complète alternative.</p>"

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
    output_file = "sortie_CGC_simple.html"
    try : 
        with open(output_file, "w", encoding="utf-8") as f :
            f.write(rapport)
        print(f"Rapport {output_file} généré avec succès")
    except OSError as e : 
        print(f"Impossible d'écrire le rapport {output_file}, erreur : {e}")

# Lancement 

if __name__ == "__main__":
    main()
