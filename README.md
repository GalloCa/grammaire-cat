# Moteur d’inférence pour Grammaire Catégorielle Combinatoire (CCG)

Ce projet propose une implémentation exploratoire en Python d'un moteur d'inférence syntaxique fondé sur le formalisme des **Grammaires Catégorielles Combinatoires (CCG)** (Steedman, Baldridge).

Conçu selon les principes des systèmes à base de connaissances (*Knowledge-Based Systems*), il modélise la syntaxe comme un calcul logique de types déclaratif. L'objectif est d'étudier le comportement d'un parseur symbolique ascendant (*chart parsing*), d'observer la traçabilité des preuves formelles et d'analyser les limites combinatoires du formalisme face au français (corpus contrôlé vs données réelles).

**Rapport d'analyse complet** : [Consulter le rapport (PDF)](rapport_grammaire_categorielle.pdf)

---

## Cadre formel & Architecture

Le système repose sur une stricte séparation entre connaissances et moteur de déduction :
* **Connaissances Factuelles (KF)** : le lexique catégoriel associant à chaque unité ses types atomiques (`S`, `NP`) ou ses catégories fonctionnelles directionnelles (`X/Y`, `X\Y`).
* **Connaissances Procédurales (KP)** : les règles combinatoires universelles régissant les réductions.
* **Moteur d'inférence** : un algorithme de *chart parsing* ascendant qui explore exhaustivement l'espace des réductions possibles pour prouver l'axiome cible **`S`**.

### Règles combinatoires implémentées

| Règle | Notation | Schéma formel | Description |
| :--- | :---: | :--- | :--- |
| **Application avant** | `>` | `X/Y  Y → X` | Consommation d'un argument à droite |
| **Application arrière** | `<` | `Y  X\Y → X` | Consommation d'un argument à gauche |
| **Composition harmonique avant** | `>B` | `X/Y  Y/Z → X/Z` | Fusion fonctionnelle projective |
| **Composition harmonique arrière** | `<B` | `Y\Z  X\Y → X\Z` | Fusion fonctionnelle rétrograde |
| **Type-Raising** | `>T` | `NP → S/(S\NP)` | Élévation catégorielle de NP |
| **Coordination** | `<*>` | `X  (X\X)/X  X → X` | Schéma polymorphe pour les conjonctions |

---

## Organisation des données
Les fichiers d'entrée doivent être placés dans le répertoire data/ :
```
.
├── data/
│   ├── lexique_gorafi.txt   # Lexique syntaxique
│   └── phrases_gorafi.txt   # Énoncés à analyser (un par ligne)
├── main.py
└── README.md
```

**Format du lexique** :
Chaque ligne associe un mot à une ou plusieurs catégories séparées par des virgules (mot : cat1, cat2) :
```
Garfield : NP
mange : S\NP, S\NP/NP
et : X\X/X
de : NP\NP/NP
```
**Format des phrases** : 
Les énoncés sont indiqués bruts, ligne par ligne :
```
Garfield mange Mickey
Nicolas Sarkozy reçoit le prix de la littérature de la FIFA
```

---

## Expérimentations & Réflexions

Le moteur a été confronté à deux types d'énoncés pour comparer son comportement théorique et pratique :

### 1. Corpus contrôlé (11 phrases de test)
* **Structures validées** : transitivité (SVO), auxiliaires modaux (`(S\NP)/(S\NP)`), adverbes finaux et coordinations propositionnelles.
* **Extraction & relatives** : validation de l'interaction clé entre *Type-Raising* (`>T`) et composition (`>B`) pour résoudre les relatives objets sans mouvement transformationnel (*« Mickey et Jerry que Garfield dévore mangent voracement »*).
* **Binarité & axiome S** : mise en évidence de la stricte binarité symbolique. Une relative isolée (*« Mickey que Garfield dévore »*) dérive correctement en `NP`, mais est formellement rejetée par le moteur car l'axiome cible attendu est exclusivement `S`.

### 2. Épreuve sur langue réelle (Corpus *Le Gorafi*)
* **Densité catégorielle** : l'introduction de prépositions fonctionnelles (`NP\NP/NP`) et d'adjectifs multiplie les possibilités d'attachement.
* **Explosion combinatoire** : sur la phrase *« Nicolas Sarkozy reçoit le prix de la littérature de la FIFA »*, le moteur explore **518 combinaisons** et génère **106 dérivations valides** pour `S` (phénomène de *spurious ambiguity*).
* **Limites matérielles** : sur des structures à fort enchâssement prépositionnel (ex. phrase P3b à plus de 100 000 combinaisons), le stockage exhaustif des traces en mémoire illustre concrètement le coût du raisonnement symbolique non guidé face à la combinatoire de la langue naturelle.

---

## Visualisation & Monitoring

Pour chaque phrase soumise, le script compile un rapport HTML autonome (`sortie_gorafi.html`) comprenant :
* **Arbres de dérivation complets en SVG** : tracé vectoriel des barres de règles, étiquettes combinatoires et catégories intermédiaires.
* **Courbes de performance** : graphiques `matplotlib` (intégrés en base64) mesurant par longueur de *span* le temps de calcul (ms), le nombre cumulé d'unifications et le pic de mémoire vive (`tracemalloc`).
* **Analyse d'erreur** : isolation des constituants maximaux et identification des points de blocage en cas d'échec de réduction.

Le rapport interactif est généré dans sortie_gorafi.html. Il s'ouvre directement dans n'importe quel navigateur web.

---

## Exécution
Lancez le script principal depuis la racine du projet :
```
python main.py
```

---

## Références 

* **Miller, P. & Torris, T. (1990)**. *Formalismes syntaxiques pour le traitement automatique du langage naturel*. Hermès.
* **Steedman, M. & Baldridge, J. (2011)**. *Combinatory Categorial Grammar. In Non-Transformational Syntax*, Wiley-Blackwell.
