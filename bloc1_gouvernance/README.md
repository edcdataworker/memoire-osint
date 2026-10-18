# Bloc 1 : gouvernance du mémoire OSINT

Plan et présentation version 1.6 du 18 octobre 2026, synchronisés. La structure Eugenia reste adaptée à une cellule de veille fictive. Cette version intègre la collecte réseau et le mini-site Bloc 3, ses révisions, exports et contrôles locaux, en distinguant règles proposées et preuves techniques.

1. [Plan de gouvernance](Plan_gouvernance_OSINT.pdf) : dix pages au total, couverture et références comprises, avec visuels intégrés, avec périmètre, RACI, traitements, droits, sécurité, dix risques et continuité.
2. [Présentation modifiable](Presentation_Bloc1_OSINT.pptx) : douze diapositives et notes, budget de quinze minutes.
3. [Grille d’utilisation](Grille_utilisation_gouvernance.md) : sept parcours et trois cas guidés, collecte, export jury et demande de droits.
4. [Préparation orale](Preparation_orale_Bloc1.md) : déroulé et réponses sur le fonctionnement actuel.
5. [Correspondance des critères](Correspondance_criteres_Bloc1.csv) : les vingt-deux critères exacts de l’école, pages, preuves et limites.
6. [Source textuelle](Plan_gouvernance_OSINT.md) et Sources/contenu_plan.json : contenu modifiable du plan.

Les états du critère complet restent « Implémenté » pour les quinze critères documentaires et « Prévu » pour les sept critères d’oral. Les preuves locales ne constituent ni validation du jury, ni conformité globale. Le classeur central conserve les autres blocs et actualise seulement les éléments de preuve du Bloc 1.

## Ce que cette version apporte

T01 couvre acquisition, consultation et synthèse, tandis que T02 encadre séparément le modèle. E01 documente les exports et D01 leur effacement coordonné. Le constat daté sur le volume chiffré Bloc 3, les comptes applicatifs individuels absents, les filtres après téléchargement et les copies sorties du périmètre sont explicites. Les cinq articles collectés récemment sont distincts du corpus historique et de ses mentions NER.

Le relevé [Harmonisation_bloc3.json](verification/Harmonisation_bloc3.json) identifie sources, code et preuves par SHA-256. Les contrôles documentaires de cette version sont dans [Validation_bloc1.json](verification/Validation_bloc1.json). Les preuves antérieures restent datées ; elles ne démontrent pas une demande de droits réelle, un audit juridique ou une formation.

## Suite à réaliser

1. Renseigner les coordonnées réelles de la notice, obtenir les justificatifs de droit d’usage et faire valider les décisions proposées dans le dossier juridique.
2. Mettre en œuvre visas, suivi des copies externes, purge des corpus par échéance, contrôle du maintien du volume chiffré du Bloc 3 et sauvegarde hors poste avant les usages concernés.
3. Effectuer validation humaine des annotations, revue complète d’accessibilité et lecture par un tiers.
4. Relire, s’approprier les choix et répéter l’oral avec chronomètre.

L’adaptation a été préparée avec assistance Codex. Edouard Cappaert reste responsable de sa relecture et maîtrise. Les auteurs historiques conservent leurs crédits. La version antérieure et les aperçus sont conservés en construction privée, hors remise au jury. Le [rapport Bloc 3](../00_Pilotage/Execution_PRD_TASS.md) décrit la recette locale correspondante.

## Qualification juridique et procédures V1.5

Le [dossier juridique et procédures](Dossier_juridique_et_procedures_OSINT.pdf) renseigne J01-J07 : source, bases légales T01/T02, AIPD, notice, droits, conservation, exports, incidents et accessibilité. Il distingue les analyses rédigées des autorisations et actes réels attendus.

À expliquer au jury : une base RGPD ne donne pas un droit d’usage sur TASS ; une notice écrite doit encore recevoir les coordonnées du responsable réel et être diffusée selon les conditions applicables. Le cas fictif ne crée ni signature ni conformité réelle.

## Synchronisation du support oral

Les diapositives et notes intègrent l’activation et la migration vérifiées du volume AES-256 du Bloc 3 ainsi que les analyses et procédures J01-J07 rédigées. Autorisations, coordonnées réelles, diffusion de la notice, copies externes et revue humaine restent distinctes des documents disponibles. Douze diapositives et budget indicatif de quinze minutes conservés. Le contrôle ciblé est consigné dans [Synchronisation_presentation.json](verification/Synchronisation_presentation.json).


## Complément des consignes du 18 octobre 2026

Le livrable principal respecte 8 à 10 pages : le plan comporte exactement 10 pages, couverture, sommaire et références compris. Le PowerPoint comporte 12 diapositives principales, dans la fourchette de 10 à 15 demandée. Les notes conservent un budget indicatif de 15 minutes, sans répétition observée. Le plan conserve l’ordre : contexte, cadre, responsabilités, politiques, risques, contingence, audit et conclusion. Les résumés visuels et l’extension TASS sont intégrés aux sections concernées.

La collaboration est précisée par la revue mensuelle, les visas, les rôles et la vérification distincte des corrections. La formation de 45 minutes comporte programme, exercice et preuve attendue ; l’audit distingue périmètre, contrôle, constat, correction et clôture. Ces actions restent proposées, sans participants ni résultats inventés. Les évolutions locales des autres blocs sont rattachées à leurs preuves datées.

Le dossier juridique de huit pages reste un outil de travail séparé. Il ne prolonge pas le plan principal et n’est pas nécessaire pour en comprendre les règles. Le guide de préparation orale reste local et exclu des nouveaux paquets de remise. La révision précédente est publiée sur GitHub avec CI réussie. Les compléments du 19 octobre sont inclus dans cette publication GitHub ; aucun nouvel envoi Drive n’est effectué.

Pondérations du complément : complétude 25 %, choix stratégiques 20 %, parties prenantes 15 %, risques 15 %, présentation orale 15 %, questions 10 %. Les 22 critères exacts de la grille école restent conservés et localisés. Voir `verification/Complement_20261018/Validation.json`.


## Actualisation du 19 octobre 2026

Le registre `Registre_decisions_et_preuves.csv` sépare décisions métier attendues et contrôles techniques. Aucune attestation, formation ni décision juridique réelle n’est créée.

Publication précédente et CI : https://github.com/edcdataworker/memoire-osint/actions/runs/39174668036. Cette révision publie les compléments du 19 octobre. Leur CI est consultable dans GitHub Actions. Les guides oraux et vidéos restent exclus de cette publication.
