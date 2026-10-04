# Diagnostic exploratoire sur 42 articles

Le 4 octobre 2026, la référence IA a été élargie de 18 à 42 articles, avec le même modèle `weak-efc7c759e0-s42-e6`. La preuve publique expurgée [Diagnostic_annotations_IA_42_articles.json](Diagnostic_annotations_IA_42_articles.json) identifie la référence, la sélection, les erreurs et le modèle. Les propositions sont produites par Codex ; cette attribution ne concerne pas Haiku.

## Sélection et conventions

La référence initiale de 18 articles est conservée sans modification. L’extension comporte 24 autres articles du jeu de test figé, soit huit dans chacune des classes de longueur 1 à 1 199, 1 200 à 2 499 et 2 500 à 4 500 points de code Unicode. Les articles sont classés par SHA-256 de leur identifiant et d’une graine fixe. La sélection n’utilise ni les préannotations lexicales ni les prédictions. Les groupes du train/dev, les 18 articles initiaux et les identifiants exclus sont écartés. Les 42 identifiants, empreintes et groupes correspondent au manifeste test.

Codex a lu les 24 textes complets avant le calcul des nouvelles prédictions. Les propositions sont figées et identifiées par empreinte avant le chargement du modèle. Les conventions de l’extension incluent les noms de matériels et de navires militaires dans WEAPON, les unités, flottes, districts et bases nommées dans MIL_UNIT, les ministères militaires, états-majors, branches et alliances nommées dans MIL_ORG. Les institutions civiles, industriels et équipements sans nom sont exclus. Une désignation coordonnée contiguë est conservée comme un seul span. Les occurrences d’une même surface sont développées puis les chevauchements résolus au profit du span le plus long. Ce sont des choix de diagnostic, dont l’ambiguïté résiduelle limite les scores.

## Résultats à correspondance exacte

| Référence | Articles | Mentions | TP | FP | FN | Précision | Rappel | F1 micro |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Initiale, conservée | 18 | 104 | 31 | 3 | 73 | 91,18 % | 29,81 % | 44,93 % |
| Extension seule | 24 | 150 | 23 | 19 | 127 | 54,76 % | 15,33 % | 23,96 % |
| Ensemble élargi | 42 | 254 | 54 | 22 | 200 | 71,05 % | 21,26 % | 32,73 % |

Sept articles de l’ensemble n’ont aucune mention proposée ; ils restent dans l’évaluation. Le score exige le même label et les deux frontières exactes. Une frontière ou un label différent peut compter à la fois comme faux positif et faux négatif.

| Label sur les 42 articles | Mentions | TP | FP | FN | Précision | Rappel | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| WEAPON | 139 | 26 | 18 | 113 | 59,09 % | 18,71 % | 28,42 % |
| MIL_UNIT | 33 | 11 | 1 | 22 | 91,67 % | 33,33 % | 48,89 % |
| MIL_ORG | 82 | 17 | 3 | 65 | 85,00 % | 20,73 % | 33,33 % |

Le contrôle complémentaire de 27 000 paires entre train, dev et test élargi ne détecte aucun groupe commun, empreinte identique ou Jaccard de triplets de mots supérieur ou égal à 0,8. Le maximum vaut 0,374. Voir `Preuves/split_audit_42_articles.json`. Cela ne garantit pas l’indépendance sémantique des récits.

| Extension par longueur | Articles | Mentions | Précision | Rappel | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Courts | 8 | 18 | 80,00 % | 22,22 % | 34,78 % |
| Moyens | 8 | 54 | 68,75 % | 20,37 % | 31,43 % |
| Longs | 8 | 78 | 38,10 % | 10,26 % | 16,16 % |

Le diagnostic confirme une faible couverture des mentions proposées, particulièrement dans les textes longs de cet échantillon. Il apporte une preuve plus large et mieux décrite ; il ne démontre pas une amélioration du modèle. Les poids sont identiques, empreinte `f35d2e57acb16d96b802c1b578b3c9e780ea53114dcd28c7cb8d65b54fc5f918`.

## Reproduction et limites

Les textes, références et prédictions restent dans `/Volumes/MemoireOSINT/B4/Evaluation_42_articles`, sur le volume chiffré. La preuve identifie la sélection, les fichiers et le script.

L’archive locale `Artefacts_locaux/Diagnostic_IA_42_articles.zip` contient cette sélection, les références et les prédictions figées. Ses empreintes figurent dans `Manifest_artefacts.json`. Pour une reproduction ailleurs, extraire l’archive dans un espace privé chiffré et adapter `--directory`, puis installer le modèle et les jeux fournis séparément. Ces textes ne font pas partie du zip public du code.

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python scripts/diagnostic_ia_elargi.py \
  --directory /Volumes/MemoireOSINT/B4/Evaluation_42_articles \
  --run .state/runs/baseline \
  --initial-reference Artefacts_locaux/Propositions_annotations_IA.jsonl \
  --split-manifest .state/data/split_manifest.jsonl \
  --output Preuves/Diagnostic_annotations_IA_42_articles_nouveau_passage.json
.venv/bin/python scripts/audit_splits.py \
  --reference /Volumes/MemoireOSINT/B4/Evaluation_42_articles/reference_42.jsonl \
  --output Preuves/split_audit_42_articles_nouveau_passage.json
```

Cette référence IA peut omettre ou mal classer des mentions. Les 18 premiers textes gardent leur biais de sélection ; l’extension est stratifiée par longueur, non pondérée et limitée à 4 500 caractères. Les paraphrases entre groupes ne sont pas détectées exhaustivement. Aucun score global de production n’est déduit, aucune promotion n’est débloquée et aucun réentraînement n’a eu lieu. Un contrôle sur la même référence figée permettrait de comparer un futur candidat au modèle actuel.

La preuve JSON publiée remplace les surfaces textuelles des erreurs par leur empreinte SHA-256 et leur longueur. Les textes et la preuve intégrale restent dans le périmètre local protégé.
