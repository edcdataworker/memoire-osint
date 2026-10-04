# Bloc 4 : solution IA OSINT

Version locale de démonstration, 4 octobre 2026. Extraction spaCy des labels WEAPON, MIL_UNIT et MIL_ORG dans les articles TASS. Les prédictions ne sont pas validées sur une référence humaine indépendante. Les scores qualité restent indisponibles.

## Livrables

1. `Rapport_solution_IA_OSINT.pdf` : plan historique conservé, pipeline, modèle, dashboards, métriques et note d’analyse.
2. `Presentation_Bloc4.pptx` et `Guide_oral_Bloc4.md` : support de cinq minutes et questions du jury.
3. `src/osint_ner/` : code de développement, contrats, annotation, apprentissage, évaluation, inférence, monitoring, registre et interface.
4. `scripts/ci_local.py`, `.github/workflows/tests.yml`, `config/` : code de déploiement local et workflow cloud préparé.
5. `Preuves/` : exécutions, tests, captures, manifests et vidéo si présente.
6. `Correspondance_criteres_Bloc4.json` : les 41 critères exacts, état, preuves et limites.
7. `Revue_annotations_locale.html` : interface de revue de 18 articles, sans attestation préremplie.

## Installation

Python3.12 et CPU. Les dépendances viennent des paquets publics, aucune donnée d’article n’est envoyée à un service. Depuis ce dossier :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
```

Le fichier de verrou a été vérifié sur macOS ARM64. Les wheels disponibles et versions système peuvent différer sur d’autres plateformes. Les articles et modèles locaux sont sous `.state/`, exclus du dépôt. Les récupérer via les artefacts locaux autorisés ou les reconstruire ci-dessous.

## Exécution reproductible

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -m osint_ner.cli prepare --corpus ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/data
.venv/bin/python scripts/audit_splits.py
.venv/bin/python -m osint_ner.cli train --train .state/data/train.jsonl --dev .state/data/dev.jsonl --output .state/runs/new-run --epochs 6
.venv/bin/python -m osint_ner.cli infer --run .state/runs/new-run --input ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/inference.jsonl
.venv/bin/python -m osint_ner.cli export-es --input .state/inference.jsonl --output .state/es-mentions.ndjson --exclusions ../02_Bloc_2_Architecture/.state/erasures.json
```

Le nom de run doit être neuf. Adapter le chemin du registre réel d’exclusion, vérifier sa présence et sa forme, puis toujours l’appliquer à l’inférence ET à l’export en exploitation. Le corpus B3 JSONL est accepté sans renettoyage. Le mapping distinct est dans `config/elasticsearch-entities-mapping.json`. L’import dans Elasticsearch TLS relève du raccordement B2/B3/B4, sans toucher l’index des articles.

## Revue et évaluation

Ouvrir `Revue_annotations_locale.html`. Lire chaque article complet, corriger les propositions, renseigner le relecteur puis attester les articles effectivement relus. Exporter `human-reviewed.jsonl` et le placer dans `.state/data/`. Les 18 exemples sont réservés au test et ne doivent pas intégrer train/dev. Le document `docs/Annotation_et_protocole.md` définit les règles et biais.

```sh
.venv/bin/python -m osint_ner.cli evaluate --run .state/runs/baseline --reference .state/data/human-reviewed.jsonl --manifest .state/data/split_manifest.jsonl --output Preuves/quality_human_sample.json
```

Cette commande refuse une référence sans provenance de revue. Une performance sur un petit échantillon assisté ne constitue pas une validation de production.

## Interface, automatisation et livraison

```sh
.venv/bin/python -m osint_ner.cli serve --data .state/inference.jsonl --run .state/runs/baseline --port 8764
.venv/bin/python -m osint_ner.cli watch --train .state/data/train.jsonl --dev .state/data/dev.jsonl --state .state/scheduler --cycles 2 --interval 1 --demo --epochs 3
.venv/bin/python -m osint_ner.cli monitor --reference .state/data/train.jsonl --current .state/data/dev.jsonl --output Preuves/monitor_current.json
.venv/bin/python scripts/ci_local.py
```

L’interface écoute sur http://127.0.0.1:8764. La chaîne CI/CD locale livre un wheel identifié et contrôle le service sur 8765. Le workflow GitHub est préparé, sans preuve d’exécution distante. L’ordonnanceur normal exige des labels revus ; le mode démo mesure le mécanisme sans promouvoir un modèle non validé.

## Tests et limites

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python scripts/benchmark.py
```

Les tests couvrent contrats, offsets Unicode, doublons, métriques sur fixtures, protection de promotion, dérive, exclusions et HTTP. Ils ne mesurent pas l’exactitude NER réelle. `erase` traite un export local et indique les autres purges nécessaires, sans prétendre désapprendre un modèle. Voir `docs/Integration_securite_gouvernance.md`.

## Crédits et contribution

Le rendu de cours historique reste attribué à Jean-Christophe Dorn, Noah Segonds et Edouard Cappaert, encadrés par Matthieu Larboullet. Le nouveau code et les documents ont été préparés pour le mémoire d’Edouard Cappaert avec assistance Codex. Edouard doit les relire, maîtriser et assumer les choix présentés. Aucune nouvelle contribution des co-auteurs historiques n’est présumée. TASS est la source des articles ; aucune publication des textes ou du modèle n’est autorisée par cette préparation locale.

## Références

Cours AI Deployment, pages 21 à 31 ; Design Thinking, pages 6 et 8 à 15 ; grille Bloc 4 A6:A46. Documentation technique consultée le 4 octobre 2026 : https://spacy.io/usage/training et https://spacy.io/api/entityrecognizer. Les dépendances logicielles conservent leurs licences respectives. Le code local est consultable dans Git, sans dépôt distant nouvellement publié.

## Artefacts locaux fournis et démarrage court

`Artefacts_locaux/Modele_baseline_OSINT.zip` contient le modèle sérialisé, ses DocBin et son rapport. `Jeux_reproductibles_OSINT.zip` contient les 240 articles train, 60 dev, la file de revue et les manifestes. Ces archives contiennent des données du corpus et restent dans le périmètre local contrôlé. Le fichier `Manifest_artefacts.json` donne leurs SHA-256.

```sh
mkdir -p .state/runs/baseline .state/data
unzip Artefacts_locaux/Modele_baseline_OSINT.zip -d .state/runs/baseline
unzip Artefacts_locaux/Jeux_reproductibles_OSINT.zip -d .state/data
.venv/bin/python -m osint_ner.cli serve --data Artefacts_locaux/Fixture_5_articles_reels.jsonl --run .state/runs/baseline --port 8764
```

Ce parcours affiche cinq articles réels avec le modèle livré. L’inférence complète de cette exécution reste dans `.state/inference-full.jsonl` ; pour reconstruire la totalité, fournir le corpus B3 autorisé et appliquer le registre d’exclusion courant. La vidéo et les captures finales utilisent les 21 676 sorties complètes, pas le petit fixture portable.

Le code de la solution a été vérifié par 32 tests et une chaîne locale au commit `5d571ee`. Les modifications documentaires ultérieures ne modifient pas les modules applicatifs. Les identités précises figurent dans `Preuves/Versions.json`. La vidéo finale décrit une capture réelle de l’interface locale ; ses caractéristiques sont vérifiées avec ffprobe et consignées dans `Preuves/Video_metadata.json`.
