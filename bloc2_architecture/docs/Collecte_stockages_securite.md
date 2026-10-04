# Collecte TASS, stockages et protection des copies

Version 1.2 du 4 octobre 2026. Cette fiche décrit le périmètre commun B3/B2. Les résultats cités sont des essais locaux, avec données réelles ou fixtures explicitement distinguées.

## Parcours et autorités

Navigateur local → service B3 → worker séparé → découverte et téléchargement HTTPS TASS → validation → SQLite et publication JSON/JSONL → import opérateur B2 → PostgreSQL/MongoDB → index Elasticsearch.

SQLite B3 conserve jobs, checkpoints, catalogue, versions et événements. PostgreSQL fait autorité pour les métadonnées publiées et les identifiants validés ; MongoDB conserve les textes chiffrés correspondants. Elasticsearch est dérivé. L’état d’un job de collecte et l’UUID d’une ingestion B2 sont deux identifiants différents, rapprochés par la provenance et le journal d’import. Il n’existe pas de transaction distribuée entre SQLite, SQL et MongoDB.

Le raccordement enregistré dans `Preuves/Contrat_collecte_TASS.json` vérifie cinq nouveaux articles et 21 681 articles dans chaque stockage. Les 39 511 mentions NER sont conservées dans un index B4 distinct et concernent le corpus initial. Les cinq nouveaux textes n’ont pas d’inférence dans cette recette.

## Révisions et contrat

L’identifiant TASS reste stable. Une empreinte de texte distingue les versions textuelles ; l’empreinte du JSON B2 contrôle l’intégrité du payload chiffré. Ces empreintes n’ont pas le même périmètre et ne doivent pas être interchangées.

`article_revisions` archive les métadonnées SQL antérieures, avec une clé composée `article_id, content_sha256`. `document_revisions` conserve le document chiffré précédent, avec `_id=article_id:empreinte`, `article_id` et `archived_at`. Le déchiffrement utilise l’identifiant original comme donnée authentifiée AES-GCM. Un rejeu identique ne duplique pas l’archive. Une révision de contenu n’impose pas de modifier `schema_version=1`.

Le contrat conserve identifiant, date de publication en secondes UTC, titre, URL et texte, puis ajoute provenance, version de schéma, `text_sha256` et `offset_unit=unicode_codepoint`. Une nouvelle inférence doit référencer la bonne version du texte et le modèle utilisé.

L’API B2 authentifiée `/api/articles?start=YYYY-MM-DD&end=YYYY-MM-DD` applique `published_at >= début UTC` et `published_at < lendemain UTC de fin`. Elle retourne au plus 1 000 métadonnées, sans pagination ; elle ne constitue pas un export exhaustif pour une période plus volumineuse. Les dates de publication et de téléchargement sont distinctes.

## Cartographie des copies

| Copie | Protection et accès | Reprise et effacement | État et limite |
| --- | --- | --- | --- |
| Catalogue SQLite B3, WAL, jobs et événements | Permissions restrictives ; le lanceur exige un volume chiffré. Host et session CSRF sur HTTP local. | Checkpoints durables ; exclusion avant lecture/publication ; purge des versions gérées. | Implémenté. Pas de comptes individuels ; montage chiffré à vérifier sur le poste. |
| Miroir SQLite et exports JSON/JSONL B3 | Même répertoire privé ; instantané cohérent vérifié et publication atomique. | Lecture seule si catalogue principal invalide ; restauration explicite avec réapplication des droits. | Testé sur fixtures B3 ; même hôte. Sauvegarde externe B3 non démontrée. |
| PostgreSQL et MongoDB B2 | TLS et rôles lecteur/écrivain ; textes courants et archivés AES-GCM. | Dumps des bases, y compris révisions ; purge des versions et exclusion du réimport. | Révisions, dates, chiffrement et effacement testés sur fixture. Métadonnées non entièrement chiffrées au repos. |
| Registres de suppressions et rectifications | Identifiants minimaux ; corrections B2 chiffrées avec clé séparée. | Registres à conserver et réappliquer avant exposition d’une restauration. | Rectification/effacement et restauration B3/B2 testés sur un article de test, avec réapplication des décisions actuelles. |
| Elasticsearch et index NER | Accès authentifié ; index articles reconstructible depuis SQL/Mongo. | Suppressions à propager ; reconstruire l’index après restauration. | Index courant et NER distincts ; aucune analyse des cinq nouveaux articles attestée. |
| Exports téléchargés ailleurs, sources, annotations et modèle | Protection dépendant du lieu et de l’usage ; inventaire nécessaire. | Procédure coordonnée de conservation et de droits du bloc 1. | Pas de purge distante automatique ni de désapprentissage démontré. |

Les textes SQLite/JSON sont lisibles par le processus après montage du volume. Le chiffrement B2 ne protège pas les copies B3. Les permissions ne constituent pas un chiffrement ; le jeton CSRF ne constitue pas une authentification personnelle. La capture de raccordement utilise l’état local existant sans chiffrement du volume (`encrypted_volume=false`, `encryption_required=false`). Elle démontre l’import, pas l’activation de cette protection.

## Sauvegarde et restauration

Le script B2 prend un verrou commun à l’ingestion, capture les deux bases et les registres, puis chiffre l’archive. La recette `Preuves/Collecte_TASS/restore.json` restaure 21 681 articles par moteur dans `osint_restore_test` et réapplique quatre suppressions, sans remplacer les bases actives. Le contrôle ultérieur Droits_B3_B2.json du bloc 3 vérifie une restauration depuis la sauvegarde antérieure à une correction, puis à une suppression, sur un identifiant de test. PostgreSQL et MongoDB sont vérifiés dans la base isolée. Les clés doivent être conservées séparément ; les index sont reconstruits depuis les autorités restaurées.

Pour B3, suspendre les écritures, obtenir un instantané SQLite cohérent par l’API backup, conserver les exports nécessaires, la configuration non secrète et les registres de droits, puis tester restauration et reprise. Une copie brute de la base avec WAL actif peut être incohérente. Le miroir vérifié B3, le refus des écritures en secours et la restauration explicite avec droits sont testés dans Tests_cloture_final.log et Verification_HTTP.json du bloc 3. Le montage chiffré physique reste à activer par son propriétaire. Le miroir local ne protège pas de la perte du Mac.

Après effacement, purger documents courants, révisions et exports gérés, garder l’exclusion minimale puis vérifier recollecte, réimport et restauration. Copies externes, annotations et usages du modèle restent dans la procédure transversale. Les essais utilisent un jeu de test isolé ; ils ne correspondent pas au traitement d’une demande d’une personne concernée.

Le compte Elasticsearch osint_writer reçoit le privilège maintenance uniquement sur osint-entities-v1 : la suppression par requête demande un rafraîchissement de cet index. Les résultats de suppression sont contrôlés (échec, délai dépassé ou conflit bloquent la clôture). Le compte lecteur conserve ses interdictions ; aucun privilège maintenance n’est accordé sur osint-articles-v1. Voir Permissions_ES_final.json.

## Exploitation et supervision

La collecte fonctionne sans Docker ; l’import B2 demande Docker et ses services disponibles. La migration `sql/02_revisions.sql` est additive et ne supprime pas les volumes. Le service prépare un export figé, applique la migration, ingère puis reconstruit l’index des articles. Une erreur laisse un état et un journal explicites, sans relancer automatiquement le NER.

B3 suit jobs, erreurs, rejets, débit et checkpoints. B2 suit bases, CPU, RAM, réseau et disque via Docker/Portainer. Les essais de 60 000, 600 000 et 6 millions sont synthétiques et rattachés au code mesuré ; ils ne mesurent pas la performance du parcours web et scraping complet.

Références de preuve : `Preuves/Revisions_collecte_TASS.json`, `Contrat_collecte_TASS.json`, `Integration_collecte_TASS.json`, `Collecte_TASS/backup.json`, `Collecte_TASS/restore.json` et `Raccordement_Observatoire.json`. Les copies des preuves B3 pertinentes sont regroupées dans `Preuves/Collecte_TASS/` pour la remise. La matrice conserve les critères exacts de la grille école et leurs cellules ; aucun statut ne constitue une validation du jury.
