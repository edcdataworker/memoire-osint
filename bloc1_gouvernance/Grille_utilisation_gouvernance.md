# Grille d’utilisation et cas de gouvernance de l’Observatoire TASS

Edouard Cappaert. Bloc 1, version 1.6 du 18 octobre 2026.

Cette grille complète le plan de gouvernance sans modifier la grille d’évaluation de l’école. La cellule de veille et ses rôles sont fictifs. Les fonctions du mini-site et les tests disponibles sont réels et locaux. Autorisations, demandes de droits et incidents métier décrits ci-dessous restent des scénarios proposés, sauf preuve explicitement citée.

## Périmètre et fonctionnement

Le parcours est : besoin défini par RV, collecte par AN, consultation du catalogue et de ses versions, export ou import B2, éventuelle inférence B4 distincte, puis relecture d’une note avant diffusion. La rubrique, les dates UTC, les mots-clés et la limite définissent le job. Les mots-clés filtrent après téléchargement. Le total local, le nombre découvert, les téléchargements et les textes analysés par NER sont des populations distinctes.

Le mini-site écoute sur 127.0.0.1:18743. Il n’implémente ni comptes individuels, ni validation RV dans l’interface, ni formulaire destiné aux personnes citées. Les rôles du plan sont des responsabilités organisationnelles. Le jeton CSRF protège les commandes et ne constitue pas une authentification personnelle. L’opérateur du poste dispose des fonctions proposées par le service. Les consultations et opérations sont tracées sous le compte système du serveur. Une session partagée ne permet pas d’attribuer ces actions à chaque personne. Un volume AES-256 B3 est préparé ; son activation et la migration doivent être attestées séparément.

## Matrice de contrôle

Les références B1 renvoient à la feuille Bloc 1 du classeur RNCP38777. Les liens ci-dessous pointent vers les sources locales ; leurs versions et SHA-256 sont consignés dans [le relevé de cette mise à jour](verification/Harmonisation_bloc3.json).

| ID et situation | Responsable et règle du scénario | Action ou contrôle | Preuve et état | Écart ou limite | Critères concernés |
| --- | --- | --- | --- | --- | --- |
| U01 Lancer une collecte | RV justifie source, rubrique, dates, mots-clés et limite. DIR porte la décision de traitement. | AN saisit les paramètres dans Collecte, relève job_id et consulte le bilan de couverture. TECH vérifie restrictions et provenance. | Collecte bornée démontrée localement dans [UI_validation.json](../bloc3_pipeline/verification/Collecte_TASS/UI_validation.json). Consultation de robots.txt et bornes implémentées dans [source.py](../bloc3_pipeline/pipeline/collection/source.py). | Base légale, droit de réutilisation, revue des CGU et visa du périmètre restent à documenter. L’API interne TASS n’est pas une API contractuelle. | B1-1.1 A6, 1.2 A7, 1.3 A8, 2.2 A12, 4.3 A25. B3-6.1 A34. |
| U02 Lire un article qui cite une personne | AN vérifie la nécessité du texte et signale contenu sensible ou usage de profilage. RPD qualifie. | Lire texte et provenance dans Corpus. Limiter la finalité à la veille et isoler les contenus non pertinents avant réutilisation. | Extraction du corps et filtrage implémentés dans [source.py](../bloc3_pipeline/pipeline/collection/source.py) et [worker.py](../bloc3_pipeline/pipeline/collection/worker.py). Les payloads hors filtre ne sont pas conservés. | Pas de détection automatique des personnes ou données sensibles, ni d’anonymisation attestée. Notice et canal de droits à établir. Un texte public reste susceptible de contenir des données personnelles. | B1-1.2 A7, 2.3 A13, 2.4 A14. B3-6.1 A34, 6.3 A36. |
| U03 Exporter une sélection | AN indique motif, destinataire et échéance. RV autorise le partage selon E01. | Vérifier les filtres Corpus et le nombre réel d’articles, générer JSON/JSONL, conserver export_id et empreinte, relever toute copie sortie du périmètre. | Contrat et exports testés dans [collection.py](../bloc3_pipeline/tests/collection.py), bilan réel dans [UI_validation.json](../bloc3_pipeline/verification/Collecte_TASS/UI_validation.json). | Le visa d’export et l’inventaire des copies externes restent des procédures proposées. L’export peut dépasser la limite du dernier job. Aucune purge distante d’une copie téléchargée ailleurs. | B1-2.2 A12, 2.3 A13, 2.4 A14, 4.3 A25, 4.5 A27. |
| U04 Accorder un droit d’accès, rectification ou effacement | RV reçoit, RPD qualifie, DIR décide et TECH exécute. | Retrouver les IDs et dérivés, utiliser les commandes administratives collect-access, collect-rectify ou collect-erase après décision ; contrôler catalogue, versions, tâches, exports, secours et rejeu. Propager explicitement à B2. | Scénarios fictifs testés dans [collection.py](../bloc3_pipeline/tests/collection.py) et [closure.py](../bloc3_pipeline/tests/closure.py) : rectification, purge SQLite/WAL, recollecte et restauration. [Droits_B3_B2.json](../bloc3_pipeline/verification/Collecte_TASS/Droits_B3_B2.json) atteste une propagation B2 sur fixture, avec registre de correction chiffré. [Revisions_collecte_TASS.json](../bloc2_architecture/verification/Revisions_collecte_TASS.json) atteste le test des versions B2 et du réimport. | Granularité par article, sans moteur de recherche des droits par personne. Copies externes, sources, annotations, modèles et sauvegardes hors périmètre géré exigent une procédure coordonnée. Tests de purge logique, sans effacement physique universel ni désapprentissage. | B1-1.2 A7, 1.3 A8, 2.4 A14, 4.3 A25. B3-6.3 A36. |
| U05 Réviser un article ou conserver une ancienne version | TECH trace les révisions. RV justifie leur nécessité et leur durée. | Consulter versions et empreintes, distinguer version courante et ancienne. Une nouvelle inférence doit être identifiée si le texte change. | Versions et rejeu testés dans [collection.py](../bloc3_pipeline/tests/collection.py). Révisions B2 dans [Revisions_collecte_TASS.json](../bloc2_architecture/verification/Revisions_collecte_TASS.json). | Purge des journaux gérés implémentée au démarrage à six mois ; purge des corpus, versions et copies externes par échéance non automatisée. Les fichiers de tâches, SQLite/WAL et exports font partie de l’inventaire à contrôler. Une collecte ne déclenche pas une nouvelle inférence ni un entraînement. | B1-1.3 A8, 2.3 A13, 2.4 A14, 4.3 A25. B3-6.4 A37. |
| U06 Accès inattendu, export erroné ou panne | TECH contient et préserve les traces. DIR qualifie avec RPD selon I01, C01 et C02. | Vérifier les refus Host/CSRF, suspendre partage erroné, qualifier l’atteinte aux personnes. Reprendre un job interrompu selon son état. | Permissions, intégrité et secours de lecture testés sur fixtures dans [closure.py](../bloc3_pipeline/tests/closure.py). Deux refus 403 dans [Acces_local.json](../bloc3_pipeline/verification/Collecte_TASS/Acces_local.json). Reprise de worker dans les tests collecte. [restore.json](../bloc2_architecture/verification/Collecte_TASS/restore.json) documente une restauration B2 isolée. | Alertes et confinement testés sur fixtures, aucun incident de divulgation réel ni notification revendiqués. Le secours autorise consultation/export et bloque les mutations ; il reste sur le même Mac. Une panne ou un refus 403 n’est pas automatiquement une violation. Reprise de processus et restauration locale ne couvrent pas la perte du Mac. | B1-1.4 A9, 2.3 A13, 2.4 A14, 2.5 A15. B3-6.2 A35, 6.5 A38, selon leur portée. |
| U07 Utiliser l’interface et surveiller les changements | RV vérifie inclusion et compréhension. TECH corrige l’interface et suit TASS. RPD tient la veille juridique. | Parcours clavier, focus, lecture des états et erreurs, zoom, contrastes. Réexaminer CGU, robots.txt, schéma, finalité ou destination avant adaptation. | Tests de disposition Chrome et zoom CSS dans [UI_validation.json](../bloc3_pipeline/verification/Collecte_TASS/UI_validation.json). [Reconnexion_tests.log](../bloc3_pipeline/verification/Collecte_TASS/Reconnexion_tests.log) décrit la récupération de l’interface. | Pas d’audit RGAA complet, lecteur d’écran, zoom natif ou test avec personne concernée. Veille planifiée, sans revue périodique déjà réalisée. | B1-1.2 A7, 1.5 A10, 2.4 A14, 4.5 A27. |

## Cas A : une veille sur la rubrique défense

Besoin fictif : RV demande à AN de préparer une note sur une journée de publications de défense. La recette réelle du bloc 3 a sélectionné cinq articles du 3 octobre 2026. Elle illustre le mécanisme, sans prouver un visa métier ou une exhaustivité des archives.

1. RV documente l’intérêt de la veille, la rubrique et la période. RPD relève les questions de base légale et de réutilisation. Les données nécessaires sont les textes et métadonnées permettant de retrouver la source.
2. AN saisit le périmètre dans Collecte, relève le job et suit téléchargements, rejets, filtres et couverture. La limite porte sur les articles découverts à vérifier. Un mot-clé réduit les articles retenus sans garantir une réduction des téléchargements.
3. AN lit les articles dans Corpus, vérifie versions et provenance, puis soumet une note contextualisée. La période affichée et le nombre local ne sont pas un inventaire de tous les événements militaires.
4. RV vérifie dénominateurs, extraits et limite de source unique. Les cinq articles récents ne disposent pas d’une inférence B4 dans les preuves de cette recette. Toute nouvelle analyse et tout entraînement relèvent de décisions distinctes.

Trace à renseigner : référence du besoin, RV, date, périmètre approuvé, job_id, motif de nécessité, couverture observée et décision sur la note. Aucun champ n’est prérempli comme une validation humaine réalisée.

## Cas B : un export destiné au jury

Besoin fictif : AN veut montrer un exemple de collecte. RV privilégie une capture, des métadonnées et des extraits limités au besoin d’évaluation, sous réserve des droits applicables. La capacité technique d’exporter le corpus entier ne constitue pas une permission de le diffuser.

1. AN vérifie les filtres Corpus et le nombre sélectionné, indépendamment de la limite du dernier job.
2. RV examine destinataire, accès prévu, contenu utile, droits d’usage et échéance. Il autorise, réduit ou refuse l’export avec motif.
3. TECH relève export_id, empreinte et emplacement. Toute copie téléchargée ou envoyée ailleurs entre dans le suivi E01. L’import B2 reste un flux local distinct d’une transmission à un LLM ou d’une publication.
4. À l’échéance ou après un effacement accordé, TECH traite les copies gérées et RV fait suivre la décision aux destinataires concernés. La clôture conserve la preuve de chaque action restant dans son périmètre.

Fiche E01 à remplir : demande, auteur, filtre, volume, contenu, destinataire, motif, visa RV, date, export_id, SHA-256, copies externes, échéance et preuve de fin de vie. Le mini-site ne collecte pas actuellement ce visa.

## Cas C : une personne citée demande un effacement

Scénario fictif distinct des tests techniques : une personne identifie un article et demande son retrait de la plateforme. Le responsable examine le droit applicable et motive sa décision. Une demande ne déclenche pas automatiquement un effacement.

1. RV ouvre une référence, relève les éléments strictement nécessaires et le délai. RPD qualifie accès, rectification, opposition, limitation ou effacement. Ne demander une identité supplémentaire qu’en présence d’un doute raisonnable.
2. TECH recherche articles, anciennes versions, tâches, exports, stockages B2, index, annotations et usages du modèle. La recherche par personne reste une opération à organiser, le registre d’exclusion utilise les IDs d’articles.
3. Après accord de DIR, l’opérateur habilité suit D01. TECH utilise `collect-erase` avec ID et référence de dossier opaque, selon le mode d’emploi B3 ; `collect-access` et `collect-rectify` couvrent accès et rectification. Propager explicitement la décision à B2 et vérifier son résultat. Le registre durable bloque la recollecte et les décisions sont réappliquées avant restauration. Ces commandes n’ont pas été exécutées sur un article réel pour cette mise à jour.
4. RV contrôle les résultats et suit séparément copies téléchargées, sources, sauvegardes, annotations, fournisseurs et modèle. Une purge du catalogue ne prouve pas un effacement dans les poids. La réponse motivée intervient selon D01 et les délais applicables, sans dossier marqué clos faute de preuve.

Fiche D01 à remplir : référence, réception, droit demandé, IDs et versions, décision DIR, échéance, systèmes touchés, état par copie, exception motivée, preuve de contrôle et date de réponse. Les tests disponibles portent sur des données fictives et ne démontrent pas le traitement d’une demande réelle.

## Protection, notice et conservation à organiser

Le volume macOS AES-256 préparé couvre les états B3, journaux, exports gérés et secours après migration. Le lanceur vérifie le montage chiffré et refuse un état de remplacement en clair. Le montage chiffré du catalogue est vérifié dans les recettes actuelles. Il ne prouve ni chiffrement intégral du Mac ni protection des exports copiés ailleurs. Les traces techniques excluent textes, secrets et mots-clés libres ; elles portent le compte système. Le code et les tests correspondants sont [security.py](../bloc3_pipeline/pipeline/collection/security.py), [rights.py](../bloc3_pipeline/pipeline/collection/rights.py) et [closure.py](../bloc3_pipeline/tests/closure.py).

La notice destinée aux personnes citées doit identifier le responsable et un contact effectif, sources, finalités et bases, catégories, destinataires, transferts éventuels, durées, droits et recours CNIL. Aucun contact fictif n’est présenté comme opérationnel. Une notice sur un site général ne dispense pas automatiquement de l’information de l’article 14 ; toute exception doit être justifiée et assortie de garanties.

Pour le mémoire, le plan propose douze mois après la dernière soutenance pour corpus, versions, annotations, modèles et index, six mois glissants pour journaux, douze mois après clôture pour dossiers de droits/incidents et trente jours glissants pour sauvegardes. Ces durées sont des choix du cas, pas des délais légaux universels. RV doit revoir leur pertinence si l’Observatoire devient une veille durable. Les exports temporaires ont une échéance liée à leur usage, dans cette limite ; le calendrier de purge des corpus et copies externes reste à mettre en œuvre. La purge des journaux gérés à six mois est implémentée au démarrage, sans preuve ici d’une exécution continue ni test de seuil ancien. Les décisions actives d’exclusion/correction restent séparées, conservées aussi longtemps que nécessaire contre une réintroduction, puis réexaminées.

## Sources et portée

Plan de gouvernance V1.6, sections 3, 4.1 à 4.4, 5 et 6. Cours Data Governance & RGPD, diapositives 18 à 21, 40 à 41 et 62. Grille de certification RNCP38777, Bloc 1 A6:A27 et Bloc 3 A34:A38. Le cours Books mentionne « pas de données personnelles » p. 29 : cette simplification ne prouve pas l’absence de personnes dans TASS.

Les garanties de collecte suivent les [recommandations CNIL sur le moissonnage](https://www.cnil.fr/fr/focus-interet-legitime-collecte-par-moissonnage). La séparation téléchargement, filtrage et conservation s’appuie sur les [recommandations de minimisation et gestion des données](https://www.cnil.fr/fr/tenir-compte-de-la-protection-des-donnees-dans-la-collecte-et-la-gestion-des-donnees). Sources consultées le 4 octobre 2026.

Cette grille documente une politique et des contrôles limités. Elle ne valide pas la conformité globale ni les critères complets du bloc 3. Les critères d’oral restent à observer lors de la prestation.

## Qualification juridique et procédures V1.5

Le [dossier juridique et procédures](Dossier_juridique_et_procedures_OSINT.pdf) renseigne J01-J07 : source, bases légales T01/T02, AIPD, notice, droits, conservation, exports, incidents et accessibilité. Il distingue les analyses rédigées des autorisations et actes réels attendus.

À expliquer au jury : une base RGPD ne donne pas un droit d’usage sur TASS ; une notice écrite doit encore recevoir les coordonnées du responsable réel et être diffusée selon les conditions applicables. Le cas fictif ne crée ni signature ni conformité réelle.


## Complément de la version 1.6

Le plan principal compte dix pages. Cadre p. 2, responsabilités p. 3, qualité/sécurité p. 4, vie privée/droits/accessibilité p. 5, risques p. 6 et 7, incidents et continuité p. 8, audit/formation/veille p. 9, références p. 10. Le mode périodique du Bloc 3 ajoute une cadence et une fenêtre à faire autoriser ; sa recette automatique reste fictive. Les décisions, visas, formations et audits organisationnels restent à réaliser.


## Décisions et preuves actualisées

Le registre `Registre_decisions_et_preuves.csv` distingue décisions humaines encore ouvertes et contrôles techniques réalisés. La sauvegarde du 19 octobre réunit les bases du Bloc 2, le catalogue du Bloc 3, ses exports et le registre de droits. Sa restauration reste locale ; les décisions de droits intervenues après capture doivent être réappliquées avant toute réouverture. Trois cycles réels de collecte sont vérifiés avec quota de cinq articles. Aucun audit réglementaire indépendant, participant à une formation ou visa métier n’est inventé.
