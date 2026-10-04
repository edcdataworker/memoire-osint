# Correspondance avec les recommandations ANSSI, bloc 2

Version 1.2 du 4 octobre 2026. Réponse au critère B2-3.2 (grille école, Bloc 2!A17). Le rapprochement couvre les recommandations pertinentes pour les conteneurs, les accès, les copies, la sauvegarde et l’exploitation du poste local. Il distingue les configurations relues, les essais identifiés et les actions restantes. Il ne constitue ni un audit exhaustif ANSSI, ni une certification ISO 27001. Les référentiels servent de recommandations adaptées au contexte ; aucun assujettissement réglementaire supplémentaire n’est supposé.

## Sources officielles et méthode

1. ANSSI, [fiche Docker ANSSI-FT-082](https://messervices.cyber.gouv.fr/documents-guides/docker_fiche_technique.pdf), v1.0 du 23 septembre 2020. Les numéros de pages ci-dessous sont les pages imprimées ; ajouter 1 pour l’index PDF à partir de zéro.
2. ANSSI, [Guide d’hygiène informatique](https://messervices.cyber.gouv.fr/documents-guides/guide_hygiene_informatique_anssi.pdf), janvier 2017. Pages imprimées ; le PDF ajoute deux pages de couverture.
3. ANSSI, [Sauvegarde des systèmes d’information](https://messervices.cyber.gouv.fr/documents-guides/anssi_essentiels_sauvegarde-si_v1.1.pdf), Les essentiels v1.1, décembre 2023, page unique, parties 1 et 2.

Sources consultées le 4 octobre 2026. Les formulations des objectifs sont des résumés. Les configurations sont localisées dans la version livrée ; les preuves techniques conservent leurs dates et leur portée. Aucun test de charge ou de fonctionnement n’a été rejoué pour ce rapprochement documentaire. Les autres domaines du guide d’hygiène (messagerie, Wi-Fi, parc mobile) ne sont pas évalués par cette revue ciblée. ISO 27001 reste une référence de management de la sécurité dans la gouvernance ; ses clauses n’ont pas fait l’objet d’un audit complet.

## Conteneurs Docker

| Référence | Objectif résumé | Mesure constatée | Preuve localisée | État | Écart et action |
| --- | --- | --- | --- | --- | --- |
| R1 (p. 6) | Montages sensibles | Compose sans privileged ; Portainer monte le socket Docker. | docker-compose.yml:1 | Configuration relue, protection partielle | Le profil admin est ponctuel ; le socket accorde une forte autorité sur le moteur. Ne pas présenter Portainer comme une isolation de l’hôte. |
| R2 (p. 7) | Périphériques | Aucun devices ni privileged déclaré. | docker-compose.yml:15 | Configuration relue | Aucun contrôle physique des périphériques ou du moteur Docker effectué par cette revue. |
| R3, R4, R5 (p. 7) | Réseaux | data_net interne et front_net ; pas de network_mode host ; bases sans ports publiés. | docker-compose.yml:6 | Cloisonnement partiel | Deux réseaux partagés ; pas un réseau par connexion. Configuration bridge du daemon non auditée. |
| R6 (p. 9) | Namespaces | Pas de pid, ipc ou uts partageant l’hôte déclaré. | docker-compose.yml:15 | Configuration relue | La configuration ne remplace pas une inspection des namespaces actifs. |
| R7 (p. 9) | Identités système | Aucun userns-remap explicite ; ops utilise UID 0. | docker-compose.yml:79 | Non démontré | Vérifier la configuration du moteur et étudier un remappage compatible avant exploitation. |
| R8 (p. 11) | Capabilities | Aucun cap_drop explicite dans Compose. | docker-compose.yml:15 | À approfondir | Réduire les capabilities nécessaires par service ; les rôles SQL ne limitent pas les privilèges Linux. |
| R9 (p. 12) | Cgroups | Aucun partage explicite du namespace cgroup avec l’hôte déclaré. | docker-compose.yml:15 | Configuration relue | Isolation active des cgroups non auditée dans cette revue. |
| R10 (p. 12) | Mémoire | mem_limit sur les services ; consommation observée pendant les essais. | docker-compose.yml:36 ; Preuves/stats_6000000.jsonl | Configuré et mesures disponibles | Une limite de mémoire ne garantit pas le débit ou la disponibilité. |
| R11 (p. 12) | CPU | Pas de cpus, cpu_quota ou cpu_period déclaré. | docker-compose.yml:15 | À approfondir | Définir des quotas selon la charge et vérifier les effets ; aucun quota n’est déduit du monitoring CPU. |
| R12 (p. 13) | Racine en lecture seule | app utilise read_only: true et un montage état ro. | docker-compose.yml:68 ; Preuves/application_permissions.json | Appliqué au service de lecture | Non généralisé aux bases, opérateur ou interfaces d’administration. |
| R13 (p. 14) | Données temporaires | app utilise tmpfs /tmp. | docker-compose.yml:69 | Configuré pour app | Ne prouve pas la maîtrise des fichiers temporaires de tous les services. |
| R14 (p. 14) | Volumes persistants | pg_data, mongo_data et es_data sont des volumes dédiés. | docker-compose.yml:167 ; Preuves/lifecycle.json | Persistance testée, couverture partielle | Aucun quota disque explicite ; un volume ne remplace pas une sauvegarde. |
| R15 (p. 14) | Fichiers et secrets | Montages ro ; app sans secret écrivain ni corpus source ; registres en lecture seule. | docker-compose.yml:60 ; Preuves/application_permissions.json | Restrictions du lecteur testées | Ops et administration restent puissants ; fichiers secrets privés sans coffre central ni rotation. |
| R16 (p. 15) | Export des journaux | Logs locaux des opérations ; docker stats et Portainer. | docker-compose.yml:154 ; Preuves/ingestion_corpus.jsonl | Collecte locale seulement | Aucun export automatique des logs vers un autre hôte ; rétention et centralisation à organiser. |

## Hygiène et exploitation

| Référence | Objectif résumé | Mesure constatée | Preuve localisée | État | Écart et action |
| --- | --- | --- | --- | --- | --- |
| 8, 9 (p. 14, 15) | Identités et droits | Rôles lecteur/écrivain et refus d’écriture ; permissions ciblées ES. | Preuves/integration.json ; Preuves/application_permissions.json ; Preuves/Collecte_TASS/Permissions_ES_final.json | Mécanismes testés, couverture partielle | Comptes de service partagés ; utilisateurs personnels et revue périodique des droits non mis en place. |
| 11, 12 (p. 17, 18) | Secrets | Génération locale et secrets exclus du dépôt. | scripts/setup.py:3 | Configuration relue | Permissions locales distinctes d’un coffre chiffré ; rotation, sauvegarde des clés et révocation à formaliser. |
| 19, 29 (p. 27, 39) | Réseau et administration | data_net interne ; interfaces sur boucle locale ; profil admin. | docker-compose.yml:175 | Configuration relue, couverture partielle | Pas de poste dédié ; pgAdmin et Mongo Express sur HTTP local, Portainer puissant. |
| 30 (p. 41) | Protection du poste nomade | Textes Mongo AES-GCM et sauvegardes chiffrées ; catalogue sur volume AES-256. | Preuves/integration.json ; Preuves/Collecte_TASS/Volume_chiffre.json | Mécanismes testés, périmètre limité | Métadonnées B2, fichiers secrets et copies externes ne sont pas intégralement protégés par ce volume. Lecture en clair possible après montage ; protection physique du Mac non auditée. |
| 34, 35 (p. 46, 47) | Versions et correctifs | Images et dépendances identifiées ; code mesuré et livré distingués. | docker-compose.yml ; Preuves/Environnement_et_version.json | Inventaire disponible | Fixer une version ne prouve pas l’application des correctifs ; veille et fins de support à formaliser. |
| 36 (p. 49, 50) | Journalisation | Logs des opérations, erreurs, checkpoints et versions des essais. | Preuves/ingestion_corpus.jsonl ; Preuves/Integration_collecte_TASS.json | Traces disponibles, couverture partielle | Rétention, source de temps et journalisation des accès à vérifier ; aucun export central distant. |
| 37 (p. 51) | Sauvegarde et restauration | Dumps B2 chiffrés ; bases isolées ; corrections et exclusions actuelles réappliquées. | scripts/backup_restore.py ; Preuves/Collecte_TASS/restore.json ; Preuves/Collecte_TASS/Droits_B3_B2.json | Essais locaux réussis | Automatisation, copie hors ligne/hors machine et exercice de sinistre complet non démontrés ; catalogue SQLite séparé du dump B2. |
| 38 (p. 52) | Contrôles périodiques | Tests droits, TLS, intégrité, reprise et lecture dégradée. | Preuves/integration.json ; Preuves/lifecycle.json ; Preuves/continuity.json | Contrôles ciblés testés | Pas d’audit externe ou de programme périodique attesté ; aucune garantie d’absence de vulnérabilité. |

## Sauvegarde : rapprochement avec Les essentiels

La partie 1 demande une politique, des données critiques identifiées et des protections des sauvegardes. Les objectifs RTO/RPO du bloc 1 et le script B2 fournissent le cadrage et les dumps chiffrés ; ils ne prouvent pas une exécution quotidienne automatisée ou un stockage indépendant. La partie 2 demande une stratégie de restauration, des essais et des copies hors ligne. `restore.json` vérifie une restauration isolée de 21 681 articles par moteur et quatre exclusions. `Droits_B3_B2.json` vérifie sur un jeu de test la réapplication d’une rectification puis d’un effacement après restauration. La copie hors ligne et le sinistre complet restent à organiser.

## Portée des preuves récentes

`Preuves/Collecte_TASS/Volume_chiffre.json` atteste l’activation physique AES-256, la migration et l’intégrité du catalogue et du miroir. Cette protection concerne l’état géré par le programme développé dans le bloc 3 ; elle ne chiffre pas les volumes Docker B2 ou les téléchargements externes. La vidéo de raccordement a été réalisée avant cette activation et conserve sa portée initiale.

`Preuves/Collecte_TASS/Droits_B3_B2.json` atteste les corrections et effacements SQL/Mongo/index, la purge des anciennes versions, le blocage du réimport et les deux restaurations. Il s’agit d’un jeu de test isolé, sans suppression d’article réel. Une restauration réussie de ce cas ne démontre pas une reprise de l’ensemble de la plateforme après perte du Mac.

## Actions d’exploitation restantes

1. Préparer une copie de sauvegarde hors machine et hors ligne, la protection des clés et une fréquence d’exécution vérifiée.
2. Réduire les privilèges système des services, étudier les namespaces utilisateur et quotas CPU/disque compatibles.
3. Formaliser comptes personnels, revue des droits, protection et rotation des secrets.
4. Compléter la protection des métadonnées B2 et des copies externes, selon leur sensibilité.
5. Organiser veille des correctifs, rétention et centralisation des logs, puis contrôler ces mesures après modification.
