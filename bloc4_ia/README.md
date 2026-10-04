# Bloc 4 : solution IA OSINT

Remise du 5 octobre 2026 : le [guide de reproduction](REPRODUCTION.md) ouvre le développement et le déploiement de cette version commune. Le tag `remise-2026-10-05` et le manifeste Drive identifient les sources remises.

Version locale de démonstration, 4 octobre 2026. Extraction spaCy des labels WEAPON, MIL_UNIT et MIL_ORG dans les articles TASS. Préannotation par règles lexicales et contrôle complémentaire par IA. Le diagnostic élargi sur 42 articles mesure un F1 de 32,73 % contre une référence générée par IA ; son protocole et ses limites sont décrits dans `docs/Diagnostic_IA_42_articles.md`.

## Livrables

1. `Rapport_solution_IA_OSINT.pdf` : pipeline, modèle, dashboards, métriques et note d’analyse.
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

Le fichier de verrou a été vérifié sur macOS ARM64. Les wheels disponibles et versions système peuvent différer sur d’autres plateformes. Les articles et modèles locaux sont sous `.state/`, exclus du dépôt. Sur le poste de démonstration, ce chemin et les copies B4 inventoriées pointent vers le volume chiffré `/Volumes/MemoireOSINT/B4/Copies/`. Monter ce volume avant l’utilisation et conserver les liens : un volume absent doit provoquer un échec, sans recréer une copie en clair. Voir `Preuves/Protection_copies_B4.json`.

## Exécution reproductible

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -m osint_ner.cli prepare --corpus ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/data
.venv/bin/python scripts/audit_splits.py
.venv/bin/python -m osint_ner.cli train --train .state/data/train.jsonl --dev .state/data/dev.jsonl --output .state/runs/new-run --epochs 6
.venv/bin/python -m osint_ner.cli infer --run .state/runs/new-run --input ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/inference.jsonl
.venv/bin/python -m osint_ner.cli export-es --input .state/inference.jsonl --output .state/es-mentions.ndjson --exclusions ../02_Bloc_2_Architecture/.state/erasures.json
```

Le nom de run doit être neuf. Adapter le chemin du registre réel d’exclusion, vérifier sa présence et sa forme, puis toujours l’appliquer à l’inférence ET à l’export en exploitation. Le corpus B3 JSONL est accepté sans renettoyage. Le mapping distinct est dans `config/elasticsearch-entities-mapping.json`. L’import dans Elasticsearch TLS relève du raccordement entre les Blocs 2, 3 et 4, sans toucher l’index des articles.

## Contrôle par IA et évaluation

Le diagnostic exploratoire courant porte sur 42 articles du test figé, contre une référence proposée par Codex. Son F1 micro vaut 32,73 % ; il ne mesure pas une qualité validée par une personne. Voir [le protocole et les résultats](docs/Diagnostic_IA_42_articles.md), [la preuve publique expurgée](docs/Diagnostic_annotations_IA_42_articles.json) et [la revue humaine](docs/Revue_humaine_42_articles.md). Ces articles ne doivent pas intégrer train/dev. La commande ci-dessous concerne une référence réellement relue et attestée ; aucune attestation humaine n’est créée par la publication du code.

```sh
.venv/bin/python -m osint_ner.cli evaluate --run .state/runs/baseline --reference .state/data/human-reviewed.jsonl --manifest .state/data/split_manifest.jsonl --output Preuves/quality_human_sample.json
```

Cette commande contrôle la provenance de revue et l’indépendance du test. Les résultats restent attachés au protocole et à la version de référence utilisés.

## Interface, automatisation et livraison

```sh
.venv/bin/python -m osint_ner.cli serve --data .state/inference.jsonl --run .state/runs/baseline --port 8764
.venv/bin/python -m osint_ner.cli watch --train .state/data/train.jsonl --dev .state/data/dev.jsonl --state .state/scheduler --cycles 2 --interval 1 --demo --epochs 3
.venv/bin/python -m osint_ner.cli monitor --reference .state/data/train.jsonl --current .state/data/dev.jsonl --output Preuves/monitor_current.json
.venv/bin/python scripts/ci_local.py
```

L’interface écoute sur http://127.0.0.1:8764. La chaîne CI/CD locale livre un wheel identifié et contrôle le service sur 8765. Le [workflow commun](../.github/workflows/verification.yml) contrôle l’architecture, le pipeline et l’IA, construit le wheel et vérifie un service éphémère sur données synthétiques. Consulter l’exécution correspondant au commit de remise dans GitHub Actions ; la présence du workflow ne prouve pas son succès. Le fichier `.github/workflows/tests.yml` de ce dossier est un autre workflow, conservé pour la version locale ; sa présence ne constitue pas la preuve du run commun. L’ordonnanceur normal exige des labels revus ; le mode démo mesure le mécanisme sans promouvoir un modèle non validé.

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

Cours AI Deployment, pages 21 à 31 ; Design Thinking, pages 6 et 8 à 15 ; grille Bloc 4 A6:A46. Documentation technique consultée le 4 octobre 2026 : https://spacy.io/usage/training et https://spacy.io/api/entityrecognizer. Les dépendances logicielles conservent leurs licences respectives. Le code courant est publié dans le dépôt GitHub transversal ; les textes, états de revue et modèles réels restent locaux.

## Artefacts locaux fournis et démarrage court

`Artefacts_locaux/Modele_baseline_OSINT.zip` contient le modèle sérialisé, ses DocBin et son rapport. `Jeux_reproductibles_OSINT.zip` contient les 240 articles train, 60 dev, la file de revue et les manifestes. Ces archives contiennent des données du corpus et restent dans le périmètre local contrôlé. Le fichier `Manifest_artefacts.json` donne leurs SHA-256.

```sh
mkdir -p .state/runs/baseline .state/data
unzip Artefacts_locaux/Modele_baseline_OSINT.zip -d .state/runs/baseline
unzip Artefacts_locaux/Jeux_reproductibles_OSINT.zip -d .state/data
.venv/bin/python -m osint_ner.cli serve --data Artefacts_locaux/Fixture_5_articles_reels.jsonl --run .state/runs/baseline --port 8764
```

Ce parcours affiche cinq articles réels avec le modèle livré. L’inférence complète de cette exécution reste dans `.state/inference-full.jsonl` ; pour reconstruire la totalité, fournir le corpus B3 autorisé et appliquer le registre d’exclusion courant. La vidéo et les captures finales utilisent les 21 676 sorties complètes, pas le petit fixture portable.

La version de remise comporte 40 tests Python, notamment pour la revue d’annotations et la provenance du test indépendant. Le commit public et les empreintes des archives identifient le code courant. Ces tests utilisent des fixtures et ne valident pas les annotations réelles. La vidéo finale décrit une capture réelle de l’interface locale ; ses caractéristiques sont vérifiées avec ffprobe et consignées dans `Preuves/Video_metadata.json`.

## Complément de finalisation

Le code public est disponible sur [GitHub](https://github.com/edcdataworker/memoire-osint). Le workflow commun y contrôle les Blocs 2, 3 et 4 et livre un service IA éphémère sur données synthétiques dans son runner. L’archive `Code_OSINT_GitHub.zip` conserve cette organisation commune. Le tag de remise et le manifeste Drive rattachent les archives à cette version publique.

Un [diagnostic initial et une revue assistée](docs/Diagnostic_et_revue_assistee.md) complètent les préannotations : 18 articles, 104 mentions proposées par Codex, F1 diagnostic de 44,93 %. Cette évaluation exploratoire mesure l’accord avec les propositions IA. `Revue_annotations_assistee_IA.html` permet de corriger les frontières, labels et décisions de périmètre. Le modèle reste identique.

Un [raccordement manuel sur cinq nouveaux articles](docs/Raccordement_manuel_nouveaux_articles.md) a été exécuté le 4 octobre 2026 : inférence en 1,476 seconde avec le modèle existant, neuf mentions indexées et relues avec le compte lecteur. L’index local contient désormais 39 520 mentions. Le rejeu conserve ce total. Ce complément démontre le parcours de nouvelles données ; il ne déclenche aucun réentraînement et ne mesure pas la qualité NER.

Le [diagnostic élargi](docs/Diagnostic_IA_42_articles.md) conserve les 18 articles initiaux et ajoute 24 articles du test figé, sélectionnés par longueur sans consulter les prédictions. Il porte sur 42 articles et 254 mentions proposées par IA : précision 71,05 %, rappel 21,26 %, F1 32,73 %. Le changement de score provient de la référence élargie ; les poids du modèle sont identiques. Ce résultat exploratoire confirme les omissions, surtout sur les textes longs. Les révisions locales et la migration du stockage ne sont pas attribuées au run GitHub antérieur.

## Revue humaine des 42 articles

Le [parcours de revue](docs/Revue_humaine_42_articles.md) permet de corriger les propositions, enregistrer les décisions sur le volume chiffré, puis calculer la qualité sur le test figé. Les prédictions sont masquées pendant la lecture. Aucun article réel n’est attesté par les tests automatiques ; la revue personnelle reste à effectuer. Démarrer le lanceur Lancer_revue_humaine.command depuis le dossier B4.


Codex a examiné les 42 textes de test et corrigé les propositions comme IA. La méthode est décrite dans [le guide de revue](docs/Revue_humaine_42_articles.md). L’attestation et les décisions détaillées sont dans le dossier chiffré privé, fichier `Codex_prelecture_attestation_42.json`, empreinte 2f889f6130008464c181fb4e72ae134e4f9dc7be9da717a2d3292109d87f9d79. Elles ne constituent pas une validation humaine. La remise comporte 0/42 attestations humaines ; aucune métrique humaine n’est calculée. Le [parcours local](Lancer_revue_humaine.command) attend ta lecture personnelle pour attester chaque article.
