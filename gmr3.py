import time
import tracemalloc

# ==========================================
# 1. CLASSES ET STRUCTURES DE DONNÉES
# ==========================================

class Categories: 
    """ 
    left = résultat attendu (gauche du slash)
    right = argument attendu (droite du slash)
    is_basic = catégorie basique (S, NP, X)
    """
    def __init__(self, left, slash=None, right=None, word=None, origin=None):
        self.left = left    
        self.slash = slash  
        self.right = right  
        self.word = word    
        self.origin = origin 
        self.is_basic = slash is None

    def __str__(self):
        if self.is_basic: 
            return str(self.left)
        l_str = str(self.left) if isinstance(self.left, str) or getattr(self.left, 'is_basic', False) else f"({self.left})"
        r_str = str(self.right) if getattr(self.right, 'is_basic', False) else f"({self.right})"
        return f"{l_str}{self.slash}{r_str}"
    
    def matches(self, other):
        """ Comparaison structurelle robuste pour éviter les faux positifs textuels """
        # Sécurité anti-crash si on compare accidentellement avec une chaîne
        if isinstance(other, str): 
            return str(self) == other
            
        # 1. Joker X (pour la coordination)
        if (self.is_basic and self.left == "X") or (other.is_basic and other.left == "X"):
            return True
            
        # 2. Rejet immédiat si les types (basique vs complexe) ne correspondent pas
        if self.is_basic != other.is_basic: 
            return False
            
        # 3. Comparaison des catégories de base
        if self.is_basic:
            return self.left == other.left
            
        # 4. Comparaison récursive sécurisée des foncteurs
        left_match = self.left.matches(other.left) if hasattr(self.left, 'matches') else str(self.left) == str(other.left)
        right_match = self.right.matches(other.right) if hasattr(self.right, 'matches') else str(self.right) == str(other.right)
        
        return self.slash == other.slash and left_match and right_match

# ==========================================
# 2. CHARGEMENT ET NETTOYAGE
# ==========================================

def charger_phrases(filename):
    phrases = []
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            for ligne in f:
                l = ligne.strip()
                if l and not l.startswith("#"):
                    phrases.append(l)
    except FileNotFoundError:
        print(f"Erreur : le fichier {filename} est introuvable.")
    return phrases

def charger_lexique(filename):
    lexique = {}
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            for ligne in f:
                l = ligne.strip()
                if l and not l.startswith("#"):
                    if ":" in ligne:
                        mot, cats = ligne.split(":", 1)
                        listes_cats = [c.strip() for c in cats.split(",")]
                        lexique[mot.strip()] = listes_cats
    except Exception as e:
        print(f"Erreur de lecture du lexique : {e}")
    return lexique

def clean_categories(s, word=None):
    s = s.strip()
    # Retrait des parenthèses englobantes inutiles
    while s.startswith("(") and s.endswith(")"):
        depth, split = 0, True
        for char in s[1:-1]:
            if char == "(": depth += 1
            elif char == ")": depth -= 1
            if depth < 0: 
                split = False
                break
        if split: 
            s = s[1:-1].strip()
        else: 
            break
            
    if not any(c in s for c in ["/", "\\"]):
        return Categories(s, word=word)
        
    # Recherche du slash principal de droite à gauche
    depth, split_idx = 0, -1
    for i in range(len(s)-1, -1, -1):
        if s[i] == ")": depth += 1
        elif s[i] == "(": depth -= 1
        elif depth == 0 and s[i] in ["/", "\\"]:
            split_idx = i
            break
            
    if split_idx != -1:
        return Categories(clean_categories(s[:split_idx]), s[split_idx], clean_categories(s[split_idx+1:]), word=word)
    return Categories(s, word=word)

# ==========================================
# 3. MOTEUR DE RÈGLES CCG
# ==========================================

def substitute_x(template, concrete):
    """ Remplace le Joker X par la catégorie concrète lors d'une coordination """
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
    if l.slash == "/" and r.slash == "/":
        if l.right.matches(r.left):
            return Categories(l.left, "/", r.right, origin=(l, r, ">B"))
    return None

def compo_inverse(l, r):
    if r.slash == "\\" and l.slash == "\\":
        if r.right.matches(l.left):
            return Categories(r.left, "\\", l.left, origin=(l, r, "<B"))
    return None

def type_raising(c):
    if c.is_basic and c.left == "NP":
        s = Categories("S")
        s_np = Categories(Categories("S"), "\\", Categories("NP"))
        return Categories(s, "/", s_np, origin=(c, None, "TR"))
    return None

# ==========================================
# 4. ALGORITHME CYK PRINCIPAL
# ==========================================

def prog_cat(sentence, lexicon, use_tr=True):
    start_t = time.perf_counter()
    tracemalloc.start()
    words = sentence.split()
    n = len(words)
    
    chart = [[{"succes": [], "stop": []} for _ in range(n + 1)] for _ in range(n + 1)]
    nb_comb = 0

    # Ligne 0 : Chargement du lexique
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

    # Boucle CYK
    for span in range(2, n + 1):
        for i in range(n - span + 1):
            j = i + span
            for k in range(i + 1, j):
                
                # RÈGLE TERNAIRE : COORDINATION (<*>)
                if j - i >= 3:
                    for k2 in range(k + 1, j):
                        for c1 in chart[i][k]["succes"]:
                            for c2 in chart[k][k2]["succes"]:
                                if (c2.word or '').lower() == 'et':
                                    for c3 in chart[k2][j]["succes"]:
                                        nb_comb += 1
                                        if c1.matches(c3):
                                            # CORRECTION CRITIQUE : Nouvel objet pour éviter RecursionError
                                            res = Categories(c1.left, c1.slash, c1.right, origin=(c1, c2, c3, "<*>"))
                                            chart[i][j]["succes"].append(res)

                # RÈGLES BINAIRES
                for left in chart[i][k]["succes"]:
                    for right in chart[k][j]["succes"]:
                        # On empêche de traiter le "et" en binaire
                        if (left.word or '').lower() == 'et' or (right.word or '').lower() == 'et': 
                            continue

                        nb_comb += 1
                        found_rule = False

                        for res in [appli_norm(left, right), appli_inverse(left, right), 
                                    compo_harmo(left, right), compo_inverse(left, right)]:
                            if res: 
                                chart[i][j]["succes"].append(res)
                                found_rule = True
                        
                        if not found_rule:
                            chart[i][j]["stop"].append((left, right))
                            
    exec_t = (time.perf_counter() - start_t) * 1000
    courant, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    pic_kb = pic / 1024
    valid = [s for s in chart[0][n]["succes"] if str(s) in ["S", "NP"]]
    
    return valid, nb_comb, exec_t, chart, pic_kb

# ==========================================
# 5. GESTION DU HTML ET DES ARBRES
# ==========================================

def recup_frag_abandon(chart, n):
    dp = {0: (0, [])}
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

def arbre_echec(fragments):
    if not fragments: return None
    trees = [recup_strc_arbre(cat) for cat in fragments]
    while len(trees) > 1:
        left = trees.pop(0)
        right = trees.pop(0)
        fake_node = {
            "result": "<span style='color:#d63031; font-weight:bold;'>RUPTURE</span>", 
            "rule": "NOPE", 
            "left": left, 
            "right": right
        }
        trees.insert(0, fake_node)
    return trees[0]

def recup_strc_arbre(cat):
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
                "left": recup_strc_arbre(l)}
        
    return {"result": str(cat), 
            "rule": rule, 
            "left": recup_strc_arbre(l), 
            "right": recup_strc_arbre(r)}

def tree_to_html(tree, title, nb_tests=0):
    if not tree: return ""
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
    
    stats_html = f"<div class='stats'>Combinaisons testées : {nb_tests}</div>" if nb_tests else ""
    html = f"<h3>{title}</h3>{stats_html}<table class='ccg'><tr>"
    
    for w in words_list: 
        html += f'<td class="word">{w["word"]}</td>'
    html += '</tr>'
    
    for r in range(max_row + 1):
        html += '<tr>'
        c = 0
        while c < n:
            if (r, c) in grid:
                cell = grid[(r, c)]
                label = (cell["rule"] or "").replace("<", "&lt;").replace(">", "&gt;")
                html += f'<td colspan="{cell["width"]}">'
                if cell["rule"]: 
                    html += f'<div class="line"><span class="rule">{label}</span></div>'
                html += f'<div class="cat">{cell["cat"]}</div></td>'
                c += cell["width"]
            else: 
                html += '<td></td>'
                c += 1
        html += '</tr>'
    return html + '</table><hr>'


# ==========================================
# 6. EXÉCUTION DU TEST
# ==========================================

# ==========================================
# 6. EXÉCUTION DU TEST ET GÉNÉRATION HTML
# ==========================================

if __name__ == "__main__":
    lexique_test = charger_lexique("base_lexicale.txt")
    phrases_test = charger_phrases("phrases.txt")

    global_style = """
    <style>
        body { font-family: sans-serif; background: #f4f7f6; padding: 40px; color:#2d3436; }
        h1 { border-bottom: 3px solid #d63031; padding-bottom: 10px; }
        .stats { color: black; font-weight: bold; margin-bottom: 10px; font-size: 0.9em; }
        .ccg { border-collapse: collapse; margin: 30px 0; background: white; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px;}
        .ccg td { text-align: center; vertical-align: bottom; padding: 8px 12px; min-width: 100px; }
        .word { font-weight: bold; font-size: 1.2em; padding-bottom: 15px !important; color: #2d3436; }
        .cat { font-family: 'Consolas', monospace; font-size: 0.95em; color: #636e72; padding: 4px 0; }
        .line { border-top: 2px solid #2d3436; position: relative; margin-top: 6px; height: 15px; }
        .rule { position: absolute; right: 0; top: -14px; background: white; padding: 0 4px; font-size: 0.75em; font-weight: bold; color: #d63031; }
    </style>
    """

    rapport = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{global_style}</head><body>"
    rapport += "<h1>SORTIE TEST</h1>"

    for p in phrases_test:
        p_clean = p.replace(".", "").strip()
        words = p_clean.split()
        n = len(words)
        
        valid_sols, nb, t, chart, pic_kb = prog_cat(p_clean, lexique_test)
        
        rapport += f"<h2 style='margin-bottom: 5px;'>Phrase : « {p} »</h2>"
        rapport += f"<p style='margin-top: 0; color: #636e72; font-size: 0.9em;'>Temps d'exécution : {t:.2f} ms | Combinaisons testées : {nb} | Impact mémoire : {pic_kb:.2f} KB</p>"
        
        # 1. SUCCÈS (Le chemin parfait jusqu'à S ou NP)
        if valid_sols:
            rapport += "<h3 style='color:#00b894;'>SUCCES /clap clap</h3>"
            for i, sol in enumerate(valid_sols):
                rapport += tree_to_html(recup_strc_arbre(sol), f"Succès {i+1}/{len(valid_sols)}")
        else:
            # Gestion visuelle de la rupture finale si aucun S n'est trouvé
            rapport += "<h3 style='color:#d63031;'>RIP (Échec complet)</h3>"
            frags = recup_frag_abandon(chart, n)
            if frags:
                rapport += tree_to_html(arbre_echec(frags), "Arbre de rupture")

        # 2. ÉCHECS FINAUX (Arrive au bout [0][n] mais n'est ni S ni NP)
        echecs = [c for c in chart[0][n]["succes"] if str(c) not in ["S", "NP"]]
        if echecs:
            rapport += "<h3 style='color:#e17055;'>Échec Syntaxique</h3>"
            rapport += "<p style='font-size:0.9em; color:#555;'>Ça arrive au bout mais pas un S (ou NP).</p>"
            for i, sol in enumerate(echecs):
                rapport += tree_to_html(recup_strc_arbre(sol), f"Échec : structure finale {i+1}")

        # 3. ABANDONS (Constructions intermédiaires qui ne vont pas au bout)
        abandon = []
        for span in range(n - 1, 1, -1):
            for i_idx in range(n - span + 1):
                j_idx = i_idx + span
                for cat in chart[i_idx][j_idx]["succes"]:
                    abandon.append((i_idx, j_idx, cat))

        if abandon:
            rapport += f"""
            <details style='margin-top:20px; background:#fff; padding:15px; border:1px solid #dfe6e9; border-radius:5px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);'>
                <summary style='cursor:pointer; font-weight:bold; color:#0984e3; font-size:1.1em;'>
                    Arbres abandonnés ({len(abandon)} abandons)
                </summary>
                <div style='margin-top:20px; border-top: 1px dashed #ccc; padding-top:15px;'>
                    <p style='font-size:0.85em; color:#636e72;'>
                    Construction réussie mais abandonnée par la suite.
                    </p>
            """
            for idx, (i_idx, j_idx, cat) in enumerate(abandon):
                mots_concernes = " ".join(words[i_idx:j_idx])
                titre = f"Abandon n°{idx+1} : « {mots_concernes} »"
                rapport += tree_to_html(recup_strc_arbre(cat), titre)
            rapport += "</details>"

        # 4. CLASHS (Règles qui échouent directement entre deux blocs)
        rapport += "<h3>Abandon en cours de route (Clashs)</h3>"
        for span in range(1, n + 1):
            for i_idx in range(n - span + 1):
                j_idx = i_idx + span
                
                if chart[i_idx][j_idx]["stop"]:
                    mots_segment = " ".join(words[i_idx:j_idx])
                    rapport += f"""
                    <details style='margin-bottom:5px; margin-left: 10px;'>
                        <summary style='color:#636e72; font-size:0.85em; cursor:pointer;'>
                            Segment « {mots_segment} » : {len(chart[i_idx][j_idx]['stop'])} clashs
                        </summary>
                        <ul style='font-size:0.8em; color:#d63031; list-style-type: "ABANDON ";'>
                    """
                    for left, right in chart[i_idx][j_idx]["stop"]:
                        rapport += f"<li>Incompatibilité : <b>{left}</b> et <b>{right}</b></li>"
                    rapport += "</ul></details>"
                    
        rapport += "<hr style='margin-top:40px; border-top: 2px solid #2d3436;'>"

    rapport += "</body></html>"

    with open("test_phrase_a_la_con2.html", "w", encoding="utf-8") as f:
        f.write(rapport)

    print("CLAP CLAP")