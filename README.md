# Mémoire OSINT : gouvernance, architecture, pipeline et IA

Extension locale TASS : [mode d’emploi](bloc3_pipeline/Collecte_TASS.md), [plan B3](bloc3_pipeline/Plan_pipeline_OSINT.pdf), [vidéo fictive actuelle](bloc3_pipeline/Demonstration_locale_pipeline.mp4) et [preuves expurgées](bloc3_pipeline/verification/). Préparer le volume AES-256 avec Preparer_volume_chiffre.command, saisir personnellement le mot de passe puis utiliser Lancer_Observatoire_TASS.command. Le lanceur refuse un remplacement en clair. Activation et migration physiques vérifiées sur le poste de réalisation, voir verification/Volume_chiffre.json. Droits, secours, reprise et monitoring sont testés. B4 conserve ses modèles. FINALISATION_B3_MAP.json identifie les sources et l’expurgation ; SOURCE_MAP.json conserve la provenance historique.

La [gouvernance B1 actualisée](bloc1_gouvernance/Plan_gouvernance_OSINT.pdf) accompagne les dépendances directes de la collecte. Les 33 critères B3 sont suivis ; les huit critères de prestation orale restent prévus. Le dossier Drive lié ci-dessous conserve sa version précédente : cette livraison actualise GitHub et le dossier local uniquement.


Projet transversal d’Edouard Cappaert pour une cellule de veille documentaire fictive. Un analyste et un responsable de veille explorent les mentions d’armes, d’unités et d’organisations militaires dans le corpus TASS afin de préparer des notes sourcées. Une mention constitue une information à vérifier dans son contexte.

## Essayer l’Observatoire sans mot de passe

```sh
cd bloc3_pipeline
python3 scripts/demo_collection_fixture.py .demo-publique 18743
```

Ouvrir `http://127.0.0.1:18743`. Choisir Militaire et défense et la journée du 26 novembre 2023 pour récupérer cinq articles fictifs sans accès au réseau TASS. Python 3.12 suffit, sans Docker ni dépendance. Ctrl+C arrête le serveur. Ce test public n’utilise aucune donnée réelle. Le mot de passe du volume protège les données privées du poste ; il ne conditionne ni l’accès au code ni cette démonstration.

## Les quatre blocs

| Bloc | Contenu | Code |
| --- | --- | --- |
| 1 | Gouvernance, responsabilités, qualité, risques et procédures | Plan de gouvernance dans le dossier de remise |
| 2 | PostgreSQL, MongoDB, Elasticsearch, TLS, rôles, sauvegarde et restauration | [bloc2_architecture](bloc2_architecture/) |
| 3 | Import JSON/JSONL, validation, déduplication, publication, reprise et suivi | [bloc3_pipeline](bloc3_pipeline/) |
| 4 | NER spaCy, trois labels, annotations, entraînement, inférence, surveillance et livraison | [bloc4_ia](bloc4_ia/) |

[Dossier de remise et supports par bloc](https://drive.google.com/drive/folders/1J8Z47ahaArvT0LjxEmnu_0ozatUgiXuO). Les consignes, grilles, rapports, vidéos et artefacts sont identifiés dans ce dossier. Télécharger l’archive complète pour conserver ses liens locaux.

## Démarrage sans corpus externe

Python 3.12 est utilisé pour les vérifications. Le pipeline B3 utilise la bibliothèque standard.

```sh
cd bloc3_pipeline
python3 -m pipeline worker --config config/portable.json
python3 -m pipeline status --state .state-portable
python3 tests/integration.py
```

Pour l’IA, depuis la racine du dépôt :

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r bloc4_ia/requirements.lock.txt
.venv/bin/python -m pip install --no-deps -e bloc4_ia
cd bloc4_ia
../.venv/bin/python -m pytest -q
../.venv/bin/python scripts/prepare_ci_demo.py
../.venv/bin/python scripts/ci_local.py
```

La démonstration CI génère exclusivement des textes synthétiques, entraîne un petit modèle de contrôle, construit et installe le wheel, puis démarre et vérifie le service sur le loopback du runner. Ce service est arrêté après le contrôle. Aucun déploiement public permanent n’est effectué par le workflow.

L’architecture B2 nécessite Docker et des secrets générés localement. Suivre [son mode d’emploi](bloc2_architecture/README.md). Le workflow contrôle son code et sa configuration ; les essais complets sur les stockages et les volumes sont documentés dans la remise.

## Résultats et limites

La version locale identifiée du pipeline a accepté 21 676 articles. L’inférence complète de la baseline expérimentale a produit 39 511 mentions. Quatorze tests de mécanismes B3 et trente-deux tests IA ont été exécutés localement. Les preuves, versions et conditions de mesure sont fournies dans les livrables.

Le modèle TASS livré est entraîné sur des préannotations lexicales. Sa qualité métier n’est pas validée. Un [diagnostic sur 18 articles proposés par une IA](bloc4_ia/docs/Diagnostic_et_revue_assistee.md) donne un F1 micro de 44,93 %, un rappel de 29,81 % et 73 omissions par rapport à ce brouillon. Ce diagnostic ne remplace pas une référence humaine. Les F1 historiques de 34 %, 49,82 et 56,55 correspondent à des protocoles non réconciliés et ne sont pas des scores de cette baseline. Une relecture humaine historique est déclarée dans le notebook, avec les annotations correspondantes toujours non retrouvées. La relecture humaine requise et la mesure sur une référence traçable restent nécessaires.

Le corpus réel et le modèle TASS sérialisé sont distribués dans le périmètre de remise choisi par le candidat, sans être ajoutés à ce dépôt de code. Les tests publics utilisent uniquement des fixtures synthétiques. Les paramètres de promotion sont des choix de projet, pas des seuils de certification.

## Organisation de la livraison

Le workflow [verification.yml](.github/workflows/verification.yml) exécute les contrôles des trois ensembles de code. Les identités exactes du commit et des exécutions réussies doivent être consultées dans GitHub Actions et dans le rapport de publication du dossier de pilotage. Un badge ou la présence d’un workflow ne prouve pas à lui seul son succès.

`SOURCE_MAP.json` rattache le code initial aux archives locales de remise. Les adaptations du dépôt concernent son organisation, le workflow commun et le générateur de démonstration synthétique. Les modes d’emploi des blocs conservent leur contexte de version locale ; les ajouts de publication sont précisés ici et dans l’addendum de remise.

## Crédits et droits

Les travaux collectifs historiques conservent les crédits Edouard Cappaert, Jean-Christophe Dorn et Noah Segonds, ainsi que les références pédagogiques de Matthieu Larboullet. L’adaptation actuelle et les vérifications ont été assistées par Codex. Les anciens coauteurs ne sont pas présentés comme ayant validé cette nouvelle version.

La mise à disposition du code ne crée pas de licence sur les cours, les textes TASS ou les ressources tierces. Aucune licence générale de réutilisation n’est ajoutée sans clarification des droits. Chaque dépendance conserve sa licence.
