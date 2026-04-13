**(WIP) -- CCG-Parser : Analyseur de Grammaires Catégorielles**

Ce projet implémente un analyseur syntaxique basé sur les Grammaires Catégorielles Combinatoires (CCG). Il permet de transformer des énoncés en langage naturel en structures formelles de dérivation en utilisant un algorithme de type Chart Parsing.

**Objectifs du projet**

L'enjeu est de modéliser la langue non pas comme une simple suite de mots, mais comme un système de calcul de types. Chaque entrée lexicale est vue comme une fonction ou un argument, permettant de vérifier la grammaticalité d'une phrase par réduction logique.

Ce parseur a été développé dans le cadre de mon Master 1 Industries de la Langue (UGA) afin d'explorer l'interface entre sémantique formelle et développement Python.

**Fonctionnalités techniques**
1. Raisonnement formel sur structures typées

L'analyseur repose sur une classe Categories capable de manipuler récursivement des catégories atomiques (S, NP, N) et complexes (fonctions de type A/B ou A\B).

    Parsing de catégories : Transformation de chaînes complexes (ex: (S\NP)/NP) en arbres d'objets.

    Gestion de la coordination : Implémentation d'un mécanisme de substitution via une 
                                 catégorie schématique X pour gérer les conjonctions (type X\X/X).

2. Règles Combinatoires implémentées

Le système supporte les règles fondamentales du calcul de Steedman :

    Applications : Fonctionnelle directe (>) et inverse (<).

    Compositions : Harmonique (>B) et inverse (<B).

    Type-Raising : Montée de type (>T) pour les groupes nominaux (NP→S/(S\NP)).

3. Monitoring et Performance

Pour répondre aux exigences d'optimisation, le parseur intègre :

    Un suivi du temps d'exécution (via time.perf_counter).

    Un monitoring de la consommation mémoire (via tracemalloc) pour identifier les pics lors du 
    remplissage de la table de hachage.

4. Visualisation HTML

Le script génère un rapport dynamique au format HTML (dérivation_gram_cat3.html) affichant :

    Les arbres de dérivation complets avec stylisation CSS.

    Les segments intermédiaires et les échecs de dérivation (pour le débogage linguistique).

**État du projet (Work In Progress)**

Ce projet est actuellement en cours de développement.

    Réalisé : Cœur de l'algorithme, gestion des types récursifs, règles de base et export HTML.

    En cours : Amélioration du rendu visuel des pointillés de dérivation dans le rapport HTML et extension du lexique de test.

    Perspectives : Intégration de l'unification pour la gestion des traits de genre et de nombre.

**Utilisation**

    Assurez-vous d'avoir deux fichiers sources à la racine :

        base_lexicale.txt : Lexique au format mot : catégorie1, catégorie2

        phrases.txt : Liste des phrases à tester.

    Lancez le script :
  
    Bash
    
    python main.py
    
    Ouvrez le fichier dérivation_gram_cat.html généré pour visualiser les résultats.
