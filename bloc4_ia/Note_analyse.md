# Note d’analyse : les limites des mentions extraites

Objet : qualification d’un tableau de bord expérimental sur les textes TASS. Exécution locale du 4 octobre 2026, modèle `weak-efc7c759e0-s42-e6`, empreinte `f35d2e57acb16d96b802c1b578b3c9e780ea53114dcd28c7cb8d65b54fc5f918`.

Le traitement de 21 676 articles produit 39 511 mentions, réparties en 17 479 WEAPON, 7 098 MIL_UNIT et 14 934 MIL_ORG. Au moins une prédiction apparaît dans 13 099 articles. Ces totaux sont des sorties du modèle à supervision faible, pas une référence sur l’armement ou les organisations réellement présentes.

Une inspection technique ponctuelle constate des erreurs manifestes au regard du schéma d’annotation. Le classement contient 2 959 prédictions « NATO » sous WEAPON, tandis que 1 295 autres portent MIL_ORG. « Pentagon » apparaît aussi sous WEAPON. L’article 2034929 fournit un exemple de NATO entre les positions 662 et 666, accessible par son URL TASS et son empreinte. Cette incohérence contamine le top des armes. Elle suffit à écarter une interprétation automatique de ce classement comme hiérarchie stratégique, sans permettre de calculer une précision globale.

Les variations de casse et les frontières erronées divisent également les comptes : « Black Sea » peut apparaître séparément de « Black Sea Fleet ». Une normalisation ultérieure doit être documentée et comparée aux spans originaux. Elle ne doit pas masquer des erreurs d’extraction.

Les volumes par année décrivent le contenu disponible dans le corpus, avec un pic de 4 639 articles en 2023. Ce nombre ne prouve ni exhaustivité de la collecte TASS ni variation correspondante des opérations militaires. Le volume publié, la couverture du corpus, le vocabulaire de la source et les erreurs du modèle influencent les résultats. TASS est une source unique avec un cadrage éditorial. Une absence de prédiction ne prouve aucune absence sur le terrain.

L’usage défendable est une aide à la navigation : repérer un groupe de passages, ouvrir l’article intégral, vérifier la mention, consulter la source puis recouper avec des sources indépendantes. Une évaluation exploratoire complémentaire utilise 104 mentions proposées par Codex sur 18 articles réservés au test. Elle mesure une précision de 91,18 %, un rappel de 29,81 % et un F1 micro de 44,93 % à correspondance exacte. Ces valeurs décrivent l’accord avec la référence générée par IA ; elles dépendent de ses erreurs possibles et du choix des textes.

La référence a ensuite été élargie à 42 articles, avec 24 textes supplémentaires issus du test figé et répartis en trois classes de longueur. Les 254 mentions proposées par IA donnent une précision de 71,05 %, un rappel de 21,26 % et un F1 de 32,73 %. L’extension seule mesure un F1 de 23,96 %, et sa classe de textes longs 16,16 %. Les propositions nouvelles ont été figées avant l’inférence. Ces résultats renforcent le constat d’omissions ; ils ne montrent ni une dégradation dans le temps ni une amélioration des poids, puisque la référence change et que le modèle reste identique. Voir `docs/Diagnostic_IA_42_articles.md` et `Preuves/Diagnostic_annotations_IA_42_articles.json`.

La prochaine étape consiste à contrôler davantage la référence et comparer les modèles sur ce même jeu figé. Les seuils de promotion sont des choix de fiabilité proposés pour le mémoire, sans constituer des seuils officiels de réussite du jury.

Preuves : `Preuves/corpus_predictions_summary.json`, `Preuves/inference_full.json`, `Preuves/quality_gate.json`, `Preuves/Diagnostic_annotations_IA.json`, captures Kibana et interface. Les contrôles techniques et le diagnostic exploratoire ont des périmètres distincts.
