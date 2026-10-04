# Architecture commune du mémoire OSINT

Version 1.1 du 4 octobre 2026. L’Observatoire B3 collecte par rubrique et dates UTC, publie un export figé puis importe dans B2. Le raccordement testé conserve 21 676 articles initiaux et ajoute 5 articles, soit 21 681 articles. Voir [la cartographie des copies et la reprise](docs/Collecte_stockages_securite.md).

Bloc 2, version locale du 4 octobre 2026. Plateforme pour la veille OSINT. Elle stocke le corpus TASS enrichi, relie la collecte B3 et la restitution B4 et distingue systématiquement les données réelles des essais synthétiques.

## Livrables

1. `Plan_infrastructure_OSINT.pdf` : cahier des charges, schémas, architecture, Compose, preuves et utilisation.
2. `docker-compose.yml`, `app/`, `sql/`, `mongo/`, `scripts/`, `tests/` : code exécutable.
3. `Preuves/` : résultats des contrôles, mesures, captures et manifeste des versions.
4. `Demonstration_locale_OSINT.mp4` : enregistrement du fonctionnement local, avec une panne simulée. Ce fichier ne prouve pas un hébergement de production externe.
5. `Demonstration_raccordement_Observatoire.mp4` : import réel depuis le suivi B3, état final des stockages et limites. Journal : `Preuves/Raccordement_Observatoire.json`.
6. `Correspondance_criteres_Bloc2.csv` et `Preparation_orale_Bloc2.md` : correspondance des 28 critères et trame de cinq minutes.

## Stockages et autorité

PostgreSQL fait autorité pour les identifiants, sources, dates, empreintes, exécutions et suppressions. MongoDB conserve les documents chiffrés, avec un identifiant partagé et un validateur JSON. Une écriture MongoDB précède la transaction SQL et le point de reprise ; un lot interrompu se rejoue par remplacement et upsert. Une divergence doit être réconciliée avant indexation. Il n’existe pas de transaction distribuée entre les deux moteurs.

Elasticsearch est un index dérivé, reconstructible depuis les identifiants SQL validés et les documents MongoDB. À ce stade il contient dates, identifiants, empreintes et texte chiffré. L’index NER B4 distinct conserve 39 511 mentions sur le corpus initial. Les cinq articles ajoutés ne sont pas analysés dans la recette du raccordement. Les volumes techniques ne prouvent pas la qualité des prédictions.

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

La vidéo assemble deux captures réelles : le passage en lecture dégradée, puis un plan de l’article après rétablissement. Elle est muette et comporte une coupe ; elle ne représente pas une mesure chronométrée de basculement. Les temps de la vidéo et du journal d’actions ne sont pas interchangeables.

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

La sauvegarde prend un verrou partagé avec l’ingestion. Les mutations administratives directes doivent être suspendues pendant cette fenêtre. Elle contient les deux bases, leurs révisions et les registres de suppressions et de rectifications, chiffrés par AES-256-GCM. La restauration de contrôle cible uniquement `osint_restore_test`, réapplique aussi les suppressions plus récentes et vérifie les comptes. Elle ne remplace pas les bases de travail et ne rétablit pas automatiquement le service après perte de l’hôte. L’index doit être reconstruit depuis les autorités restaurées. La recette `Preuves/Collecte_TASS/restore.json` couvre les 21 681 articles et les suppressions. La recette de clôture B3 Droits_B3_B2.json vérifie aussi la réapplication d’une rectification puis d’une suppression après restauration, sur un identifiant de test isolé. SQLite B3, ses exports et checkpoints ne sont pas inclus dans la sauvegarde B2. La copie hors machine et l’automatisation quotidienne restent à mettre en place avant exploitation réelle.

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
