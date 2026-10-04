# Observatoire TASS local

## Architecture et sources

Le service reste sur le Mac, à http://127.0.0.1:18743. GitHub conserve le code et les preuves expurgées. Le collecteur découvre les articles des rubriques publiques de [TASS](https://tass.com) via POST /userApi/categoryNewsList, puis extrait titre, date et corps HTML text-content/text-block avec les métadonnées JSON-LD NewsArticle. Cette interface du site ne constitue pas une API contractuelle. robots.txt, HTTPS, cadence minimale et nouvelles tentatives bornées sont appliqués.

SQLite conserve catalogue, versions et checkpoints. JSON tableau alimente B2, JSONL conserve le contrat B4 : ID, date, titre, texte, URL, empreinte et provenance. Filtrer les dates ne réentraîne aucun modèle. Un texte corrigé demande une nouvelle inférence ; les anciennes annotations et copies externes doivent être coordonnées séparément.

## Préparation et lancement

1. Arrêter l’Observatoire et les anciens workers/planificateurs B3.
2. Ouvrir Preparer_volume_chiffre.command. Choisir et confirmer personnellement le mot de passe dans Terminal, puis déverrouiller le volume si demandé. Ne jamais mettre ce mot de passe dans la conversation, un fichier de configuration ou GitHub.
3. La migration vers /Volumes/MemoireOSINT/B3 vérifie les empreintes de chaque fichier et les comptes avant de retirer l’ancien état. Le pointeur privé .collection-location.json désigne le volume. L’état historique .state est aussi copié, vérifié puis remplacé par un lien vers B3_historique.
4. Ouvrir Lancer_Observatoire_TASS.command. Le lanceur demande le déverrouillage et refuse un remplacement en clair lorsque le volume manque.

L’image sparse APFS AES-256 est dans le dossier personnel Application Support/MemoireOSINT. macOS gère le mot de passe. Image, états et pointeur sont exclus de GitHub. Catalogue, audits, exports gérés, droits et secours sont dans ce volume après migration. Les corpus originaux et stockages des autres blocs ont leur propre politique. Ce volume ne protège pas automatiquement toutes les copies du mémoire.

État de preuve : volume APFS AES-256 activé et migration physique vérifiée le 4 octobre 2026. Les comptes de 21 681 articles au transfert, 69 fichiers du collecteur et 19 historiques ont été contrôlés. verification/Volume_chiffre.json fait foi. Le test unitaire simule un montage ; la preuve physique est distincte. La protection concerne les états B3 migrés et ne démontre pas le chiffrement intégral du Mac. Aucun effacement physique garanti du SSD n’est revendiqué.

```sh
python3 -m pipeline collect-ui --state /Volumes/MemoireOSINT/B3 --require-encrypted --open
```

Python 3.12 et la bibliothèque standard suffisent au fonctionnement. Verrous POSIX. Les suites sur fixtures fonctionnent sous Linux ou macOS ; la préparation du volume est propre à macOS.

## Utilisation et monitoring

Choisir défense, monde, politique russe ou économie, les dates de publication UTC, éventuellement des mots-clés et une limite de candidats. Une journée inclut début et fin : le lendemain de la fin est exclu. Les mots-clés appliquent une sélection OU sur titre/texte ; ils ne réduisent pas nécessairement les téléchargements. Limite 1 à 2 000 candidats, cadence par défaut 0,7 seconde, 250 pages et trois tentatives bornées.

Suivi affiche découverts, téléchargés, validés, nouveaux, modifiés, inchangés, filtrés, supprimés, rejetés, durée, débit, tentatives et couverture. Une collecte incomplète n’est pas annoncée exhaustive. Les checkpoints sont durables. Une panne du worker déclenche une relance automatique ; une pause volontaire demande Reprendre. Le contrôle qualité précède publication. Le seuil de 20 % de rejets est un choix configurable, pas une exigence de certification.

Corpus consulte les versions et exporte les articles locaux sur les dates retenues. Un export peut contenir plus d’articles que la dernière collecte. La session CSRF est renouvelée après reconnexion ; une commande à résultat incertain n’est pas rejouée automatiquement.

Le statut donne backend, date du secours et sécurité. Le seuil de lenteur est configurable avec --slow-article-seconds 10. Pour ajouter une métrique : timer perf_counter de l’étape dans worker.py, store.emit sans texte, agrégation éventuelle dans Controller.snapshot puis libellé app.js. stage_duration montre ce mécanisme pour découverte, téléchargement et publication. Vérifier les unités et le franchissement du seuil sans modifier le contrat d’article.

## Droits, audit et conservation

Commandes réservées à l’opérateur après qualification de la demande. Utiliser une référence opaque sans coordonnées. Conserver le fichier de rectification dans le volume. La sortie de collect-access contient du texte : toute redirection doit rester privée dans le volume.

```sh
python3 -m pipeline collect-access --state /Volumes/MemoireOSINT/B3 ARTICLE_ID --request-ref DOSSIER-001
python3 -m pipeline collect-rectify --state /Volumes/MemoireOSINT/B3 ARTICLE_ID --request-ref DOSSIER-001 --changes /Volumes/MemoireOSINT/B3/correction.json --propagate-b2
python3 -m pipeline collect-erase --state /Volumes/MemoireOSINT/B3 ARTICLE_ID --request-ref DOSSIER-002 --propagate-b2
python3 -m pipeline collect-check-security --state /Volumes/MemoireOSINT/B3 --require-encrypted
```

correction.json contient uniquement titre et/ou texte. Le texte est normalisé et son empreinte renouvelée. L’ancienne version est retirée du catalogue, tâches, exports gérés et secours. Le registre prend priorité sur une recollecte. La suppression purge les mêmes périmètres, active secure_delete, checkpoint WAL et compactage SQLite sous verrou du worker. Elle interdit la réintroduction.

--propagate-b2 applique SQL/Mongo/index, retire les versions et invalide les mentions d’entités indexées pour l’ID. Un échec reste explicite et rejouable. La restauration B2 réapplique les registres actuels avant remise en service. Les copies externes, sources historiques, annotations et modèles nécessitent une procédure coordonnée. Les poids B4 restent inchangés.

Les audits de consultations, exports et droits conservent compte système, date UTC, résultat, ID et référence technique. Ils excluent texte, secrets, mots-clés libres et coordonnées. Conservation de six mois calendaires, purge au lancement puis quotidiennement hors écriture active. Les décisions nécessaires pour empêcher une réintroduction sont séparées et à réexaminer dans la gouvernance. Le compte du serveur ne distingue pas plusieurs personnes partageant une session ; les lectures directes de fichiers ne sont pas auditées.

## Continuité et incident

Une copie SQLite cohérente, contrôlée et identifiée par SHA-256 est créée après import initial et publication, puis synchronisée après un droit. En panne ou corruption du principal, consultation et export passent sur le secours vérifié. Collecte, import B2 et droits sont bloqués. Si les deux copies sont invalides, le service refuse le catalogue.

Restaurer explicitement, serveur arrêté et sans worker :

```sh
python3 -m pipeline collect-restore --state /Volumes/MemoireOSINT/B3
```

La restauration contrôle l’intégrité, réapplique d’abord les droits, compacte et renouvelle le secours. Redémarrer ensuite le lanceur. Principal et secours sont sur le même Mac et le même volume : aucune continuité d’écriture ni protection contre la perte du poste.

Lenteur, permissions et intégrité produisent des alertes locales. Les permissions sont confinées. La procédure B1 qualifie nature, risque, périmètre, mesures et décision de notification. Incident_simule.json documente l’exercice fictif. Il ne vaut pas décision juridique réelle. La notification dépend du risque pour les personnes selon les [règles CNIL](https://www.cnil.fr/fr/violations-de-donnees-personnelles-les-regles-suivre), consultées le 4 octobre 2026. Aucun envoi à un tiers n’est effectué.

## Import B2 et vérification

Préparer B2 selon son README, construire app, démarrer ses services et appliquer sql/02_revisions.sql sans supprimer les volumes. Importer dans B2 est proposé pour une collecte validée ; résultat et journal privé restent dans l’état. Secrets/certificats B2 sont gérés séparément.

```sh
python3 -m unittest discover -s tests -p collection.py
python3 -m unittest discover -s tests -p closure.py
python3 tests/integration.py
node --test tests/frontend_recovery.cjs
```

Les fixtures couvrent droits après recollecte/export/restauration, purge SQLite/WAL, secours, corruption, qualité, dates, reprise et audit. Le test de migration simulée est distinct de l’activation physique. Les 9 benchmarks utilisent 100, 1 000 et 2 000 articles de tailles variées avec trois répétitions. Les 20 extractions réseau ont une preuve séparée sans texte conservé. La vidéo actuelle montre cinq articles fictifs dans le service réel, avec pause/reprise et panne/restauration. Historique conserve les anciens rendus sans les assimiler à des preuves actuelles.

Les 33 critères sont reliés aux preuves dans Correspondance_criteres_Bloc3.json. Les huit critères oraux restent prévus jusqu’à une répétition personnelle observée. La gouvernance B1 précise la qualification juridique et les copies hors collecteur.

## Contrôles complémentaires du 4 octobre 2026

Les 18 mesures de Benchmark_chiffre.json utilisent le volume AES-256, des copies isolées et 100, 1 000 ou 2 000 articles fictifs de tailles variées. Le catalogue réel reste intact. Trois répétitions par taille pour chacun des catalogues, vide et rempli de 21 701 articles ; ordre alterné ; préparation et création des index exclues des durées ; checkpoints, export et copie du catalogue complet inclus. Catalogue rempli, médianes : 100 : 2.89 s (34.5 articles/s), 1000 : 14.29 s (70.0 articles/s), 2000 : 26.17 s (76.4 articles/s). Doubler le lot de 1 000 à 2 000 multiplie la durée par 1.83 et fait varier le débit de +9.2 %. Le volume des réponses, des exports et du secours, ainsi que les durées par étape et leur dispersion, sont conservés dans la preuve. catalog_bytes exclut un éventuel WAL ; mirror_bytes représente la copie complète publiée.

Les requêtes de sélection du prochain article et de propagation des suppressions disposent désormais des index tasks_pending et tasks_article, créés automatiquement aussi sur un catalogue existant. Les premiers essais exploratoires avant correction sont conservés dans Benchmark_chiffre_avant_index.json, avec leurs répétitions réellement achevées ; ils ne constituent pas une série complète de validation. Aucun test n’isole le surcoût du chiffrement, aucun débit réseau ni SLA n’est déduit de ces mesures sur poste partagé.

Pour reproduire les mesures, déverrouiller le volume, vérifier qu’aucune collecte n’est active et réserver assez d’espace pour une copie du catalogue, ses exports et son secours. La commande exige un état et un répertoire sur un volume chiffré macOS. Les fichiers de données temporaires restent dans ce volume et sont retirés à la fin.

```sh
python3 scripts/benchmark_encrypted.py --state /Volumes/MemoireOSINT/B3 --directory /Volumes/MemoireOSINT/Benchmark_B3
```

Procédure de cycle, état réel dans Cycle_volume_chiffre.json :

1. Arrêter le serveur par Ctrl+C après la fin de toute collecte/import et checkpoint WAL.
2. Démonter normalement le volume avec hdiutil detach /Volumes/MemoireOSINT. Ne pas forcer un volume occupé.
3. Le service HTTP devient indisponible et un lancement direct avec --require-encrypted échoue sans recréer de catalogue en clair.
4. Ouvrir Lancer_Observatoire_TASS.command et saisir personnellement le mot de passe au prompt natif Terminal. La session HTTP est renouvelée après reconnexion.
5. Vérifier statut principal, AES-256, permissions, intégrité principal/secours et comptes/empreintes des tables et exports.

Cycle complet non achevé : le démontage normal a été refusé par Docker, qui conserve des fichiers B4 ouverts. Le serveur B3 a été remis en service. Aucun démontage forcé ou arrêt des autres conteneurs n’a été effectué.
