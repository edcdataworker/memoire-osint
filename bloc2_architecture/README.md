# Architecture commune du mémoire OSINT

Version 1.4 du 18 octobre 2026. Le programme développé dans le bloc 3 (Observatoire) collecte par rubrique et dates UTC, publie un export figé puis importe dans Bloc 2. Le raccordement testé conserve 21 676 articles initiaux et ajoute 5 articles, soit 21 681 articles. Voir [la cartographie des copies et la reprise](docs/Collecte_stockages_securite.md).

Bloc 2, version locale du 4 octobre 2026. Plateforme pour la veille OSINT. Elle stocke le corpus TASS enrichi, relie la collecte du programme développé dans le bloc 3 et la restitution Bloc 4 et distingue systématiquement les données réelles des essais synthétiques.

## Livrables

1. `Plan_infrastructure_OSINT.pdf` : cahier des charges, schémas, architecture, Compose, preuves et utilisation.
2. `docker-compose.yml`, `app/`, `sql/`, `mongo/`, `scripts/`, `tests/` : code exécutable.
3. `Preuves/` : résultats des contrôles, mesures, captures et manifeste des versions.
4. `Demonstration_locale_OSINT.mp4` : enregistrement du fonctionnement local, avec une panne simulée. Ce fichier ne prouve pas un hébergement de production externe.
5. `Demonstration_raccordement_Observatoire.mp4` : import réel depuis le suivi du programme développé dans le bloc 3, état final des stockages et limites. Journal : `Preuves/Raccordement_Observatoire.json`.
6. `Correspondance_criteres_Bloc2.csv` et `Preparation_orale_Bloc2.md` : correspondance des 28 critères et trame de cinq minutes.
7. [Presentation_Bloc2_OSINT.pptx](Presentation_Bloc2_OSINT.pptx) : sept diapositives pour les cinq minutes d’oral, avec notes du présentateur et références des preuves. Le minutage est prévu et reste à vérifier pendant une répétition.

## Stockages et autorité

PostgreSQL fait autorité pour les identifiants, sources, dates, empreintes, exécutions et suppressions. MongoDB conserve les documents chiffrés, avec un identifiant partagé et un validateur JSON. Une écriture MongoDB précède la transaction SQL et le point de reprise ; un lot interrompu se rejoue par remplacement et upsert. Une divergence doit être réconciliée avant indexation. Il n’existe pas de transaction distribuée entre les deux moteurs.

Elasticsearch est un index dérivé, reconstructible depuis les identifiants SQL validés et les documents MongoDB. À ce stade il contient dates, identifiants, empreintes et texte chiffré. L’index NER Bloc 4 distinct conserve 39 511 mentions sur le corpus initial. Les cinq articles ajoutés ne sont pas analysés dans la recette du raccordement. Les volumes techniques ne prouvent pas la qualité des prédictions.

Le service HTTPS consulte SQL et MongoDB. En cas d’indisponibilité d’un de ces services, il peut lire un article depuis le dernier index Elasticsearch, avec l’état `degraded_index_snapshot`. Ce mode peut être moins frais ; il ne permet pas l’ingestion. Il ne protège pas contre une panne de Docker, de l’application ou du Mac.

## Démarrer

Prérequis : Docker Desktop démarré, Python 3, OpenSSL et au moins 10 Gio disponibles avant les essais de charge. Pour rejouer les trois tailles, prévoir une marge supérieure pour les index et les images. Ne pas arrêter d’autres projets sans accord de leur utilisateur.

Depuis ce dossier :

```sh
python3 scripts/setup.py
# Placer le corpus nettoyé dans .data/corpus_clean.json.
docker compose build app
docker compose up -d postgres mongo app
docker compose run --rm -T ops python -m osint.cli ingest --file /data/corpus_clean.json
docker compose up -d elasticsearch
# Attendre la disponibilité HTTPS du moteur avant cette initialisation.
docker compose run --rm -T ops python -m osint.cli init-index
docker compose run --rm -T ops python -m osint.cli index
docker compose up -d kibana
```

Les secrets sont générés localement dans `.secrets/`, dont le répertoire est accessible au seul utilisateur du Mac. Les fichiers montés individuellement doivent être lisibles par les utilisateurs des conteneurs. Ne pas joindre `.secrets`, `.env`, `.data`, `.state` ou `.backups` à la remise. Conserver séparément et de manière sûre les clés de déchiffrement et les sauvegardes ; perdre `data_key` empêche de relire les textes.

Les certificats sont signés par une autorité locale, pas une autorité publique. Les clients Python vérifient cette autorité et les noms des serveurs. Pour une utilisation dans un navigateur habituel, faire approuver uniquement cette autorité de démonstration, ou configurer un certificat reconnu. Les captures automatiques utilisent une exception de certificat limitée à leur navigateur de test ; les clients des bases conservent la vérification TLS.

## Consulter et administrer

| Service | Adresse locale | Compte | Secret local |
| --- | --- | --- | --- |
| Application | https://localhost:18443 | analyste | `.secrets/api_password` |
| pgAdmin | http://localhost:15050 | analyste@example.org | `.secrets/pgadmin` |
| PostgreSQL dans pgAdmin | hôte postgres, base osint | osint_reader | `.secrets/reader` |
| Mongo Express | http://localhost:18081 | analyste | `.secrets/mongo_express` |
| Portainer | https://localhost:19443 | admin | `.secrets/portainer` |
| Kibana | https://localhost:15601 | elastic pour administration locale | `.secrets/elastic` |

Activer les interfaces de cours avec `docker compose up -d pgadmin mongo-express portainer`. Elles sont liées à 127.0.0.1. pgAdmin et Mongo Express utilisent HTTP sur cette interface locale seulement. Ne pas exposer ces ports sur le réseau. Portainer possède le socket Docker et peut administrer tous les conteneurs de la machine : le réserver à l’opérateur, l’arrêter après usage et ne pas montrer d’autres projets dans les captures.

```sh
docker compose run --rm -T ops python -m osint.cli status
docker compose ps
docker stats --no-stream
```

## Contrôles et essais du cours

```sh
docker compose run --rm -T -e PYTHONPATH=/app -v "$PWD/tests:/tests:ro" ops python /tests/integration.py
python3 scripts/benchmark.py
```

Les essais créent successivement 60 000, 600 000 et 6 000 000 enregistrements synthétiques dans PostgreSQL et MongoDB. Le texte synthétique est court, répétitif avant chiffrement, et ne représente pas la distribution des articles TASS. Les contraintes, index, TLS et chiffrement applicatif restent actifs. Les données synthétiques précédentes sont supprimées avant chaque taille ; les articles réels sont conservés. Les durées et les compteurs sont mesurés, sans extrapolation vers 6 millions d’articles réels. Elasticsearch est contrôlé sur le corpus réel, pas sur ces trois tailles.

Les métriques Docker CPU, RAM, réseau et entrées/sorties sont échantillonnées ; un maximum échantillonné n’est pas le pic absolu. Les mesures proviennent d’un seul poste, sans répétition statistique ni garantie de performance en production. Un échec laisse ses journaux et ne doit pas être annoncé comme un résultat réussi.

Un essai complémentaire `.venv/bin/python scripts/verify_lifecycle.py` vérifie la reprise, la persistance et une suppression sur une fixture sans personne réelle. Il suppose le corpus chargé, l’index disponible et les essais de charge terminés. Il nettoie uniquement les données marquées synthétiques et recrée les conteneurs des deux bases en conservant leurs volumes.

Les empreintes du code utilisé pendant les mesures et du code livré sont distinguées dans `Preuves/Environnement_et_version.json`. Après les charges, le délai Mongo des opérations écrivain a été porté à 300 secondes pour permettre un nettoyage de masse ; la lecture garde 30 secondes. La présentation HTML et les montages du service lecteur ont aussi été affinés. Les tests fonctionnels portent sur la version livrée.

Pour vérifier la continuité sans enregistrement, exécuter `python3 scripts/verify_continuity.py` après le test de suppression. Ce script arrête et redémarre uniquement les bases du projet OSINT ; il conserve les volumes.

La vidéo `Demonstration_locale_OSINT.mp4`, actualisée le 5 octobre 2026, montre l’exécution réelle du programme d’administration et du service de consultation : statut initial, import de trois articles fictifs, indexation, comparaison des identifiants et empreintes dans les trois moteurs, consultation, arrêt des deux bases, lecture depuis l’index et rétablissement. Les bases et volumes de démonstration sont séparés du corpus de travail.

La vidéo est muette, avec des légendes et des coupes entre étapes. Elle conserve les durées des séquences enregistrées par captures successives de l’interface ; elle ne mesure pas la latence de basculement. La console affiche les sorties réelles des commandes Docker. Pour la capture uniquement, un relais HTTP lié à `127.0.0.1` transmet les pages du service HTTPS en vérifiant son autorité locale ; aucun secret n’est affiché. Ce relais temporaire ne fait pas partie de l’architecture livrée et ne démontre pas TLS entre navigateur et relais. Les contrôles et les empreintes de la version exécutée sont dans [le journal de la vidéo](verification/Video_execution_Bloc2.json).

## Reprise et erreurs

Chaque exécution possède un UUID, l’empreinte du fichier, le volume attendu et le dernier lot validé. Après interruption, retrouver l’UUID dans la sortie `start` ou la table `runs`, puis :

```sh
docker compose run --rm -T ops python -m osint.cli ingest --file /data/corpus_clean.json --resume UUID_EXISTANT
```

La source et le volume doivent correspondre. Un verrou empêche deux ingestions concurrentes. Une panne après l’écriture MongoDB mais avant le commit SQL peut laisser un lot supplémentaire dans MongoDB ; sa reprise remplace ce lot, sans publier d’identifiants non validés. L’indexation vérifie les empreintes communes et échoue sur une incohérence. Les erreurs opérationnelles sortent avec un code non nul et sans mots de passe dans les journaux. Inspecter les services et l’exécution concernée, puis reprendre ; ne pas supprimer les volumes pour résoudre un problème.

## Sauvegarde, restauration et droits

Installer les dépendances utilitaires dans un environnement Python local : `python3 -m venv .venv`, puis `.venv/bin/pip install -r requirements-tools.txt`.

```sh
.venv/bin/python scripts/backup_restore.py backup
.venv/bin/python scripts/backup_restore.py restore-test .backups/FICHIER.enc
```

La sauvegarde prend un verrou partagé avec l’ingestion. Les mutations administratives directes doivent être suspendues pendant cette fenêtre. Elle contient les deux bases, leurs révisions et les registres de suppressions et de rectifications, chiffrés par AES-256-GCM. La restauration de contrôle cible uniquement `osint_restore_test`, réapplique aussi les suppressions plus récentes et vérifie les comptes. Elle ne remplace pas les bases de travail et ne rétablit pas automatiquement le service après perte de l’hôte. L’index doit être reconstruit depuis les autorités restaurées. La recette `Preuves/Collecte_TASS/restore.json` couvre les 21 681 articles et les suppressions. La recette de clôture du programme développé dans le bloc 3 Droits_B3_B2.json vérifie aussi la réapplication d’une rectification puis d’une suppression après restauration, sur un identifiant de test isolé (Preuves/Collecte_TASS/Droits_B3_B2.json). SQLite du programme développé dans le bloc 3, ses exports et checkpoints ne sont pas inclus dans la sauvegarde Bloc 2. La copie hors machine et l’automatisation quotidienne restent à mettre en place avant exploitation réelle.

Les révisions sont conservées dans `article_revisions` et `document_revisions`. Un article inchangé ne crée pas d’archive supplémentaire. L’API HTTPS authentifiée `/api/articles?start=YYYY-MM-DD&end=YYYY-MM-DD` sélectionne les dates de publication inclusives UTC ; elle retourne au plus 1 000 métadonnées, sans pagination. La migration additive `sql/02_revisions.sql` s’applique sans supprimer les volumes.

Pour un droit portant sur un article identifié :

```sh
docker compose run --rm -T ops python -m osint.cli erase IDENTIFIANT
```

L’API permet l’accès au document par identifiant après authentification. La suppression enregistre un identifiant dans le registre local, puis retire le document courant et ses révisions de MongoDB et PostgreSQL, ainsi que sa copie Elasticsearch. Le registre empêche une réapparition à l’ingestion et masque le document dans le mode de lecture dégradé. Si une étape échoue, le registre reste actif et l’opération se rejoue. Les demandes réelles nécessitent identification et qualification selon le bloc 1. Le collecteur synchronise les exclusions et purge les versions et exports gérés. Les copies téléchargées hors du périmètre, les annotations et le modèle restent à traiter dans la procédure coordonnée. Les fichiers sources historiques conservés hors de cette architecture ne sont pas purgés par cette commande.

Durées et objectifs proposés par le bloc 1 : corpus et modèles jusqu’à 12 mois après soutenance, journaux 6 mois, sauvegardes 30 jours, RTO 8 heures ouvrées et RPO 24 heures. Ce sont des choix à valider, pas des obligations générales ni des garanties déjà mesurées. Le script de sauvegarde seul n’exécute pas un calendrier de purge.

## Arrêt et limites

```sh
docker compose stop pgadmin mongo-express portainer kibana
# Arrêt complet du projet en conservant les volumes :
docker compose --profile admin --profile search --profile ops down
```

Ne pas ajouter l’option de suppression des volumes sauf volonté explicite d’effacer les données de cet environnement. Les textes stockés et les sauvegardes sont chiffrés ; les métadonnées, les journaux limités et le corpus source local ne sont pas tous chiffrés au repos. FileVault était désactivé pendant l’essai. TLS n’est pas un chiffrement du disque. La gestion centralisée et la rotation des clés, le stockage chiffré, les sauvegardes hors machine et une architecture sur plusieurs hôtes doivent être préparés pour un déploiement réel.

## Sources et crédits

La structure documentaire et la démarche SQL/NoSQL reprennent le cours de Mathieu Larboullet, pages 4 à 23, et le rendu Architecture d’E. Cappaert, JC. Dorn et N. Segonds. Ces crédits concernent le travail antérieur ; ils n’attribuent pas automatiquement cette adaptation aux anciens coéquipiers. L’adaptation OSINT a été préparée avec l’assistance de Codex et doit être relue et maîtrisée par Edouard Cappaert.

Références techniques consultées le 4 octobre 2026 : [Compose et dépendances](https://docs.docker.com/compose/how-tos/startup-order/), [secrets Compose](https://docs.docker.com/reference/compose-file/secrets/), [TLS PostgreSQL](https://www.postgresql.org/docs/16/ssl-tcp.html), [TLS MongoDB](https://www.mongodb.com/docs/manual/tutorial/configure-ssl/), [HTTPS Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/security-basic-setup-https.html). Les configurations livrées et les essais datés font foi pour ce prototype.

## Correspondance avec les recommandations ANSSI

Le [rapprochement Bloc 2-3.2](docs/Correspondance_ANSSI_Bloc2.md) localise les recommandations, configurations, preuves et écarts. Le volume chiffré du programme développé dans le bloc 3 et la restauration des rectifications/effacements sont vérifiés dans les preuves jointes. La vidéo de raccordement conserve son état antérieur au chiffrement. Les métadonnées Bloc 2 et les copies externes ne bénéficient pas automatiquement de la protection du volume.

Le [rapport d’infrastructure V1.4](Plan_infrastructure_OSINT.pdf) et la [correspondance des critères](Correspondance_criteres_Bloc2.csv) accompagnent cette version du code. Les preuves publiques expurgées sont dans [verification/Finalisation_Bloc2.json](verification/Finalisation_Bloc2.json).

## Complément des consignes du 18 octobre 2026

Le plan PDF et les sept diapositives gardent leur structure. Le complément fourni précise l'architecture, le modèle de données, le code IaC, le déploiement, la surveillance et la documentation. Les critères pondérés sont : architecture 25 %, modèle 15 %, IaC 20 %, déploiement 15 %, monitoring 10 %, documentation 10 %, présentation et questions 5 %. Ces poids ne remplacent pas les 28 formulations de la grille école. La vidéo est hors périmètre de cette révision.

### Déploiement reproductible

Prérequis : Python 3, OpenSSL, Docker Desktop démarré, Docker Compose v2 avec `up --wait`, volume de données monté et espace disque disponible. Le moteur virtualisé de Docker Desktop est l'hôte local testé. Aucun serveur virtuel autonome ou cloud n'est provisionné par ces scripts.

```sh
python3 scripts/infrastructure.py deploy
```

Cette commande génère uniquement les secrets/certificats absents, valide Compose, construit l'image, démarre PostgreSQL/MongoDB/application, attend leurs healthchecks puis applique la migration additive des révisions. Un deuxième passage réutilise les volumes. `--no-build` utilise l'image locale existante. Aucun import de corpus, effacement de volume ou remplacement d'index n'est implicite. Les étapes Elasticsearch/Kibana et l'ingestion restent explicites dans le mode opératoire ci-dessus. Une erreur arrête la commande avec un code non nul et un diagnostic sans sortie brute de sous-processus. Un échec partiel n'entraîne pas un rollback des données : corriger la cause puis relancer.

`docker/compose.yaml` inclut la définition racine sans la dupliquer. Le dossier `docker/` documente les chemins de construction. Docker Compose constitue le choix IaC de ce projet ; Terraform et Kubernetes ne sont pas utilisés.

### Surveillance active locale

```sh
python3 scripts/infrastructure.py monitor --search --samples 0 --interval 30 \
  --output .state/infrastructure_monitor.jsonl
```

Arrêt par Ctrl+C. `--samples 3` permet une vérification bornée. L'intervalle est une attente après le prélèvement ; le prélèvement lui-même prend aussi du temps. La commande suit les seuls conteneurs des services attendus du projet Compose et n'affiche ni labels, ni variables d'environnement, ni commandes internes, ni secrets. PostgreSQL, MongoDB et l'application sont obligatoires ; `--search` ajoute Elasticsearch.

À chaque échantillon : état, healthcheck disponible, CPU, mémoire utilisée/limite et pourcentage, réseau et disque cumulatifs. Alertes : service absent, arrêté, non sain ou mémoire au moins égale au seuil configurable, 85 % par défaut. Ce seuil est un choix d'exploitation, pas un seuil de certification. Code 0 si tous les prélèvements sont bons ; 2 si au moins un prélèvement signale une alerte ; 1 pour un échec du déploiement ; 130 après Ctrl+C. Le fichier JSONL est ajouté sans écrasement. Prévoir sa rotation si utilisé durablement.

La surveillance reste au premier plan et n'est pas installée comme service permanent. Elle ne redémarre pas les services, n'envoie aucune notification distante et ne mesure ni la fraîcheur des données ni la qualité NER. Le healthcheck `/health` de l'application vérifie sa disponibilité HTTP, pas une lecture SQL/Mongo ; Elasticsearch sans healthcheck est contrôlé comme processus en cours. Le test d'intégration distinct vérifie les données et droits. Les compteurs réseau/disque ne sont pas des débits ni le coût isolé d'un lot.

### Modèle et preuve

L'ERD relationnel reste adapté aux écritures opérationnelles, identifiants, sources et révisions. Aucun modèle en étoile n'est implémenté : un entrepôt décisionnel introduirait des faits/dimensions et un chargement distincts, sans besoin établi pour cette consultation documentaire. MongoDB conserve le JSON variable et le texte chiffré ; l'index Elasticsearch se reconstruit depuis les autorités SQL/Mongo.

Les nouvelles preuves sont dans `Preuves/Complement_20261018/`. Les essais de 60 000, 600 000 et 6 000 000 lignes ne sont pas relancés : code d'ingestion et schémas inchangés, résultats attribués à leur version mesurée. Le redéploiement testé sur l'environnement existant ne démontre pas une installation vierge sur un deuxième poste. Les révisions publiées et leurs vérifications distantes sont consultables dans GitHub Actions.

## Provisionnement du serveur virtuel

La VM `memoire-osint-bloc2` est déployée et laissée démarrée : Ubuntu 24.04.5, 4 CPU, 8 Go de RAM et 30 Go de disque virtuel. PostgreSQL, MongoDB et l’API HTTPS sont vérifiés sur 100 documents fictifs. Un redémarrage complet conserve les données et relance les services automatiquement. Trois relevés de monitoring ne déclenchent aucune alerte. La procédure corrigée, les commandes d’arrêt et les limites sont dans [vm/README.md](vm/README.md) ; preuves dans `Preuves/VM_20261018/`. Les essais TASS et les charges de Docker Desktop restent distincts. Aucun corpus, secret existant, guide oral ou vidéo transféré dans la VM.

Les preuves du déploiement VM sont accessibles dans [verification/VM_20261018](verification/VM_20261018). Elles identifient les essais locaux, distincts de la CI GitHub.
