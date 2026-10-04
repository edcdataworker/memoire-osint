# Pipeline OSINT TASS, Bloc 3

Version actualisée : [Observatoire TASS local](Collecte_TASS.md), droits, monitoring et lecture de secours. Le PDF et la vidéo présentent cette version. Préparer Preparer_volume_chiffre.command, saisir le mot de passe personnellement dans Terminal, puis ouvrir Lancer_Observatoire_TASS.command. Le lanceur refuse un remplacement en clair. Volume_chiffre.json distingue préparation et activation effective.

Pour essayer l’interface publique sans corpus réel ni mot de passe, lancer la source fictive :

```sh
python3 scripts/demo_collection_fixture.py .demo-publique 18743
```

Ouvrir `http://127.0.0.1:18743`, choisir Militaire et défense et le 26 novembre 2023 comme début et fin, puis lancer la collecte. Cinq articles fictifs sont générés localement. Aucune requête TASS n’est effectuée. Arrêter avec Ctrl+C. Ce mode est réservé aux fixtures ; le lanceur du corpus réel conserve son exigence de volume chiffré. Le code public ne contient ni mot de passe ni clé.

Les sections suivantes conservent le mode d’emploi du pipeline historique de fichiers et ses commandes. Pour le collecteur, suivre le mode d’emploi dédié.

Version locale du 4 octobre 2026. Le pipeline collecte un fichier JSON ou JSONL autorisé, valide chaque article, retire les doublons exacts, conserve sa provenance et publie des données figées pour les blocs 2 et 4. Le code opérationnel utilise la bibliothèque standard Python 3.12 uniquement.

## Livrables et état réel

1. `Plan_pipeline_OSINT.pdf` et sa source `Plan_pipeline_OSINT.md` reprennent le plan Books : contexte, données, schéma, code, difficultés, résultats, utilisation et conclusion.
2. `pipeline/`, `tests/`, `scripts/`, `config/` : code et configuration. `Code_OSINT_Bloc3.zip` est la copie portable sans corpus réel, base locale ni secret.
3. `Preuves/Tests_pipeline.json` : 14 scénarios synthétiques, dont arrêt brutal au milieu d'une transaction et reprise autonome. `Preuves/Benchmark_pipeline.json` : volumes et durées réellement mesurés.
4. `Demonstration_locale_pipeline.mp4` : enregistrement du navigateur sur cinq articles fictifs, avec pause, reprise, panne du catalogue et restauration. Le ralentissement de démonstration est explicite. Il ne s'agit pas d'une exploitation externe en production.
5. `Correspondance_criteres_Bloc3.json` : les 33 critères exacts, preuves et écarts. `Preparation_orale_Bloc3.md` : trame de cinq minutes à répéter par Edouard.

Implémenté et testé : import, validation, nettoyage minimal, déduplication exacte, publication après qualité, persistance, planification bornée, reprise automatique, monitoring, alertes locales, effacement local et import d'un registre B2. Docker et Compose : construction et exécution locales vérifiées par le coordinateur, avec reprise au checkpoint 21 676 après correction de l’espace temporaire. Aucun job launchd/cron installé. Aucun envoi de notification à autrui.

## Démarrage portable en trois commandes

Ouvrir un terminal dans le dossier extrait. Python 3.12 ou ultérieur sur macOS ou Linux est requis (verrous POSIX). Aucune installation de dépendance n'est nécessaire pour traiter les données.

```sh
python3 -m pipeline schedule --config config/portable.json --first-delay 2
python3 -m pipeline status --state .state-portable
python3 -m pipeline serve --state .state-portable --port 18743
```

Ouvrir `http://127.0.0.1:18743`. Ce tableau n'expose pas les textes, seulement les métriques locales. Arrêter le serveur par Ctrl+C. Le planificateur sort après une exécution réussie par défaut. La fixture contient cinq articles explicitement synthétiques et aucune personne réelle.

Un second `worker` sur une source et un contrat identiques constate `unchanged_source`. Pour une exécution immédiate sans attendre la prochaine échéance sauvegardée :

```sh
python3 -m pipeline worker --config config/portable.json
python3 tests/integration.py
```

Le dossier `.state-portable` contient le registre durable, les exports et les logs. Ne pas supprimer ce dossier pour résoudre une erreur : il contient le point de reprise et les suppressions.

## Corpus réel et contrat avec les autres blocs

La configuration `config/corpus_clean.json` contient les chemins du poste de réalisation. Les adapter si le dossier est déplacé. Le brut retrouvé est dans `00_Pilotage/Sources/Artefacts_recuperes/data_set.json`. Le corpus nettoyé reconstitué est dans `00_Pilotage/Sources/Artefacts_reconstitues/corpus_clean.json`. Les originaux sont lus sans modification et ne sont pas inclus dans l'archive portable.

Le mode `raw` normalise les espaces, retire les caractères de contrôle, ajuste les bords du titre et reconstruit l'URL TASS depuis `link`. Le mode `clean` refuse un texte qui demanderait encore ce nettoyage, afin de ne pas altérer silencieusement les offsets. Le titre peut être vide : six articles réels sont dans ce cas, avec un corps exploitable. Aucun titre n'est inventé.

| Champ publié | Sens et invariants |
| --- | --- |
| `id` | Identifiant et type JSON originaux. La clé SQLite utilise sa représentation chaîne. |
| `date` | Nombre epoch en secondes, valeur originale. `date_readable` est explicitement UTC. |
| `title`, `text`, `url` | Titre facultatif, corps obligatoire, URL HTTPS sans identifiants. Pas de réseau dans le mode fichier ; le collecteur conserve une URL HTTPS TASS. |
| `text_sha256` | SHA-256 des octets UTF-8 du seul texte final. Ce n'est pas `content_sha256` de B2, qui porte sur un objet JSON. |
| `offset_unit` | `unicode_codepoint`. Les offsets Python/spaCy sont [start,end), relatifs à ce texte exact. |
| `provenance` | Empreinte du fichier source, index de l'article base zéro, UUID d'exécution, version de nettoyage, hash du texte brut, indication de changement. |
| `schema_version`, `source_id` | Version 1 et source TASS. La nature synthétique d'une exécution est dans le registre et les preuves. |

Le pointeur `.state/current.json` désigne une release et ses empreintes. `articles.jsonl` est le contrat B4 ; `articles.json` est un tableau accepté par la CLI B2 actuelle. Le code NER doit vérifier `text_sha256`, puis ne plus nettoyer le texte après annotation. Un changement de texte impose de recalculer annotations et inférences.

La release réelle stable `c581d2e5-eed4-4992-8bfc-18ab80cbbd86` contient 21 676 articles. SHA-256 du tableau JSON : `e1f810cae67c35ad2e57e653babba2f5b00b2013d17d98493356f9d3f7d74fdb`. Le manifeste voisin identifie aussi le JSONL. Le coordinateur a vérifié l’ingestion et la réindexation B2 des 21 676 articles, avec comparaison complète des textes déchiffrés, dates, identifiants et provenance. Les preuves sont dans 00_Pilotage/Integration_transversale/Preuves ; cette vérification reste distincte des tests locaux B3.

## Fonctionnement et reprise

`source.py` lit les tableaux JSON de façon incrémentale et les fichiers JSONL ligne par ligne. `transform.py` sélectionne uniquement les champs utiles et valide types, timestamp, texte et URL. `worker.py` traite les lots de 500 par défaut. `state.py` gère SQLite WAL avec `synchronous=FULL`.

Une transaction écrit le lot accepté, les motifs de rejet et le prochain numéro d'article à lire. Le curseur représente donc le dernier lot entièrement validé. Après SIGKILL, SQLite abandonne le lot incomplet et le nouveau processus retrouve le même run par empreinte du fichier et du contrat. Le fichier est relu jusqu'au curseur, puis seuls les articles suivants sont retraités. Cette reprise évite perte et doublon, mais la relecture initiale reste proportionnelle à la position.

`publish.py` n'active la release qu'après contrôle global : au moins un article accepté et taux de rejet inférieur ou égal au seuil configuré. Le seuil local de 0,5 % accepte les 66 textes vides du brut (environ 0,304 %) ; il est un choix documenté, pas un seuil d'école. Un lot invalide reste dans le staging et ne remplace pas la dernière release valide. Les IDs conflictuels avec textes différents sont rejetés ; une répétition exacte d'ID ou de texte conserve la première occurrence. Les quasi-doublons sémantiques ne sont pas détectés.

Deux exports complets et leurs copies locales sont préparés avant le remplacement atomique de `current.json`. `export` vérifie les hashes et utilise le miroir si le fichier principal manque ou est altéré. Cette redondance de lecture a été testée. Les copies restent sur le même Mac : elles ne protègent ni d'une perte disque ni d'une panne de l'hôte. L'écriture dépend d'une seule instance SQLite ; il n'y a pas de redondance active de l'ingestion.

## Planification, surveillance et alertes

`scheduler.py` écrit l'échéance epoch dans `schedule.json`, lance un processus enfant à l'heure prévue et détecte son code de sortie. Trois relances sont configurées, avec attente exponentielle bornée à 60 secondes. Le run reprend son curseur durable sans action manuelle. Après épuisement des tentatives, une alerte locale est émise et le superviseur sort avec un code d'erreur. La correction d'une source invalide reste une action humaine.

```sh
# Exécution périodique explicite, à arrêter par Ctrl+C.
python3 -m pipeline schedule --config config/portable.json --cycles 0 --interval 86400
# Consultation sans serveur.
python3 -m pipeline status --state .state-portable
python3 -m pipeline export --state .state-portable
```

L'état HTTP est actualisé chaque seconde. Les volumes, acceptés/rejetés, doublons, suppressions, tentatives, durée des lots, débit de traitement et fraîcheur du dernier changement sont observables. Le débit du tableau porte sur le temps des transactions ; les benchmarks portent sur le processus complet. Les deux indicateurs ne doivent pas être confondus.

Les alertes sont conservées dans `alerts.jsonl` et visibles dans le tableau : erreur du processus, rejet, qualité bloquée, lot lent ou permissions anormales. Le seuil de cinq secondes par lot est un seuil local d'exploitation à calibrer ; le test utilise volontairement zéro pour forcer le franchissement. Ajouter une métrique consiste à compléter `event()` et `snapshot()` ; une règle se place après le commit d'un lot, sans modifier la transaction.

## Droits, sécurité et incidents

Le traitement sélectionne les champs nécessaires à l'analyse de textes publics. Un article public peut contenir des personnes : la simplification « pas de données personnelles » du cours n'est pas supposée vraie pour TASS. La base légale et la nécessité du consentement doivent être qualifiées selon le plan B1 ; aucun consentement n'est inventé. La collecte n'ajoute ni profil individuel, ni coordonnées, ni données de connexion.

La configuration réelle consulte le registre B2 `.state/erasures.json` avant collecte et juste avant publication. Les IDs sont importés dans des tombstones durables B3 ; les textes correspondants sont retirés du SQLite et des exports courants/historiques B3. Si le registre est présent mais malformé, le traitement échoue. Son absence est permise pour le mode portable ; B4 doit également le consulter avant de lire un export ancien.

```sh
python3 -m pipeline access --state .state-portable b3-synthetic-001
python3 -m pipeline erase --state .state-portable b3-synthetic-001 --request-ref DEMO-DROITS-001
python3 -m pipeline check-security --state .state-portable
```

Ces commandes sont réservées à l'opérateur local, après qualification de la demande. L'accès est journalisé par l'application. L'effacement purge les releases historiques, compacte SQLite et son WAL, et interdit la réintroduction à l'import. Le mode fichier demande une source corrigée ; le collecteur dispose de collect-rectify et de son registre prioritaire. Les sources historiques hors B3, les sauvegardes externes, annotations et modèles doivent être traités dans la procédure transversale ; ces commandes seules ne prouvent pas sa complétude.

Les répertoires d'état sont en 0700 et les fichiers créés par la CLI en 0600. Les logs ne conservent pas le texte des articles ni les lignes invalides. Le tableau historique écoute sur 127.0.0.1 sans mutation ; le collecteur protège ses commandes par Host et session CSRF. Aucune clé ni API payante n'est utilisée. Les états actifs du collecteur et du pipeline historique ont été migrés vers le volume AES-256 ; les anciennes copies de travail extérieures ont leur propre politique. La migration est vérifiée avant retrait de la source et le lanceur interdit un remplacement en clair. Voir Volume_chiffre.json pour l’activation effective. Les permissions locales ne remplacent pas le chiffrement. Les ouvertures directes de fichiers par le propriétaire du Mac ne sont pas auditées par le code.

`check-security` détecte une ouverture excessive des permissions du dossier et la corrige, avec alerte locale. Un test réel de permissions 0755 reproduit ce scénario. Cette détection est un signal technique à qualifier par le responsable B1, pas la preuve d'une violation de données personnelles. La procédure B1 détermine le risque et les notifications réglementaires éventuelles ; aucun envoi automatique à des tiers n'est effectué.

## Docker et dépannage

Le Dockerfile et le Compose reprennent l’objectif de déploiement reproductible du cours. Leur construction et une exécution locale ont été vérifiées par le coordinateur. Deux défauts d’intégration ont été corrigés : UID numérique absent de /etc/passwd (identité de secours uid:<numéro>) et espace temporaire SQLite sur système de fichiers en lecture seule (tmpfs /tmp borné à 64 Mo, index run/ordre évitant le tri des payloads). La reprise a conservé le checkpoint 21 676 et publié 21 676 articles. La preuve est Preuves/Docker_B3_reprise.log. Aucun conteneur pipeline permanent n’est laissé actif. SQLite doit rester sur un stockage local, pas un partage réseau.

Avant essai Docker, créer `.state-docker` avec le propriétaire correspondant au compte non privilégié choisi, puis définir `PIPELINE_UID` et `PIPELINE_GID`. Les données source et la configuration sont montées en lecture seule ; seul `/state` est inscriptible, et le conteneur ne possède pas d'accès réseau.

```sh
mkdir -p .state-docker
PIPELINE_UID=$(id -u) PIPELINE_GID=$(id -g) docker compose up --build
# Arrêt explicite après l'essai, sans suppression des données.
docker compose stop
```

Pour une erreur, lire `alerts.jsonl`, identifier l'UUID, puis `status`. Si SQLite est occupé, laisser le retry agir ; ne pas retirer ses fichiers WAL. Une source corrompue doit être corrigée et prendra une nouvelle empreinte. Si une sortie principale manque, `export` peut retourner `mirror`. Si les deux copies sont altérées, restaurer une sauvegarde autorisée ou retraiter une source vérifiée. Aucun succès ne doit être annoncé après épuisement des retries.

## Tests, mesures et crédits

`tests/integration.py` vérifie des comportements observables avec des processus séparés et des fixtures temporaires. `scripts/benchmark.py` crée les jeux de 1 000, 10 000 et 100 000 lignes et vérifie l'équivalence brut/nettoyé. Les mesures livrées proviennent d’un poste partagé, avec d’autres services actifs et une capture navigateur en parallèle, et d’un seul passage par taille, sans garantie de débit en production. Les 100 000 lignes synthétiques ont des textes courts et répétitifs ; aucune extrapolation à 100 000 articles TASS n'est justifiée.

Le contrôle de style s'appuie sur Ruff 0.16.10, limité à des règles de syntaxe, imports et erreurs courantes, plus formatage. Le runtime, les versions et les hashes sont consignés dans `Preuves/Manifest.json`. La capture utilise agent-browser, puis ffmpeg pour convertir l'enregistrement WebM en MP4 sans modifier le contenu affiché.

Le plan et la démarche reprennent le cours Data Pipelines for AI de Matthieu Larboullet, p. 6 à 12, 17 à 21 et 25 à 30, et le livrable Books d'Edouard Cappaert du 2 juin 2026. Le code OSINT est une nouvelle adaptation préparée avec l'assistance de Codex. Les sorties Books et leurs métriques ne sont pas présentées comme des mesures OSINT. Edouard doit relire, maîtriser et personnaliser cette version avant soutenance.

Références techniques officielles consultées le 4 octobre 2026 : [transactions SQLite](https://www.sqlite.org/atomiccommit.html), [journal WAL](https://www.sqlite.org/wal.html), [écritures et remplacement atomique Python](https://docs.python.org/3/library/os.html). Les preuves exécutées localement font foi pour cette version, dans les limites explicitées.

Les générateurs de documents et de capture sont des outils de préparation facultatifs. `build_plan.py` requiert ReportLab et les preuves associées ; la capture requiert agent-browser et ffmpeg. Ces outils ne sont pas nécessaires pour exécuter le pipeline et ses tests.
