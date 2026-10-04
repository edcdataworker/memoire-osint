# Annotation et protocole d’évaluation

## Travail historique préservé

Le rapport collectif de juillet 2026 crédite Jean-Christophe Dorn, Noah Segonds et Edouard Cappaert, avec Matthieu Larboullet comme enseignant. Il indique Claude Haiku et 40 exemples / 81 entités. Le notebook archivé indique dans la cellule N06 `mistral-small-latest`, un endpoint Mistral et 1 889 articles annotés après sélection de 2 000 articles. La cellule N05 déclare explicitement une vérification manuelle d’un échantillon représentatif. Cette déclaration est conservée. Aucun journal, identité du relecteur, date, liste d’articles corrigés ou fichier d’annotations correspondant n’a été retrouvé lors de la nouvelle inspection locale. L’absence de ces pièces ne prouve pas que la revue n’a pas eu lieu.

N10 conserve 803 exemples positifs, répartis en 642 train et 161 dev, avec 46 et 8 spans ignorés. N08 contient des commandes de téléchargement et leurs widgets, sans export des spans récupérable dans les sorties archivées. Les trois F1 historiques, 34 dans le rapport, 49,82 dans le texte du notebook et 56,55 dans une sortie de validation, restent distincts. Aucun de ces scores n’est attribué à la nouvelle baseline.

## Nouvelle expérience de démonstration

Le corpus nettoyé contient 21 676 articles, empreinte dans `.state/data/manifest.json`. Aucun renettoyage n’est effectué. Les indices sont des caractères Unicode, début inclus et fin exclue. Une empreinte du texte relie source, annotation, prédiction et index. La tokenisation de ponctuation a été adaptée pour `ATACMS),The`, tout en préservant intégralement les caractères du texte.

La baseline utilise `spacy.blank('en')`, un NER à poids initiaux aléatoires et trois labels. Elle n’utilise pas les poids de `en_core_web_sm`. Le choix limite dépendances et coût local, mais ne reproduit pas le transfert pédagogique proposé. Une future comparaison avec transfert devra réutiliser la même référence humaine indépendante.

Les expressions régulières de `data.py` constituent une préannotation limitée aux noms connus. Le train contient 240 articles dont 60 sans détection et le dev 60 articles dont 15 sans détection. « Sans détection » ne signifie pas absence réelle d’entités. Les faux négatifs de l’annotateur risquent d’apprendre au modèle des absences incorrectes. Les dev labels ne servent ni à choisir le meilleur modèle ni à calculer une performance qualité, car ils proviennent des mêmes règles.

## Séparation et limites

Les groupes réunissent identifiants, URL, texte canonique et titres identiques. Un hachage avec graine de projet 42 affecte chaque groupe à train, dev ou test. La sélection équilibrée par catégories favorise des textes courts, donc elle ne représente pas uniformément le corpus. Le manifeste est figé par version. Ajouter des doublons peut modifier les groupes, ce qui exige une nouvelle version et une nouvelle vérification des chevauchements.

Un audit exhaustif de 19 800 paires entre les trois sélections teste les doublons et la similarité Jaccard des triplets de mots. Aucune paire ne dépasse 0,8, le maximum observé vaut environ 0,374. Cette barrière de projet ne garantit pas l’indépendance sémantique de récits d’un même événement. Une analyse temporelle et une revue des dépêches proches restent utiles.

## Revue humaine préparée

`Revue_annotations_locale.html` propose 18 articles complets réservés au test, dont quatre sans préannotation. Le relecteur doit vérifier toutes les mentions, y compris les omissions, corriger les frontières et labels, renseigner son nom, attester chaque article puis exporter `human-reviewed.jsonl`. Le navigateur stocke la progression localement. L’outil ne peut pas authentifier la réalité de la lecture. Aucune attestation n’a été produite par l’assistant.

WEAPON : système ou matériel militaire nommé, par exemple S-400. MIL_UNIT : unité combattante nommée ou numérotée, flottes incluses. MIL_ORG : organisation de haut niveau, ministère, état-major ou forces armées. Les mentions génériques seules sont exclues. Annoter chaque occurrence, avec le nom complet sans déterminant ni ponctuation finale. Les noms de personnes et lieux sont hors schéma, mais peuvent subsister dans le texte source.

## Exigence pédagogique et choix de projet

La relecture humaine d’un échantillon est une exigence du cours AI Deployment p.24. Le jeu de test indépendant revu humainement et les seuils de promotion ci-dessous sont des choix méthodologiques proposés pour le projet, pas des seuils de certification. Garder les nouvelles métriques à null en l’absence de référence indépendante relève de cette prudence méthodologique. La déclaration historique de relecture N05 demeure conservée.

## Métriques et promotion

Le scorer calcule précision, rappel et F1 à correspondance exacte du label et des deux bornes, global micro et par label. Les dénominateurs nuls donnent `null`. Une mauvaise frontière compte comme faux positif et faux négatif. Les erreurs sont exportées pour retour au contexte.

`evaluate` refuse une référence sans provenance de revue, hors manifeste test ou recouvrant les groupes train/dev du modèle. Un échantillon de 18 articles relus donnerait seulement une première mesure sur un échantillon assisté, avec biais de sélection et d’ancrage. Il ne suffirait pas à démontrer une qualité de production.

En l’absence de fichier revu humainement, toutes les métriques qualité restent nulles. Les scores calculés dans les tests unitaires concernent exclusivement des fixtures synthétiques destinées à vérifier les formules. Ils ne mesurent pas la NER TASS.

La promotion de production requiert labels d’entraînement revus, empreinte modèle concordante, au moins 100 articles de test, support d’au moins 20 entités par label, F1 global de 0,70 et rappel par label de 0,50. Ces seuils sont des garde-fous exploratoires du projet, à calibrer selon l’usage et les erreurs. Ils ne proviennent ni de l’école ni d’une validation métier. La baseline ne remplit pas ces conditions et reste dans l’environnement de démonstration.
