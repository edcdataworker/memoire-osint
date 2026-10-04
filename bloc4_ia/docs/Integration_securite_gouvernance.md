# Intégration, sécurité et gouvernance

Mise à jour du 4 octobre 2026 : raccordement aux décisions de droits et au périmètre de protection des Blocs 1, 2 et 3. Les procédures ci-dessous distinguent les contrôles logiciels existants des actions opérateur restant à réaliser sur les copies B4.

## Contrat et systèmes

Le Bloc 3 fournit un JSONL de schéma 1 avec `id`, `date` en secondes depuis epoch, `title`, `url`, `text`, `text_sha256`, `offset_unit=unicode_codepoint`. L’identifiant numérique reste intact à l’entrée, puis l’export des mentions le transforme explicitement en chaîne pour Elasticsearch. Les contrôles rejettent schema_version incompatible, texte vide, NUL, texte supérieur à 100 000 caractères, empreinte incorrecte et URL hors HTTP(S).

Les inférences conservent le texte complet et ajoutent entités, offsets, version, empreinte du modèle, statut de supervision et horodatage UTC. Les articles sans entités sont conservés. L’export bulk produit une ligne par mention dans `osint-entities-v1`. Il ne modifie pas le mapping strict `osint-articles-v1` du Bloc 2. Le fichier `config/elasticsearch-entities-mapping.json` définit la date, l’article, les positions, le texte de l’entité et les versions. Tous les tops et séries filtrent le même champ date.

La CLI prépare des fichiers et ne contacte pas de service externe. L’intégration au cluster local utilise les certificats et identifiants du Bloc 2, avec vérification TLS, rôle limité au nouvel index et aucune suppression préalable des index. Seul le responsable du Bloc 2 opère Docker et l’import réel. Les preuves d’import sont distinctes des fichiers bulk préparés.

## Sécurité proportionnée à une démonstration locale

L’interface sert les résultats en lecture sur 127.0.0.1. Elle refuse POST, les routes arbitraires, un Host distant et les URL trop longues. Les textes non fiables passent par `textContent`, les scripts viennent du même serveur et une politique CSP bloque les scripts inline, objets et frames. Les URL sources sont limitées à HTTP(S). Aucun mot de passe ne figure dans le code, les logs ou les exports. Les dépendances sont gelées dans `requirements.lock.txt` et `pip check` est exécuté.

Le serveur HTTP local n’est pas un serveur Internet durci. L’authentification repose sur la session locale et l’accès OS. Une exposition réseau nécessiterait reverse proxy TLS, authentification forte, quotas, observabilité et revue de menace. Les tests actuels vérifient les routes, l’injection HTML, les limites et le fonctionnement local, sans certification de sécurité ni audit exhaustif de vulnérabilités.

Les exécutants limitent à un processus et un thread numérique par travail. Les corpus, modèles, fichiers de revue et secrets sont exclus du Git public. FileVault est désactivé sur le Mac ; les copies B4 inventoriées ont donc été migrées vers l’image chiffrée existante. Ce contrôle ne prétend pas chiffrer tout le disque système.

### Protection des copies B4

La preuve B3 `Preuves/Collecte_TASS/Volume_chiffre.json` constate l’activation AES-256 des états B3. La migration physique B4 a ensuite été exécutée et enregistrée séparément dans `Preuves/Protection_copies_B4.json`. Le contrôle courant `hdiutil info -plist` confirme `image-encrypted=true` pour l’image montée sur `/Volumes/MemoireOSINT`. Le chiffrement des documents PostgreSQL/MongoDB B2 ne constitue pas la protection des fichiers de travail B4.

| Copie B4 | Contenu et protection actuelle | Action opérateur prévue |
| --- | --- | --- |
| `.state/data/` et jeux DocBin des runs | Textes, préannotations, manifestes et jeux train/dev/test ; état B4 migré et vérifié sur le volume chiffré. | Réapplication des droits avant préparation et entraînement ; conserver le lien vers le stockage privé. |
| `.state/inference*.jsonl`, exports bulk et exports téléchargés | Fichiers de travail migrés sur le volume chiffré ; les téléchargements indépendants restent hors inventaire. | Même protection, contrôle de version du texte et registre courant avant diffusion. |
| HTML de revue et stockage du navigateur | HTML migrés sur le volume chiffré ; copies persistantes possibles dans `localStorage` externe. | Garder les HTML dans le périmètre privé ; purger aussi les sessions de revue après un droit. Chiffrer le HTML seul ne protège pas le profil du navigateur. |
| `Artefacts_locaux/` et archives contenant jeux ou modèles | Copies de reconstruction et archives locales de remise migrées sur le volume chiffré, empreintes vérifiées. | Reconstruire les archives touchées par un droit ; ne pas réextraire une version invalidée. |
| Modèles, registres et sauvegardes | Poids, provenance et pointeurs de versions migrés sur le volume chiffré ; modèles locaux exclus de Git. | Protéger les sauvegardes, contrôler l’impact des droits sur les données d’apprentissage et suspendre un modèle affecté selon la décision B1. |
| Captures, vidéos et rapports | Captures, vidéos et rapports inventoriés migrés ; ils peuvent afficher des extraits même sans corpus joint. | Rechercher les dérivés concernés et remplacer ou retirer les exemplaires à diffuser. |

La migration B4 a été exécutée sans serveur ni ordonnanceur B4 actif : copie des fichiers vers `/Volumes/MemoireOSINT/B4/Copies`, comparaison intégrale des empreintes, retrait des fichiers d’origine puis création de liens aux chemins habituels. L’inventaire couvre l’état, les modèles et jeux, les HTML de revue, les preuves et captures, le rapport et la présentation, les copies locales du dépôt et de remise, les fichiers de construction, le corpus reconstitué partagé et l’archive globale de remise. Une copie identique du corpus dans B2 `.data` a aussi été protégée, sans modifier les bases SQL/Mongo. Les nouvelles évaluations restent directement sous le volume chiffré. Aucun mot de passe n’a été lu ou modifié.

Le dossier `Remise_organisee` entier est ensuite conservé sous `/Volumes/MemoireOSINT/Remise`, avec un lien à sa racine. Ses fichiers B4 héritent de cette protection ; l’inventaire identifie leur emplacement physique actuel et conserve la trace des destinations initiales.

Monter le volume avant de démarrer. Ne pas supprimer les liens ni recréer leurs destinations en clair : un lien dont la cible est absente fait échouer la lecture ou l’écriture. La CLI générique accepte encore un autre chemin fourni explicitement ; elle n’impose pas le chiffrement à toutes ses utilisations. Les empreintes du modèle et les lectures après migration sont vérifiées dans la preuve de clôture. Le retrait des anciennes copies ne garantit pas un effacement forensique des blocs SSD.

Les profils navigateur, téléchargements indépendants, sauvegardes système et sources originales hors de cet inventaire ne sont pas couverts par cette migration. Les outils de revue peuvent écrire dans `localStorage` ; les HTML protégés ne chiffrent pas un profil navigateur externe. Ce périmètre reste explicite plutôt que de déclarer une protection universelle.

## Suppression et conservation

### Décisions et contrôles existants

Le responsable désigné dans le Bloc 1 qualifie la demande et son périmètre avant exécution. TECH utilise une référence opaque, l’ID de l’article et les empreintes concernées ; les coordonnées du demandeur restent dans le dossier de droits, séparé des logs techniques.

L’inférence et l’export acceptent un registre d’exclusion, soit une liste d’IDs, soit `{article_ids:[...]}`. L’opérateur doit fournir le registre B2 courant à `infer` et à `export-es` : l’option est facultative dans le code, son application n’est donc pas garantie par défaut. `prepare`, `train` et `serve` ne consultent pas ce registre. Leur entrée doit être contrôlée avant usage. `erase` filtre un fichier local et écrit un journal ; cette commande seule ne purge pas l’ensemble du dossier et ne désapprend pas un modèle.

Les tests B3/B2 de rectification et d’effacement portent sur une fixture. B2 retire les mentions indexées de l’ID rectifié ou supprimé, mais ne purge pas les fichiers B4 et ne relance pas son NER. Le contrat B3/B4 reste de schéma 1. Une rectification renouvelle l’empreinte du texte ; les offsets et annotations de l’ancienne version ne doivent pas être réutilisés automatiquement.

### Accès, rectification et suppression

1. **Accès.** Rechercher les données concernées dans l’inventaire des copies : articles, annotations, prédictions, fichiers de revue et jeux d’apprentissage. Fournir les extraits pertinents et leur provenance selon D01 du Bloc 1, après protection des données de tiers. Les coordonnées ne sont pas ajoutées au corpus.
2. **Rectification.** Appliquer la décision B3 et sa propagation B2, puis obtenir un nouvel export admis. Suspendre les résultats B4 de la version invalidée. Retirer les anciennes prédictions et propositions d’annotation des copies actives ; régénérer les HTML de revue et supprimer leur état enregistré dans le navigateur. Produire une nouvelle inférence sur le texte corrigé avec le modèle autorisé, puis un export tenant compte des exclusions courantes. Comparer ID, empreinte du texte, modèle et offsets avant réindexation. Une correction de texte destiné seulement à l’inférence n’impose pas à elle seule un réentraînement.
3. **Suppression.** Appliquer B3/B2 et conserver l’exclusion minimale. Retirer l’ID et ses versions des corpus B4, jeux train/dev/test, DocBin, prédictions, exports, HTML de revue et copies navigateur. Reconstruire les archives contenant la donnée, traiter les captures et exports déjà diffusés selon la décision B1 et vérifier la disparition des mentions indexées. Arrêter puis redémarrer le serveur sur le fichier nettoyé : il charge les articles en mémoire au démarrage et ne se met pas à jour à la seule modification du fichier.
4. **Impact sur le modèle.** Vérifier par ID et empreinte si la donnée invalidée a servi à l’entraînement ou au dev du modèle, et examiner son éventuelle restitution. Consigner la décision de maintien, suspension ou remplacement du modèle selon B1. Un réentraînement, lorsqu’il est retenu, utilise les jeux admis et une nouvelle version identifiable. La CLI ne possède pas de commande d’invalidation pour droits ; la suspension du service et de l’ordonnanceur est actuellement une action opérateur. La suppression d’une simple sortie d’inférence ne modifie pas les poids.
5. **Clôture.** Consigner référence, IDs, versions, chemins traités, résultats de contrôle et copies restantes, sans texte complet ni secret dans le journal technique. Une propagation incomplète ou une sauvegarde non traitée reste explicitement suivie. La clôture est décidée par le responsable B1, pas par la seule réussite de `erase`.

### Restauration et conservation

Avant restauration B4, arrêter serveur et ordonnanceur. Restaurer dans un espace privé isolé ; vérifier les empreintes puis appliquer les décisions de suppression ET de rectification les plus récentes, conservées indépendamment de la sauvegarde. Un ancien export ne fait pas autorité sur la version courante d’un texte. Reconstituer les fichiers admis depuis B3/B2 et renouveler les prédictions dont l’empreinte est obsolète. Reconstruire les HTML et contrôler les copies navigateur avant remise en service. Une sauvegarde restaurée ne doit pas réactiver un modèle suspendu. Ce parcours B4 est une procédure documentée ; aucune nouvelle restauration ni purge complète B4 n’est démontrée par cette mise à jour.

Les durées proposées du Bloc 1 s’appliquent aussi à B4 : corpus, versions, annotations, modèles et index pendant 12 mois après la dernière soutenance ; journaux techniques pendant six mois calendaires ; dossiers de droits et incidents pendant 12 mois après clôture ; sauvegardes pendant 30 jours glissants. Ce sont des choix du scénario à réexaminer, pas des délais légaux universels. Les décisions actives de correction/exclusion sont séparées et maintenues tant que nécessaires contre une réintroduction. La purge par échéance et son contrôle sur toutes les copies B4 restent des actions opérateur à organiser ; la purge des journaux B3 ne les réalise pas.

### Preuves et périmètre de la mise à jour

1. Bloc 1 : `Plan_gouvernance_OSINT.md`, sections 4.4 et procédure D01 (décisions, conservation, dérivés et modèles).
2. Bloc 2 : `docs/Collecte_stockages_securite.md` et `app/osint/cli.py`, fonctions `rectify` et `invalidate_mentions` (versions et retrait des mentions obsolètes).
3. Bloc 3 : `Preuves/Collecte_TASS/Droits_B3_B2.json` et `Volume_chiffre.json` (droits sur fixture et chiffrement physique B3).
4. Bloc 4 : `src/osint_ner/cli.py`, `export.py`, `server.py` et `web/review_template.html` (options d’exclusion, portée de `erase`, chargement en mémoire et stockage navigateur).

Cette révision décrit le raccordement et la migration physique des copies B4 inventoriées. Elle ne change pas les poids du modèle ; le diagnostic élargi et les contrôles de lecture sont des preuves distinctes. Les procédures de droits suivent les recommandations de la [CNIL sur l’exercice des droits dans les systèmes d’IA](https://www.cnil.fr/fr/ia-respecter-lexercice-des-droits-des-personnes), consultées le 4 octobre 2026, en distinguant bases d’apprentissage, données dérivées et modèle.

## Droit et éthique

Le caractère public d’un article ne dispense pas d’analyser la base légale, la finalité, la minimisation, la conservation, les droits d’opposition ou d’effacement et les droits d’auteur. La présence de noms de personnes dans le texte implique de conserver les procédures d’accès, rectification et suppression du Bloc 1. Le NER ne vise pas l’identification de personnes. Aucune collecte de consentement générale ni anonymisation totale n’est prétendue.

La conformité RGPD et loi Informatique et Libertés reste une analyse documentée à faire valider dans le contexte réel du responsable du traitement, et non un statut obtenu par la réussite de tests logiciels. Sources officielles consultées le 4 octobre 2026 : CNIL, « Assurer que le traitement est licite, en cas de réutilisation des données » (https://www.cnil.fr/fr/assurer-que-le-traitement-est-licite-reutilisation-des-donnees), avec le plan de gouvernance OSINT du Bloc 1.

Aucune certification ISO 27001 n’est revendiquée. L’alignement avec les principes ISO 27001 est volontairement amorcé par les politiques, risques et contrôles d’accès du Bloc 1. Cet alignement reste partiel : aucune analyse complète des exigences ni audit du système de management n’a été réalisé. Le critère est donc implémenté avec cet écart explicite, et non déclaré non applicable du seul fait de l’absence de certificat.

La source unique TASS comporte un cadrage éditorial. Les nombres de mentions dépendent du volume publié, de la couverture du lexique, de la segmentation et des erreurs du modèle. Un changement de distribution n’établit pas une baisse de précision. L’absence de prédiction ne prouve aucune absence sur le terrain. L’explication se limite au passage source, à la catégorie et aux limites statistiques du NER. Aucun score de confiance calibré n’est inventé.
