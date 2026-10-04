# Annotation et protocole de la solution livrée

## Préannotation et contrôle par IA

Le projet utilise trois labels : `WEAPON`, `MIL_UNIT` et `MIL_ORG`. La baseline `weak-efc7c759e0-s42-e6` apprend sur des préannotations produites localement par les règles lexicales de `data.py`. Un contrôle complémentaire par Codex propose initialement 104 mentions sur 18 articles réservés au test. L’extension documentée dans `Diagnostic_IA_42_articles.md` conserve ces textes et en ajoute 24 : 254 mentions sur 42 articles, sans modifier les jeux d’apprentissage ni les poids.

Le modèle utilise `spacy.blank('en')`, un NER à poids initiaux aléatoires, la graine 42 et six époques CPU. Il ne réutilise pas les poids de `en_core_web_sm`. Le train contient 240 articles, dont 60 sans préannotation, et le dev 60 articles, dont 15 sans préannotation. Une absence de proposition ne prouve pas l’absence d’entité. Les labels dev provenant des mêmes règles ne servent pas à annoncer une qualité indépendante.

## Schéma d’annotation

`WEAPON` couvre les systèmes ou matériels militaires nommés. `MIL_UNIT` couvre les unités nommées ou numérotées, flottes incluses. `MIL_ORG` couvre les organisations de haut niveau, ministères, états-majors et forces armées. Les mentions génériques seules sont exclues. Chaque occurrence conserve son nom complet, sans déterminant ni ponctuation finale, avec début inclus et fin exclue en points de code Unicode. Les personnes et lieux restent hors schéma, mais peuvent subsister dans le texte source.

Les propositions IA signalent huit décisions de périmètre à trancher, notamment navires, bases, districts et services de renseignement. Les contrôles d’offsets, de label, de chevauchement et d’empreinte sont déterministes ; la pertinence sémantique des propositions dépend de l’annotateur.

## Séparation et limites

Les groupes réunissent identifiants, URL, texte canonique et titres identiques. Un hachage avec graine 42 affecte chaque groupe à train, dev ou test. Le manifeste est figé par version. Ajouter des doublons peut modifier les groupes et impose une nouvelle vérification des chevauchements.

L’audit de 19 800 paires entre sélections ne détecte aucune similarité Jaccard des triplets de mots supérieure à 0,8 ; le maximum observé est environ 0,374. Cette barrière ne garantit pas l’indépendance sémantique de récits d’un même événement. Les 18 textes de test sont courts et sélectionnés avec aide des règles initiales ; ils ne représentent pas uniformément le corpus.

## Évaluation exploratoire

Le scorer compare le label et les deux frontières exactes. Une frontière incorrecte compte comme faux positif et faux négatif. Il calcule précision, rappel et F1 micro et par label ; un dénominateur nul donne `null`.

La comparaison de la baseline aux propositions IA donne 31 vrais positifs, 3 faux positifs et 73 faux négatifs : précision 91,18 %, rappel 29,81 % et F1 micro 44,93 %. Les erreurs, le modèle, la référence et leurs empreintes sont consignés dans `Preuves/Diagnostic_annotations_IA.json`. Ce diagnostic mesure l’accord avec cette référence générée par IA. Les erreurs de référence, les décisions non tranchées et la sélection des textes limitent son interprétation et toute extrapolation au corpus complet.

## Outils de revue et contrôle de promotion

`Revue_annotations_locale.html` et `Revue_annotations_assistee_IA.html` affichent les textes complets et permettent de corriger les frontières, labels et omissions. Le navigateur conserve la progression localement. L’export de revue comporte la provenance du relecteur ; une attestation doit correspondre à une lecture effectivement réalisée.

La commande `evaluate` exige une provenance de revue humaine, une appartenance au manifeste test et l’absence de chevauchement avec train/dev. Elle est distincte du diagnostic IA existant. Le cours AI Deployment p. 24 demande une relecture humaine d’un échantillon : le contrôle par IA est une méthode complémentaire et ne permet pas de déclarer cette étape réalisée.

La promotion de production exige les labels d’entraînement revus, une empreinte modèle concordante, au moins 100 articles de test, au moins 20 entités par label, un F1 global de 0,70 et un rappel par label de 0,50. Ces seuils sont des garde-fous exploratoires de projet, à calibrer selon l’usage, sans provenance scolaire ni validation métier. La baseline reste dans l’environnement de démonstration ; le diagnostic IA ne débloque pas cette promotion.

## Revue humaine des 42 articles

Le [parcours de revue](Revue_humaine_42_articles.md) permet de corriger les propositions, enregistrer les décisions sur le volume chiffré, puis calculer la qualité sur le test figé. Les prédictions sont masquées pendant la lecture. Aucun article réel n’est attesté par les tests automatiques ; la revue personnelle reste à effectuer. Démarrer le lanceur Lancer_revue_humaine.command depuis le dossier B4.
