# Raccordement manuel de cinq nouveaux articles

Contrôle local exécuté le 4 octobre 2026. Les cinq articles de la collecte TASS du 3 octobre ont été analysés avec le modèle livré, puis leurs mentions ont été ajoutées à Elasticsearch et relues avec le compte lecteur. Ce contrôle complète la preuve de compatibilité avec l’infrastructure existante, critère B4-2.1, cellule `Bloc 4!A11`.

## Entrées et résultats

Le job B3 `26f06c0e-7fac-4dbe-a391-ef5c7675d8dd` fournit les identifiants `2197107`, `2197157`, `2197167`, `2197169` et `2197173`. La sélection utilise leurs versions courantes dans SQLite et applique les règles de visibilité B3. Les identifiants ont ensuite été confrontés au registre B2 d’exclusion avant l’inférence et l’indexation.

Le modèle est `weak-efc7c759e0-s42-e6`, empreinte SHA-256 `f35d2e57acb16d96b802c1b578b3c9e780ea53114dcd28c7cb8d65b54fc5f918`. Les commandes existantes `infer` et `export-es` ont été utilisées, sans réentraînement.

| Contrôle | Résultat observé |
| --- | --- |
| Inférence CPU, chargement du modèle compris | 5 textes en 1,476 seconde |
| Mentions produites | 9, réparties sur les 5 articles |
| Identité B3, SQL, MongoDB et index des articles | Identifiants, dates, textes, empreintes et provenance concordants selon le contrat de chaque stockage |
| Positions des mentions | Sous-chaînes exactes et offsets en points de code Unicode vérifiés |
| Lecture Elasticsearch | Les 9 documents relus avec `osint_reader` correspondent exactement à l’export B4 |
| Index de mentions | 39 511 avant, 39 520 après ; les 39 511 mentions hors sélection restent présentes |
| Schémas Elasticsearch | Mappings des articles et des mentions inchangés |
| Rejeu du même export | 39 520 mentions avant et après, aucune duplication |

Le contrôle des stockages et l’indexation ont pris 0,472 seconde dans le conteneur `ops`, hors démarrage de celui-ci. Ces durées portent sur ce seul essai local et ne sont pas un engagement de temps de réponse.

La preuve synthétique est [Raccordement_manuel_5_articles.json](../Preuves/Raccordement_manuel_5_articles.json). Les rapports détaillés de précontrôle, d’indexation et de rejeu sont conservés dans `00_Pilotage/Integration_transversale/Preuves/`. Ils contiennent des identifiants, comptages et empreintes, sans texte d’article ni secret.

## Reproduction opérateur

Les entrées et sorties textuelles de cet essai sont dans `/Volumes/MemoireOSINT/B4/verification_manuelle_20261004`, sur le volume chiffré déjà activé. Cette protection concerne ces fichiers ; elle ne prouve pas une migration de toutes les copies B4. Les fichiers `articles.json` et `articles.jsonl` représentent la même sélection figée. Avant un nouveau passage, vérifier les versions courantes et renouveler `exclusions.json` depuis le registre B2.

Depuis `04_Bloc_4_IA`, avec le modèle installé :

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
sample=/Volumes/MemoireOSINT/B4/verification_manuelle_20261004
.venv/bin/python -m osint_ner.cli infer --run .state/runs/baseline --input "$sample/articles.jsonl" --output "$sample/predictions.jsonl" --exclusions "$sample/exclusions.json"
.venv/bin/python -m osint_ner.cli export-es --input "$sample/predictions.jsonl" --output "$sample/mentions.ndjson" --exclusions "$sample/exclusions.json"
```

Depuis `02_Bloc_2_Architecture`, avec les services B2 disponibles, exécuter le contrôle. Sans `--index`, il effectue uniquement le précontrôle ; l’option ajoute les mentions vérifiées et contrôle leur lecture. Utiliser un nouveau nom de rapport pour conserver les preuves précédentes.

```sh
docker compose run --rm --no-deps -e PYTHONPATH=/app \
  -v /Volumes/MemoireOSINT/B4/verification_manuelle_20261004:/verification:ro \
  -v "$PWD/../00_Pilotage/Integration_transversale:/integration" \
  ops python /integration/verifier_nouveaux_articles.py \
  --directory /verification \
  --output /integration/Preuves/Controle_nouveaux_articles_nouveau_passage.json \
  --index
```

Une copie du script est fournie dans `scripts/verifier_nouveaux_articles.py` du bloc 4. Il utilise les connexions B2 et leurs secrets montés dans le conteneur, avec vérification TLS. Il refuse un article exclu, une divergence entre B3 et B2 ou une mention déjà présente qui correspond à une autre version. Il ne supprime aucune ancienne version automatiquement. Les identifiants déterministes de l’export évitent les doublons lors du rejeu identique.

## Portée pour la soutenance

La collecte ne déclenche pas automatiquement l’inférence. L’opérateur fournit les nouveaux textes au modèle existant, exporte puis indexe les mentions. Pour une correction de texte, il faut aussi retirer les mentions de la version remplacée suivant la procédure de rectification ; ce cas n’a pas été exécuté sur ces cinq articles.

Cet essai démontre le raccordement manuel de nouvelles données et leur consultation. Il ne mesure pas l’exactitude des neuf mentions. Les captures, la vidéo et le fichier d’inférence complète sur les 21 676 articles initiaux décrivent leur propre instantané ; le complément de neuf mentions est attesté séparément.

Documentation technique du protocole : [Bulk API Elasticsearch 8.19](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/docs-bulk.html) et [Count API Elasticsearch 8.19](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/search-count.html).
