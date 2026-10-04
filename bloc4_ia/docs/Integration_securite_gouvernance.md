# Intégration, sécurité et gouvernance

## Contrat et systèmes

Le Bloc 3 fournit un JSONL de schéma 1 avec `id`, `date` en secondes depuis epoch, `title`, `url`, `text`, `text_sha256`, `offset_unit=unicode_codepoint`. L’identifiant numérique reste intact à l’entrée, puis l’export des mentions le transforme explicitement en chaîne pour Elasticsearch. Les contrôles rejettent schema_version incompatible, texte vide, NUL, texte supérieur à 100 000 caractères, empreinte incorrecte et URL hors HTTP(S).

Les inférences conservent le texte complet et ajoutent entités, offsets, version, empreinte du modèle, statut de supervision et horodatage UTC. Les articles sans entités sont conservés. L’export bulk produit une ligne par mention dans `osint-entities-v1`. Il ne modifie pas le mapping strict `osint-articles-v1` du Bloc 2. Le fichier `config/elasticsearch-entities-mapping.json` définit la date, l’article, les positions, le texte de l’entité et les versions. Tous les tops et séries filtrent le même champ date.

La CLI prépare des fichiers et ne contacte pas de service externe. L’intégration au cluster local utilise les certificats et identifiants du Bloc 2, avec vérification TLS, rôle limité au nouvel index et aucune suppression préalable des index. Seul le responsable du Bloc 2 opère Docker et l’import réel. Les preuves d’import sont distinctes des fichiers bulk préparés.

## Sécurité proportionnée à une démonstration locale

L’interface sert les résultats en lecture sur 127.0.0.1. Elle refuse POST, les routes arbitraires, un Host distant et les URL trop longues. Les textes non fiables passent par `textContent`, les scripts viennent du même serveur et une politique CSP bloque les scripts inline, objets et frames. Les URL sources sont limitées à HTTP(S). Aucun mot de passe ne figure dans le code, les logs ou les exports. Les dépendances sont gelées dans `requirements.lock.txt` et `pip check` est exécuté.

Le serveur HTTP local n’est pas un serveur Internet durci. L’authentification repose sur la session locale et l’accès OS. Une exposition réseau nécessiterait reverse proxy TLS, authentification forte, quotas, observabilité et revue de menace. Les tests actuels vérifient les routes, l’injection HTML, les limites et le fonctionnement local, sans certification de sécurité ni audit exhaustif de vulnérabilités.

Les exécutants limitent à un processus et un thread numérique par travail. Les corpus, modèles, fichiers de revue et secrets sont exclus du Git public. Le disque local et les sauvegardes relèvent du dispositif du Bloc 1 et du Bloc 2. Le chiffrement intégral du disque n’est pas attesté dans ce bloc.

## Suppression et conservation

L’inférence et l’export acceptent un registre d’exclusion, soit une liste d’IDs, soit `{article_ids:[...]}`. Une nouvelle production applique toujours ce registre avant export. `erase` filtre un fichier local et écrit un journal indiquant les suites nécessaires. Cette commande seule ne purge pas l’ensemble du dossier et ne désapprend pas un modèle.

Une demande recevable impose de retirer l’article du corpus, des annotations, des données de revue, des exports et des index concernés, de bloquer les modèles affectés, puis de réentraîner sur les données admises. Les sauvegardes doivent réappliquer le registre d’exclusion après restauration, comme prévu au Bloc 2. Les données intégrées au HTML de revue et les copies dans localStorage nécessitent aussi leur régénération ou leur purge. Les procédures et durées restent reliées au plan de gouvernance du Bloc 1, avec validation humaine du responsable du traitement.

## Droit et éthique

Le caractère public d’un article ne dispense pas d’analyser la base légale, la finalité, la minimisation, la conservation, les droits d’opposition ou d’effacement et les droits d’auteur. La présence de noms de personnes dans le texte implique de conserver les procédures d’accès, rectification et suppression du Bloc 1. Le NER ne vise pas l’identification de personnes. Aucune collecte de consentement générale ni anonymisation totale n’est prétendue.

La conformité RGPD et loi Informatique et Libertés reste une analyse documentée à faire valider dans le contexte réel du responsable du traitement, et non un statut obtenu par la réussite de tests logiciels. Sources officielles consultées le 4 octobre 2026 : CNIL, « Assurer que le traitement est licite, en cas de réutilisation des données » (https://www.cnil.fr/fr/assurer-que-le-traitement-est-licite-reutilisation-des-donnees), avec le plan de gouvernance OSINT du Bloc 1.

Aucune certification ISO 27001 n’est revendiquée. L’alignement avec les principes ISO 27001 est volontairement amorcé par les politiques, risques et contrôles d’accès du Bloc 1. Cet alignement reste partiel : aucune analyse complète des exigences ni audit du système de management n’a été réalisé. Le critère est donc implémenté avec cet écart explicite, et non déclaré non applicable du seul fait de l’absence de certificat.

La source unique TASS comporte un cadrage éditorial. Les nombres de mentions dépendent du volume publié, de la couverture du lexique, de la segmentation et des erreurs du modèle. Un changement de distribution n’établit pas une baisse de précision. L’absence de prédiction ne prouve aucune absence sur le terrain. L’explication se limite au passage source, à la catégorie et aux limites statistiques du NER. Aucun score de confiance calibré n’est inventé.
