# Mémoire OSINT : gouvernance, architecture, pipeline et IA

Remise du 5 octobre 2026 : ce dépôt commun rassemble la gouvernance et les trois ensembles de code. Ouvrir le [dossier Drive organisé par bloc](https://drive.google.com/drive/folders/1n-Q7gYPQdEMPQ7oR5oZR2_1spRJqZpQT) ou son [index PDF cliquable](https://drive.google.com/file/d/1aFEyXBpYe0BEiLRSG3ymfJxwcdaGH62m/view?usp=drivesdk) pour les présentations, vidéos et archives figées. Le tag `remise-2026-10-05` identifie la version de code remise.

Pour le Bloc 4, ouvrir le [code de développement](bloc4_ia/src/osint_ner/), le [script de déploiement](bloc4_ia/scripts/ci_local.py), le [générateur de démonstration synthétique](bloc4_ia/scripts/prepare_ci_demo.py) et le [workflow commun](.github/workflows/verification.yml). Le [guide de reproduction](bloc4_ia/REPRODUCTION.md) décrit leur exécution. Les deux archives Drive incluent le runtime nécessaire ; elles constituent deux entrées de lecture vers le même ensemble de code.

Extension locale TASS : [mode d’emploi](bloc3_pipeline/Collecte_TASS.md), [plan du Bloc 3](bloc3_pipeline/Plan_pipeline_OSINT.pdf) et [preuves expurgées](bloc3_pipeline/verification/). Préparer le volume AES-256 avec Preparer_volume_chiffre.command, saisir personnellement le mot de passe puis utiliser Lancer_Observatoire_TASS.command. Le lanceur refuse un remplacement en clair. Activation et migration physiques vérifiées sur le poste de réalisation, voir verification/Volume_chiffre.json. Les modèles du Bloc 4 restent identiques. FINALISATION_B3_MAP.json et SOURCE_MAP.json conservent la provenance des sources.


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
| Bloc 1 | Gouvernance, responsabilités, qualité, risques et procédures | [Plan de gouvernance](bloc1_gouvernance/Plan_gouvernance_OSINT.pdf) |
| Bloc 2 | PostgreSQL, MongoDB, Elasticsearch, TLS, rôles, sauvegarde et restauration | [Code](bloc2_architecture/) et [plan d’infrastructure](bloc2_architecture/Plan_infrastructure_OSINT.pdf) |
| Bloc 3 | Import JSON/JSONL, validation, déduplication, publication, reprise et suivi | [Code](bloc3_pipeline/) et [plan pipeline](bloc3_pipeline/Plan_pipeline_OSINT.pdf) |
| Bloc 4 | NER spaCy, trois labels, annotations, entraînement, inférence, surveillance et livraison | [Développement](bloc4_ia/src/osint_ner/), [déploiement](bloc4_ia/scripts/ci_local.py) et [rapport](bloc4_ia/Rapport_solution_IA_OSINT.pdf) |

[Dossier de remise et supports par bloc](https://drive.google.com/drive/folders/1n-Q7gYPQdEMPQ7oR5oZR2_1spRJqZpQT). Les rapports, présentations, codes et vidéos sont identifiés dans ce dossier. Télécharger l’archive complète pour conserver sa version et son manifeste. Les vidéos montrent un environnement local ; elles ne démontrent pas une exploitation externe de production, demandée dans l’email pour les Blocs 2 et 3.

## Démarrage sans corpus externe

Python 3.12 est utilisé pour les vérifications. Le pipeline du Bloc 3 utilise la bibliothèque standard.

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

L’architecture du Bloc 2 nécessite Docker et des secrets générés localement. Suivre [son mode d’emploi](bloc2_architecture/README.md). Le workflow contrôle son code et sa configuration ; les essais complets sur les stockages et les volumes sont documentés dans la remise.

## Résultats et limites

Le pipeline initial a accepté 21 676 articles. L’inférence complète de la baseline expérimentale a produit 39 511 mentions. Les tests du pipeline, les 40 tests IA et le déploiement éphémère sur données synthétiques sont exécutés par le workflow commun. Les preuves, versions et conditions de mesure sont fournies dans les livrables et les exécutions GitHub Actions.

Le modèle TASS livré est entraîné sur des préannotations lexicales. Sa qualité métier n’est pas validée. Le [diagnostic exploratoire sur 42 articles](bloc4_ia/docs/Diagnostic_IA_42_articles.md) donne un F1 micro de 32,73 % contre une référence proposée par IA. Le modèle est inchangé. L’[interface de revue humaine](bloc4_ia/docs/Revue_humaine_42_articles.md) contrôle les attestations et la provenance sur des fixtures ; elle n’atteste pas les 42 articles réels. Une revue humaine et une mesure sur une référence indépendante restent à réaliser.

Le corpus réel et le modèle TASS sérialisé sont distribués dans le périmètre de remise choisi par le candidat, sans être ajoutés à ce dépôt de code. Les tests publics utilisent uniquement des fixtures synthétiques. Les paramètres de promotion sont des choix de projet, pas des seuils de certification.

## Organisation de la livraison

Le workflow [verification.yml](.github/workflows/verification.yml) exécute les contrôles des trois ensembles de code. Les identités exactes du commit et des exécutions réussies doivent être consultées dans GitHub Actions et dans le rapport de publication du dossier de pilotage. Un badge ou la présence d’un workflow ne prouve pas à lui seul son succès.

`SOURCE_MAP.json` rattache le code initial aux archives locales de remise. Les adaptations du dépôt concernent son organisation, le workflow commun et le générateur de démonstration synthétique. Les modes d’emploi des blocs conservent leur contexte de version locale ; les ajouts de publication sont précisés ici et dans l’addendum de remise.

## Crédits et droits

Les travaux collectifs historiques conservent les crédits Edouard Cappaert, Jean-Christophe Dorn et Noah Segonds, ainsi que les références pédagogiques de Matthieu Larboullet. L’adaptation actuelle et les vérifications ont été assistées par Codex. Les anciens coauteurs ne sont pas présentés comme ayant validé cette nouvelle version.

La mise à disposition du code ne crée pas de licence sur les cours, les textes TASS ou les ressources tierces. Aucune licence générale de réutilisation n’est ajoutée sans clarification des droits. Chaque dépendance conserve sa licence.
