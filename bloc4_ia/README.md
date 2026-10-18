# Bloc 4 : solution IA OSINT

Version locale de démonstration, 18 octobre 2026. Extraction spaCy des labels WEAPON, MIL_UNIT et MIL_ORG dans les articles TASS. Préannotation par règles lexicales et contrôle complémentaire par IA. Le diagnostic élargi sur 42 articles mesure un F1 de 32,73 % contre une référence générée par IA ; son protocole et ses limites sont décrits dans `docs/Diagnostic_IA_42_articles.md`.

## Livrables

1. `Rapport_solution_IA_OSINT.pdf` : pipeline, modèle, dashboards, métriques et note d’analyse.
2. `Presentation_Bloc4.pptx` : présentation de 19 diapositives : 15 principales pour cinq minutes indicatives, puis 4 annexes distinctes. Le guide de préparation orale reste local.
3. `src/osint_ner/` : code de développement, contrats, annotation, apprentissage, évaluation, inférence, monitoring, registre et interface.
4. `scripts/ci_local.py`, `.github/workflows/tests.yml`, `config/` : code de déploiement local, passerelle stable, retour arrière et workflow GitHub.
5. `verification/` : exécutions, tests, captures, manifests et vidéo si présente.
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

Le fichier de verrou a été vérifié sur macOS ARM64. Les wheels disponibles et versions système peuvent différer sur d’autres plateformes. Les articles et modèles locaux sont sous `.state/`, exclus du dépôt. Sur le poste de démonstration, ce chemin et les copies B4 inventoriées pointent vers le volume chiffré `/Volumes/MemoireOSINT/B4/Copies/`. Monter ce volume avant l’utilisation et conserver les liens : un volume absent doit provoquer un échec, sans recréer une copie en clair. Voir `verification/Protection_copies_B4.json`.

## Exécution reproductible

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
.venv/bin/python -m osint_ner.cli prepare --corpus ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/data
.venv/bin/python scripts/audit_splits.py
.venv/bin/python -m osint_ner.cli train --train .state/data/train.jsonl --dev .state/data/dev.jsonl --output .state/runs/new-run --epochs 6
.venv/bin/python -m osint_ner.cli infer --run .state/runs/new-run --input ../00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json --output .state/inference.jsonl
.venv/bin/python -m osint_ner.cli export-es --input .state/inference.jsonl --output .state/es-mentions.ndjson --exclusions ../bloc2_architecture/.state/erasures.json
```

Le nom de run doit être neuf. Adapter le chemin du registre réel d’exclusion, vérifier sa présence et sa forme, puis toujours l’appliquer à l’inférence ET à l’export en exploitation. Le corpus B3 JSONL est accepté sans renettoyage. Le mapping distinct est dans `config/elasticsearch-entities-mapping.json`. L’import dans Elasticsearch TLS relève du raccordement B2/B3/B4, sans toucher l’index des articles.

## Contrôle par IA et évaluation

Le diagnostic livré utilise les propositions de Codex sur 18 articles réservés au test, avec 104 mentions et une correspondance exacte des labels et offsets. Voir `verification/Diagnostic_annotations_IA.json`. Ces articles ne doivent pas intégrer train/dev. Les outils de revue permettent de corriger les propositions et de constituer une référence supplémentaire. La commande ci-dessous concerne cette référence documentée ; elle est distincte du diagnostic IA déjà livré.

```sh
.venv/bin/python -m osint_ner.cli evaluate --run .state/runs/baseline --reference .state/data/human-reviewed.jsonl --manifest .state/data/split_manifest.jsonl --output verification/quality_human_sample.json
```

Cette commande contrôle la provenance de revue et l’indépendance du test. Les résultats restent attachés au protocole et à la version de référence utilisés.

## Interface, automatisation et livraison

```sh
.venv/bin/python -m osint_ner.cli serve --data .state/inference.jsonl --run .state/runs/baseline --port 8764
.venv/bin/python -m osint_ner.cli watch --train .state/data/train.jsonl --dev .state/data/dev.jsonl --state .state/scheduler --cycles 2 --interval 1 --demo --epochs 3
.venv/bin/python -m osint_ner.cli monitor --reference .state/data/train.jsonl --current .state/data/dev.jsonl --output verification/monitor_current.json
.venv/bin/python scripts/ci_local.py
```

L’interface conserve les filtres, les couleurs et le retour aux passages sources. Elle ajoute un formulaire de prédiction sur un texte nouveau. `POST /api/predict` reçoit un objet JSON avec le seul champ `text`, renvoie entités, offsets Unicode, empreintes et durée, sans enregistrer la saisie. Une seule inférence simultanée est admise ; une requête concurrente reçoit 429. `GET /api/metrics` donne les compteurs et durées du processus, sans texte source. Le service reste limité à la boucle locale.

```sh
curl -H 'Content-Type: application/json' -d '{"text":"NATO mentioned a Kalibr missile."}' http://127.0.0.1:8764/api/predict
```

Pour un réentraînement évalué, fournir les annotations train et dev revues, une référence de test revue et son manifeste figé :

```sh
.venv/bin/python -m osint_ner.cli watch --train .state/data/train-reviewed.jsonl --dev .state/data/dev-reviewed.jsonl --reference .state/data/human-reviewed.jsonl --manifest .state/data/split_manifest.jsonl --current .state/current-articles.jsonl --state .state/scheduler-reviewed --cycles 2 --interval 60 --epochs 6
```

Chaque changement d’empreinte produit un candidat immuable, son évaluation, le monitoring et une décision de promotion. Le modèle courant reste en place en cas de refus. La commande n’atteste aucune revue humaine : elle exige les fichiers réellement relus. L’option `--delivery-config` permet ensuite de reconstruire les prédictions et de livrer automatiquement le candidat accepté ; en cas d’échec, le registre précédent est restauré. Voir `docs/Automatisation_et_exploitation.md`.

Pour construire, tester et livrer un service qui reste actif après la commande :

```sh
.venv/bin/python scripts/ci_local.py --data .state/inference-full.jsonl --run .state/runs/baseline --state .state/delivery --proofs verification/Delivery --persistent --port 8766
.venv/bin/python -m osint_ner.deployment status --state .state/delivery/service
.venv/bin/python -m osint_ner.deployment rollback --state .state/delivery/service
.venv/bin/python -m osint_ner.deployment stop --state .state/delivery/service
```

La passerelle conserve l’adresse http://127.0.0.1:8766. Elle bascule vers un nouveau processus seulement après contrôle de santé et garde la version précédente pour le retour arrière. Les processus survivent à la fermeture du terminal, pas à un redémarrage du Mac. Pour déclencher la chaîne automatiquement sur changement des sources, remplacer la première commande par `scripts/watch_delivery.py` avec les mêmes arguments, sans `--persistent`, et ajouter `--cycles 360 --interval 10`. Cela observe pendant environ une heure hors temps de livraison ; aucune tâche système permanente n’est installée. Un changement déclenche build, tests et déploiement sans étape manuelle intermédiaire ; les sources inchangées sont ignorées.

Le workflow GitHub exécute la même chaîne sur une fixture explicite dans un runner éphémère. La révision courante est vérifiée localement ; aucune nouvelle exécution GitHub ni publication distante ne lui est attribuée. Le service TASS reste un environnement local de démonstration. Une livraison applicative ne valide pas la qualité du modèle.

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

La vérification initiale comportait 32 tests au commit `5d571ee`. Les tests de la révision courante et les empreintes des sources figurent dans `Preuves_complement_20261018/`. La révision du 18 octobre ajoute une API de prédiction et une livraison locale persistante ; ses preuves sont distinctes de cette exécution initiale. Les identités précises figurent dans `verification/Versions.json`. La vidéo finale décrit une capture réelle de l’interface locale ; ses caractéristiques sont vérifiées avec ffprobe et consignées dans `verification/Video_metadata.json`.

## Complément de finalisation

Le code public est disponible sur [GitHub](https://github.com/edcdataworker/memoire-osint). Le workflow commun y contrôle B2, B3 et B4 et livre un service IA éphémère sur données synthétiques dans son runner. L’archive `Code_OSINT_GitHub.zip` conserve cette organisation commune. La version locale initiale et la publication sont identifiées séparément dans l’addendum de remise.

Un [diagnostic initial et une revue assistée](docs/Diagnostic_et_revue_assistee.md) complètent les préannotations : 18 articles, 104 mentions proposées par Codex, F1 diagnostic de 44,93 %. Cette évaluation exploratoire mesure l’accord avec les propositions IA. `Revue_annotations_assistee_IA.html` permet de corriger les frontières, labels et décisions de périmètre. Le modèle reste identique.

Un [raccordement manuel sur cinq nouveaux articles](docs/Raccordement_manuel_nouveaux_articles.md) a été exécuté le 4 octobre 2026 : inférence en 1,476 seconde avec le modèle existant, neuf mentions indexées et relues avec le compte lecteur. L’index local contient désormais 39 520 mentions. Le rejeu conserve ce total. Ce complément démontre le parcours de nouvelles données ; il ne déclenche aucun réentraînement et ne mesure pas la qualité NER.

Le [diagnostic élargi](docs/Diagnostic_IA_42_articles.md) conserve les 18 articles initiaux et ajoute 24 articles du test figé, sélectionnés par longueur sans consulter les prédictions. Il porte sur 42 articles et 254 mentions proposées par IA : précision 71,05 %, rappel 21,26 %, F1 32,73 %. Le changement de score provient de la référence élargie ; les poids du modèle sont identiques. Ce résultat exploratoire confirme les omissions, surtout sur les textes longs. Les révisions locales et la migration du stockage ne sont pas attribuées au run GitHub antérieur.

## Revue humaine des 42 articles

Le [parcours de revue](docs/Revue_humaine_42_articles.md) permet de corriger les propositions, enregistrer les décisions sur le volume chiffré, puis calculer la qualité sur le test figé. Les prédictions sont masquées pendant la lecture. Aucun article réel n’est attesté par les tests automatiques ; la revue personnelle reste à effectuer. Démarrer le lanceur Lancer_revue_humaine.command depuis le dossier B4.


Codex a examiné les 42 textes de test et corrigé les propositions comme IA. La méthode est décrite dans [le guide de revue](docs/Revue_humaine_42_articles.md). L’attestation et les décisions détaillées sont dans le dossier chiffré privé, fichier `Codex_prelecture_attestation_42.json`, empreinte 2f889f6130008464c181fb4e72ae134e4f9dc7be9da717a2d3292109d87f9d79. Elles ne constituent pas une validation humaine. La remise comporte 0/42 attestations humaines ; aucune métrique humaine n’est calculée. Le [parcours local](Lancer_revue_humaine.command) attend ta lecture personnelle pour attester chaque article.

## Serving conteneurisé

Le Dockerfile construit le paquet avec les versions Linux de `requirements.docker.lock.txt`. `.dockerignore` limite le contexte aux sources et à la configuration de construction : ni corpus, ni modèle, ni état privé ne sont intégrés. Les artefacts autorisés sont montés séparément en lecture seule.

```sh
docker build -t memoire-osint-bloc4:local .
OSINT_ARTIFACTS=/chemin/absolu/autorise docker compose up -d
OSINT_ARTIFACTS=/chemin/absolu/autorise docker compose stop
```

Le dossier doit contenir `inference.jsonl` et `runs/baseline/`. Le service est publié uniquement sur `127.0.0.1:18767`, avec utilisateur 10001, racine en lecture seule, capacités retirées et ressources bornées. `--host 0.0.0.0` sert à l’écoute interne du conteneur ; l’écoute native conserve son défaut local et les protections Host/Origin restent actives. Le serveur standard répond aux besoins de l’API locale sans ajouter de framework. Ce choix n’atteste pas un déploiement Internet.

L’essai `scripts/test_docker.py` vérifie santé, prédiction, métriques, rejet d’un Host tiers et protections du conteneur, puis le supprime. Il accepte seulement des fixtures explicitement synthétiques préparées avec `scripts/prepare_ci_demo.py --state DOSSIER_NEUF`. Preuve exécutée : `Preuves_complement_20261018/Docker.json`. Le workflow inclut désormais cet essai, sans attribuer de succès à une exécution GitHub non réalisée.

Correspondance avec l’arborescence proposée : `src/osint_ner/data.py` prépare les données, `model.py` entraîne et évalue, `server.py` fournit l’API, `monitor.py` suit la dérive, `automation.py` réentraîne et `deployment.py` livre. Les tests sont dans `tests/`, les modèles locaux restent hors dépôt et sont montés comme artefacts. Les scripts remplacent les notebooks exécutables ; Kubernetes n’est pas utilisé sur cette cible locale. Les scores métier restent conditionnés à une référence indépendante revue par une personne.


## Actualisation du 19 octobre 2026

Le refus de calculer une évaluation humaine sur 42 brouillons a été vérifié sur la référence réelle, sans changer les annotations. Preuve : `verification/Corrections_20261019/Garde_revue_humaine.json`. La prochaine action reste une lecture, correction et attestation par une personne. Les textes du test ne doivent pas servir à entraîner un candidat évalué ensuite sur ces mêmes textes.

Publication précédente et CI : https://github.com/edcdataworker/memoire-osint/actions/runs/39174668036. Cette révision publie les compléments du 19 octobre. Leur CI est consultable dans GitHub Actions. Les guides oraux et vidéos restent exclus de cette publication.
