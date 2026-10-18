# Politique de gouvernance des données et de conformité RGPD
Page 1 du PDF

Mémoire OSINT
Cellule de veille documentaire fictive

Edouard Cappaert · Bloc 1 · Version 1.6 · 18 octobre 2026

Ce plan encadre une cellule d’un petit organisme privé fictif établi en France. Elle produit des notes documentaires à partir d’articles TASS et de mentions militaires extraites par IA. La politique couvre acquisition, qualité, accès, conservation, droits, incidents et contrôle.

Statut : politique proposée. DIR désigne la direction du scénario, responsable des décisions de traitement. Aucune approbation réelle, désignation de DPO, formation, audit indépendant ou conformité globale n’est attestée. Les contrôles techniques locaux sont identifiés séparément.

Sommaire

| Rubrique | Page |
| --- | --- |
| 1 Contexte stratégique et 2 cadre réglementaire | 2 |
| 3 Parties prenantes et responsabilités | 3 |
| 4.1 Qualité, gouvernance de l’IA et 4.2 sécurité | 4 |
| 4.3 Vie privée et 4.4 conservation, droits, accessibilité | 5 |
| 5.1 et 5.2 Identification et évaluation des risques | 6 |
| 5.3 Traitement de chaque risque | 7 |
| 5.4 Incidents et plans de contingence | 8 |
| 6 Audit et amélioration, 7 conclusion | 9 |
| Références et traçabilité | 10 |

Lecture : les règles sont proposées ; « testé » désigne une preuve technique datée, souvent sur données fictives. Une mesure écrite ne prouve pas son exécution organisationnelle. Les visuels de responsabilités, cycle de vie et risques sont intégrés aux pages 3, 4 et 6.

Crédits : cours et modèle de politique Eugenia cités. Adaptation pour Edouard Cappaert avec assistance Codex ; relecture, maîtrise et décisions lui reviennent.

# 1 Introduction et contexte stratégique
Page 2 du PDF

1.1 Finalité et périmètre

AN, analyste, retrouve les passages ; RV, responsable de veille, contrôle la note avant diffusion. Le périmètre comprend collecte et catalogue du Bloc 3, versions et exports, SQL/MongoDB du Bloc 2, annotations, modèle et index du Bloc 4. Profilage individuel, décision automatisée sur les personnes et surveillance opérationnelle sont exclus. Toute nouvelle source, finalité ou destination impose une revue.

1.2 État vérifié et limites

Le corpus initial contient 21 676 articles nettoyés. Cinq ajouts portent les stockages à 21 681, concordance encore contrôlée le 18 octobre [P5, P9]. L’inférence initiale produit 39 511 mentions ; un raccordement distinct en ajoute neuf [P6]. Le diagnostic sur 42 articles contre des propositions IA donne F1 32,73 %, sans attestation humaine. Une collecte ne lance pas le NER. TASS reste une source unique : ses mentions ne prouvent pas les événements.

2 Références réglementaires et normatives

| Référence et portée | Mécanisme du scénario |
| --- | --- |
| RGPD, loi Informatique et Libertés [S1, S2] | Finalités et bases distinctes, registre, minimisation, information et droits (p. 5), sécurité (p. 4), incidents (p. 8). Données publiques parfois personnelles. |
| Scraping et réutilisation [S3, S17, S18] | Qualifier droits sur les textes, CGU, restrictions et base légale. Respecter les exclusions, sans contournement. Pas de licence ni d’autorisation générale déduite. |
| Règlement IA [S10] | Qualifier l’usage et les rôles avant exploitation, former aux limites et assurer un contrôle humain. Le thème militaire ne suffit pas à classer le cas à haut risque. |
| Accessibilité [S11] | Exigence du projet ; RGAA comme méthode. Assujettissement légal à examiner selon l’organisme et le service, contrôle des parcours p. 5. |
| ISO 27001:2022 et 27701:2025 [S12, S13] | Références volontaires pour risques, sécurité et vie privée. Aucun audit de clauses complet ou certificat revendiqué. |
| NIS 2 [S14] | Qualification selon activité, taille et exceptions. Aucune obligation sectorielle attribuée automatiquement à cette cellule. |

RPD, référent protection des données, conseille ; DIR décide et RV conserve le motif et la preuve. Le calendrier et les qualifications du règlement IA sont réexaminés sur les sources officielles avant tout usage nouveau, sans présumer l’applicabilité de toutes ses dispositions.

# 3 Parties prenantes et responsabilités
Page 3 du PDF

3.1 Fonctions du scénario

DIR : direction de l’organisme, représentant le responsable de traitement. Elle décide des finalités, moyens, risques acceptés et notifications. RV : responsable de veille, propriétaire métier des données et valideur des synthèses. AN : analyste, chargé de la qualité et des annotations. TECH : administration, données et modèle. RPD : référent protection des données, conseil et contrôle. Si un DPO est désigné, il exerce ses missions avec indépendance ; il ne se substitue pas à DIR et ne détermine pas les finalités [S1, art. 37-39].

Personnes citées, éditeur TASS, titulaires des droits, école et jury, hébergeur éventuel et prestataire sont les parties externes. TASS fournit la source et n’est pas un sous-traitant de la cellule. Les rôles AN/RV restent organisationnels : le mini-site local n’implémente pas de comptes individuels.

3.2 Matrice de responsabilités

| Décision ou opération | DIR | RV | AN | TECH | RPD |
| --- | --- | --- | --- | --- | --- |
| Finalités base légale et AIPD | A | R | C | C | C |
| Sources licence et périmètre de collecte | A | R | C | C | C |
| Qualité et relecture des annotations | I | A | R | C | C |
| Accès et départ d’un utilisateur | I | A | I | R | C |
| Entraînement et publication du modèle | I | A | C | R | C |
| Export import Bloc 2 et diffusion des notes | I | A | R | R | C |
| Demande de droits et effacement | A | R | C | R | C |
| Qualification et notification incident | A | R | I | R | C |
| Restauration et reprise | I | A | C | R | C |
| Audit veille et risque résiduel | A | R | C | C | R |

A : décide et rend compte. R : réalise. C : consulté. I : informé. Une seule autorité A par ligne. Deux R peuvent contribuer avec des tâches distinctes : TECH exécute l’effacement ou contient l’incident, RV coordonne et consigne la décision. Le RPD tient la veille ; RV rassemble les preuves d’audit.

3.3 Organisation du travail

RV tient le registre des décisions et réunit mensuellement DIR, TECH et RPD pendant 30 minutes. Les incidents graves déclenchent une réunion immédiate. Toute décision comporte date, objet, version, avis, responsable, échéance et preuve attendue. Un rôle peut être cumulé dans une petite équipe, mais une personne ne clôt pas seule une correction qu’elle a réalisée : RV ou un relecteur distinct la vérifie.

Au lancement, AN relève job_id et paramètres approuvés. Pour un export, AN décrit sélection et destination ; RV donne son visa ; TECH exécute l’import Bloc 2. Le visa, la liste des utilisateurs et le suivi des copies restent des procédures proposées, sans bouton d’approbation existant.

# 4 Politiques et procédures de gestion des données
Page 4 du PDF

4.1 Qualité des données et gouvernance de l’IA

Q01 : RV autorise source, rubrique, fenêtre UTC, mots-clés, cadence et limite. TECH vérifie restrictions et provenance. Le mode périodique du Bloc 3 conserve une fenêtre glissante ; quotas et reprises limitent sa couverture. Son essai sur source fictive ne prouve pas un flux TASS permanent [P9].

| Cycle de vie | Règle et preuve à conserver |
| --- | --- |
| Acquérir et préparer | ID, URL, date de publication et de collecte, job_id, paramètres, version d’extracteur et empreinte. Compter rejets, filtres et doublons. Le seuil de rejets de 20 % est un choix du projet. |
| Annoter, Q02 | AN relit au moins 50 articles, ou tout lot plus petit, couvrant trois labels et des négatifs. Tirage, auteur, date et corrections attendus. La préannotation par règles et les propositions IA ne valent pas revue humaine. |
| Évaluer, Q03 | TECH fige jeux séparés, code, configuration, graine et modèle. Vérifier positions Unicode et texte exact ; mesurer précision/rappel/F1 par label. RV motive la décision. La qualité humaine TASS reste indisponible. |
| Restituer et effacer | Filtrer articles et mentions avec le même périmètre. Garder extrait, source, dates et limites dans chaque note. D01 propage corrections et exclusions aux versions, exports et index (p. 5). |

Minimisation : titres, textes et métadonnées utiles ; pas de collecte distincte d’images, profils ou coordonnées. Les mots-clés filtrent après téléchargement. Les contenus personnels ou sensibles présents dans les articles ne sont pas automatiquement anonymisés.

4.2 Sécurité des données et prestataires

Accès : RV autorise nominativement ; TECH révoque après départ signalé, cible de 24 h. Session nominative requise avant partage. Boucle locale, Host/CSRF, permissions et volume AES-256 du Bloc 3 sont vérifiés. Les traces portent le compte système ; ni comptes applicatifs individuels ni chiffrement de tout le Mac attestés. Le Bloc 2 chiffre ses textes et sauvegardes, avec métadonnées partiellement protégées.

S01 : avant tout prestataire, RV décrit finalité et champs ; RPD examine contrat, rôles, sous-traitants, accès hors UE, conservation et entraînement du fournisseur ; DIR autorise sur justificatifs [S8, S9]. Aucun nouvel envoi de texte personnel sans garanties. Secrets hors code, rotation et copie sûre des clés à contrôler.

E01 : AN décrit sélection, nombre, destinataire, motif et échéance ; RV donne son visa ; TECH conserve export_id et empreinte. Le visa et les copies sorties du périmètre restent suivis manuellement. Code public séparé des textes, modèles privés et guides oraux locaux.

# 4.3 Confidentialité et protection de la vie privée
Page 5 du PDF

Registre initial : finalités et bases à valider

| Traitement | Base proposée, données et accès |
| --- | --- |
| T01 Collecte, veille et synthèse | Intérêt légitime art. 6(1)(f), à justifier par nécessité et mise en balance. Articles, versions, mentions ; AN/RV, TECH au besoin. |
| T02 Annotation et modèle | Intérêt légitime à apprécier séparément de T01. Textes, annotations et poids ; AN/TECH. Une collecte n’autorise pas un entraînement. Prestataire soumis à S01. |
| T03 Sécurité et traces | Intérêt légitime de sécurisation ; compte système, date et références sans texte, secret ni mots-clés libres ; TECH/RV/RPD. |
| T04 Droits et incidents | Obligations légales ; demande, coordonnées nécessaires, décision et preuve minimisées ; DIR/RV/RPD, TECH pour exécution. |

RV renseigne contact réel, sources, destinataires, transferts, durées et mesures. J02 analyse séparément T01/T02 : intérêt, nécessité, attentes, atteintes et garanties. Le consentement n’est pas automatique. Les droits d’usage TASS restent à établir. Isoler les données sensibles ou pénales tant qu’un fondement des art. 9-10 manque ; une publication par un média ne vaut pas divulgation manifeste par la personne [S1, S4, S17].

J03/J04 : analyse d’impact de précaution avant ouverture, à faire examiner et décider réellement. J05 : notice rédigée avec sources, finalités, bases, destinataires, durées, droits et recours ; identité/contact et diffusion restent à réaliser. Art. 14 : information au plus tard sous un mois, ou au premier contact/transfert si antérieur, sauf exception motivée au cas par cas [S5, S6].

4.4 Conservation, droits et accessibilité

| Données | Durée proposée et justification |
| --- | --- |
| Corpus, versions, annotations, modèles, index | 12 mois après la dernière soutenance pour reproductibilité ; revoir si veille durable. Purge coordonnée des copies. |
| Journaux / dossiers de droits et incidents | 6 mois calendaires pour diagnostic / 12 mois après clôture pour preuve minimisée. Décisions actives d’exclusion séparées tant que nécessaires. |
| Sauvegardes | 30 jours glissants pour reprise ; réappliquer les droits avant restauration. Calendrier hors journaux à mettre en œuvre. |

D01 : RV ouvre le dossier et vérifie l’identité seulement si doute raisonnable. RPD qualifie accès, rectification, opposition, limitation ou effacement ; DIR décide. TECH retrouve ID, versions et dérivés, utilise collect-access, collect-rectify ou collect-erase puis propage au Bloc 2, index, destinataires et copies. RV répond sous un mois ; prolongation motivée jusqu’à deux mois supplémentaires annoncée dans le premier mois [S15]. Contrôle et preuve conditionnent la clôture. Pas de portabilité générale sous intérêt légitime ni de désapprentissage promis.

Accessibilité : RV/TECH vérifient clavier, focus, zoom, contrastes, tableaux et alternatives textuelles. Prévoir sous-titres/transcription pour les visuels. Les tests de disposition ne valent pas audit RGAA, test avec personne concernée ou lecteur d’écran [S11]. Les durées ci-dessus sont des choix, pas des délais légaux universels [S7].

# 5 Gestion des risques liés aux données
Page 6 du PDF

5.1 Méthode de cotation

La probabilité P et l’impact I sont estimés de 1 à 4 pour ce scénario. P : peu plausible, possible, plausible avec défaut observé, fréquent. I : gêne limitée, atteinte réversible, atteinte majeure, atteinte grave aux personnes ou perte majeure. La criticité est P × I. Cotation initiale qualitative, sans fréquence mesurée.

Choix interne : scores 1 à 3, surveillance ; 4 à 7, traitement planifié ; 8 à 16, traitement prioritaire avant l’usage concerné. Une obligation légale non satisfaite bloque cet usage quel que soit le score. Aucun score résiduel n’est considéré atteint avant contrôle des mesures.

5.2 Cartographie couvrant le cycle de vie

| ID | Cause ou situation | Impact principal | P × I |
| --- | --- | --- | --- |
| R01 | Clés historiques ou copies Bloc 3 exposées | Divulgation de textes, contrôle local insuffisant | 3 × 4 = 12 |
| R02 | Scraping finalité base ou licence mal qualifiés | Collecte ou redistribution injustifiée | 3 × 4 = 12 |
| R03 | Transfert LLM ou cloud mal encadré | Réutilisation externe et perte de maîtrise des copies | 3 × 4 = 12 |
| R04 | Annotations erronées et source unique | Synthèse trompeuse, réexposition de personnes citées | 3 × 3 = 9 |
| R05 | Versions dates ou couverture mal interprétées | Extraits obsolètes, dénominateurs erronés | 3 × 3 = 9 |
| R06 | Perte des fichiers ou effacement d’index | Résultats impossibles à reproduire et indisponibilité | 3 × 3 = 9 |
| R07 | Export au mauvais destinataire ou poste partagé | Divulgation et copie hors contrôle du catalogue | 2 × 4 = 8 |
| R08 | Versions exports ou files d’attente non purgés | Conservation excessive et réapparition en recollecte | 2 × 3 = 6 |
| R09 | Interface ou support inaccessible | Exclusion d’un utilisateur ou d’un membre du jury | 2 × 3 = 6 |
| R10 | Changement TASS du droit ou de la finalité | Collecte inadaptée ou extension non évaluée | 2 × 4 = 8 |

R01, R05 et R06 s’appuient sur les défauts historiques. Bloc 3 ajoute copies locales, versions, exports et secours. L’activation du volume Bloc 3 est attestée ; les autres mesures de R01 restent à contrôler. Cotations estimées, sans incident réel affirmé. Revoir après toute évolution de source, CGU, utilisateur, corpus, modèle ou finalité [P4, P5].

Un prestataire ou une assurance ne transfère pas la responsabilité réglementaire de l’organisme. DIR peut accepter un risque résiduel compatible avec le droit, en documentant motif, durée et révision. Le référent conseille et contrôle cette décision.

# 5.3 Traitement de chaque risque
Page 7 du PDF

Les dix risques ont chacun une stratégie, un pilote, une échéance, une preuve et une cible résiduelle. Les contrôles locaux sont datés [P5, P6, P9] ; le chiffrement activé du Bloc 3 ne prouve pas la protection des copies externes. DIR arbitre, RV conserve le contrôle et RPD conseille. Aucune cible résiduelle n’est déclarée atteinte sans preuve.

| ID | Stratégie | Mesures et pilote | Échéance | Preuve et cible résiduelle |
| --- | --- | --- | --- | --- |
| R01 | Réduire | Rotation clés, Host/CSRF et permissions ; maintenir le volume AES-256 Bloc 3 et contrôler son montage et ses permissions. TECH | Avant appel ou accès distant | Preuve expurgée de rotation et tests ; cible 1 × 4 = 4 |
| R02 | Éviter puis réduire | Qualifier CGU, droits, base et périmètre ; respecter exclusions réseau. DIR/RPD | Avant nouvel usage ou diffusion | Analyse et décision motivées ; cible 1 × 4 = 4 |
| R03 | Éviter puis réduire | Suspendre envois non encadrés, vérifier S01 et transferts, minimiser le texte. RV/TECH | Avant chaque prestataire | Contrat et cartographie des accès ; cible 1 × 4 = 4 |
| R04 | Réduire | Relecture humaine stratifiée, erreurs par label, limites visibles et validation des notes. AN/RV | Avant entraînement et note | Fiche Q02 et protocole Q03 ; cible 2 × 3 = 6 |
| R05 | Réduire | Tracer job, empreintes, révisions et UTC ; vérifier couverture et nouvelle inférence si texte changé. TECH | Avant indexation validée | Rapport de tests article par article ; cible 1 × 3 = 3 |
| R06 | Réduire | Secours local de lecture testé ; sauvegarde hors poste et restauration coordonnées à organiser. TECH | Avant démonstration | Manifestes et procès-verbal de restauration ; cible 1 × 3 = 3 |
| R07 | Réduire | Visa E01, destinataire, accès poste et inventaire des copies ; comptes distincts avant partage. RV/TECH | Avant accès ou partage | Liste des accès et visa export ; cible 1 × 4 = 4 |
| R08 | Réduire | Purger versions tâches exports gérés ; registre d’exclusion, suivi copies externes et calendrier. TECH/RV | À chaque échéance et droit | Journal de purge et recherche de contrôle ; cible 1 × 3 = 3 |
| R09 | Réduire | Tester parcours, alternatives textuelles, sous-titres et corrections. RV/TECH | Avant remise et interface | Relevé des obstacles et contre-tests ; cible 1 × 3 = 3 |
| R10 | Éviter puis réduire | Veille juridique et TASS ; arrêter avant contournement et revoir nouvelle source ou finalité. DIR/RPD | Mensuel et à tout changement | Journal de veille et décision ; cible 1 × 4 = 4 |

Après vérification, RV renseigne date, résultat, preuve, cotation résiduelle observée, avis RPD et décision DIR. Les cibles ci-dessus sont des estimations, pas des scores constatés. Revue mensuelle tant qu’un risque prioritaire reste ouvert, puis trimestrielle. Toute preuve absente maintient la mesure au statut prévu.

Ordre de réalisation : sécuriser les identifiants et les flux ; qualifier usages et prestataires ; récupérer ou reconstruire les artefacts ; valider qualité et restitution ; tester continuité, droits et accessibilité. Ces dépendances relient le plan du Bloc 1 aux réalisations des Blocs 2, 3 et 4.

# 5.4 Incidents et plans de contingence
Page 8 du PDF

I01 Violation de données ou non conformité

1. Toute personne alerte immédiatement RV et TECH. RV ouvre un dossier avec heure de détection et de prise de connaissance, systèmes, faits et personnes potentiellement concernées. TECH préserve les journaux, isole les accès compromis et fait révoquer les clés sans détruire les preuves.
2. DIR, conseillé par RPD, distingue panne, violation de données et non-conformité de licence ou de finalité. Il évalue catégories, volume, conséquences et risque pour les personnes. Toutes les violations de données sont documentées, même sans notification.
3. Si la violation est susceptible d’engendrer un risque pour les droits et libertés, DIR organise la notification à la CNIL dans les meilleurs délais et, si possible, au plus tard 72 heures après en avoir pris connaissance. Une notification progressive est possible ; un retard est motivé. L’absence de risque est justifiée et enregistrée [S1, S16].
4. En cas de risque élevé, informer les personnes sans retard injustifié, sous réserve des exceptions de l’article 34. Le délai de 72 heures ne constitue pas un délai universel de communication aux personnes. Prévoir une formulation accessible et des conseils adaptés.
5. Une non-conformité sans violation déclenche suspension de l’usage, correction, information des responsables et nouvelle revue. RV clôt seulement après vérification des mesures et réexamen du risque.

C01 Panne perte ou corruption des artefacts

Hypothèses de service proposées : RTO de 8 heures ouvrées pour rétablir l’accès utile et RPO de 24 heures pour les fichiers en cours. Elles correspondent à une veille quotidienne différable et doivent être testées. Le corpus source et chaque modèle accepté font l’objet d’un archivage après validation ; les travaux actifs d’une sauvegarde quotidienne chiffrée, distincte du poste.

TECH interrompt les écritures, identifie une version saine et restaure en environnement isolé. Il vérifie empreintes, volumes, chargement du modèle, absence de données à effacer et un parcours article/extrait. RV autorise la reprise et informe les utilisateurs. Sans restauration valide, le mode dégradé consiste à consulter les sources déjà vérifiées et à suspendre les indicateurs non fiables. Exercice avant démonstration puis trimestriel, jamais déclaré réalisé sans procès-verbal.

C02 Résultat IA trompeur ou export erroné

RV retire la note ou le résultat concerné, avertit ses destinataires et consigne la correction. TECH fige la version et analyse le périmètre ; AN vérifie les annotations et erreurs. La reprise exige une évaluation et une validation de RV. Si une divulgation accompagne l’erreur, appliquer aussi I01. Un F1 seul n’autorise pas à déclarer fiables toutes les tendances.

Cas Bloc 3 : suspendre devant refus ou changement TASS, sans contournement. Reprise du worker et lecture/export sur copie saine testés ; collecte, import et droits bloqués en secours. Restauration explicite serveur arrêté, intégrité et registres appliqués avant exposition. Alertes de permissions et d’intégrité reliées à I01 ; tests fictifs de confinement, sans notification réelle. Restauration Bloc 2 isolée documentée, perte du Mac non couverte [P5].

# 6 Audit contrôle et amélioration continue
Page 9 du PDF

6.1 Programme de contrôle

| Quand et responsable | Contrôle et trace à conserver |
| --- | --- |
| Avant accès puis annuel · RV/RPD | Formation de 45 min : 10 min données publiques/droits, 10 min limites NER, 15 min note sourcée et demande de droits, 10 min correction. Adapter métier/technique, fournir support accessible. Feuille de présence, erreurs et rattrapage avant accès. Formation prévue, non réalisée. |
| À chaque lot · AN/TECH | Q01-Q03 : qualité, offsets, versions et évaluation. RV accepte ou renvoie le lot avec motif. |
| Mensuel · RV avec TECH/RPD | Accès, incidents, purges, risques ouverts et veille officielle. Ticket par écart avec responsable et date. |
| Trimestriel et avant remise · relecteur distinct | Audit : cadrage du périmètre, revue de preuves, entretiens, tests ciblés, constats, contradictoire, corrections et contre-tests. Clôture validée par DIR. |

RV organise une revue mensuelle de 30 min avec DIR, TECH et RPD : demandes, risques ouverts et décisions. AN signale les obstacles ; TECH propose les corrections ; un relecteur distinct vérifie la clôture. Chaque décision relie objet, version, avis, pilote, échéance et preuve. Collaboration, formation et audit indépendant restent prévus.

6.2 Indicateurs proposés

RV suit acceptés/téléchargés, rejets et hors filtre ; jobs avec périmètre validé/jobs lancés ; exports avec visa/exports partagés ; versions et copies purgées/copies concernées ; droits dans le délai/demandes échues ; restaurations réussies/tentatives ; obstacles d’accessibilité ouverts. Les compteurs techniques existent, les ratios d’autorisation et de droits restent à organiser. Dénominateur nul : « non applicable ».

6.3 Veille et amélioration

RPD consulte mensuellement CNIL, EUR-Lex, Légifrance, Commission, ANSSI, ISO et RGAA [S1-S18]. TECH relève les changements TASS de CGU, robots.txt et extraction. Documenter date, version, traitements touchés, action, pilote et échéance. DIR décide et RV actualise les supports. Toute nouvelle source, finalité ou destination déclenche une revue.

7 Conclusion et état de cette version

La politique encadre le cycle de vie complet, avec responsabilités, risques et procédures. Analyses juridiques et notice sont rédigées ; autorisations, identité/contact, décisions, exécution métier et revue humaine restent à établir. Contrôles techniques locaux distincts des actes de gouvernance ; aucune conformité globale ou répétition orale attestée.

Repères : OSINT : analyse de sources ouvertes. NER : extraction d’entités nommées. AIPD : analyse d’impact sur la protection des données. DPO : délégué à la protection des données. RTO : délai cible de reprise. RPO : perte de travail maximale visée.

# Références et traçabilité
Page 10 du PDF

Sources officielles : liens cliquables. S5, S6, S10-S13 et S15-S18 revérifiés le 18 octobre 2026 ; autres sources consultées le 4 octobre. Les normes ISO apportent une méthode, sans audit exhaustif des clauses.

| ID | Texte ou référence |
| --- | --- |
| S1 | RGPD : art. 5-6, 9-10, 12-22, 25, 28, 30, 32-39, 44 et suiv. |
| S2 | Loi Informatique et Libertés |
| S3 | CNIL, réutilisation de données publiées en ligne |
| S4 | CNIL, intérêt légitime |
| S5 | CNIL, analyse d’impact IA |
| S6 | CNIL, information des personnes et IA |
| S7 | CNIL, durées de conservation |
| S8 | CNIL, sous-traitance et clauses contractuelles |
| S9 | CNIL, transferts hors UE |
| S10 | Commission européenne, règlement IA |
| S11 | RGAA, champ d’application |
| S12 | ISO/IEC 27001:2022 |
| S13 | ISO/IEC 27701:2025 |
| S14 | ANSSI, qualification NIS 2 |
| S15 | CNIL, droits des personnes (chapitre III) |
| S16 | CNIL, notification des violations |
| S17 | CNIL, intérêt légitime et moissonnage |
| S18 | CNIL, protection dès la collecte |

Sources de l’école et preuves localisées

P1/P2 : grille école RNCP38777, Bloc 1 A6:A27, 22 critères ; complément fourni « BLOC 1 : DATA GOVERNANCE » : plan 8 à 10 pages, présentation 10 à 15 diapositives, oral 15 min puis questions 15 min. Cours Data Governance & RGPD : diapositives 16, 18-21, 40-42, 53-54, 58, 62 et 66. Le document qualité RNCP41993 reste distinct.

P4 : corpus et modèle reconstruits identifiés dans les manifestes du projet. P5/P8 : Bloc 3, Preuves/Collecte_TASS : Volume_chiffre.json, Droits_B3_B2.json, Incident_simule.json ; Bloc 2, Preuves/Collecte_TASS/restore.json. Tests fictifs, activation du volume et restauration isolée ont des portées distinctes.

P6 : Bloc 4, Preuves/Diagnostic_annotations_IA_42_articles.json et Raccordement_manuel_5_articles.json : propositions IA et neuf mentions supplémentaires, sans revue humaine. P7 : Grille_utilisation_gouvernance.md : sept parcours U01-U07. Dossier_juridique_et_procedures_OSINT : formulaires J01-J07 de travail, sans autorisation ni exécution réputée acquise.

P9 : révisions du 18 octobre : Bloc 2, Preuves/Complement_20261018/Validation.json et integration.json ; Bloc 3, Preuves/Complement_20261018/Flux_continu.json ; Bloc 4, Preuves_complement_20261018/Verification_livraison.json. Le présent plan est autonome ; ces traces complètent ses règles.

# Liens des références

[S1 RGPD, règlement (UE) 2016/679, notamment art. 5-6, 9-10, 12-22, 25, 28, 30, 32-39 et 44 et suivants](https://eur-lex.europa.eu/eli/reg/2016/679/oj/fra)
[S2 Loi du 6 janvier 1978 modifiée, Informatique et Libertés](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000886460)
[S3 CNIL, recommandations aux réutilisateurs de données publiées sur Internet](https://cnil.fr/sites/cnil/files/2024-06/recommandations_reutilisateurs_donnees_publiees_sur_internet.pdf)
[S4 CNIL, intérêt légitime : nécessité et mise en balance](https://www.cnil.fr/fr/les-bases-legales/interet-legitime)
[S5 CNIL, IA : réaliser une analyse d’impact si nécessaire](https://www.cnil.fr/fr/realiser-une-analyse-dimpact-si-necessaire)
[S6 CNIL, IA : informer les personnes concernées](https://www.cnil.fr/fr/ia-informer-les-personnes-concernees)
[S7 CNIL, les durées de conservation des données](https://www.cnil.fr/fr/passer-laction/les-durees-de-conservation-des-donnees)
[S8 CNIL, contrats entre responsable de traitement et sous-traitant](https://www.cnil.fr/fr/clauses-contractuelles-types-entre-responsable-de-traitement-et-sous-traitant)
[S9 CNIL, identifier et traiter les transferts hors UE](https://www.cnil.fr/fr/responsables-de-traitement-comment-identifier-et-traiter-des-transferts-de-donnees-hors-ue)
[S10 Commission européenne, AI Act, état du calendrier et des obligations](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
[S11 RGAA, référentiel et champ d’application](https://accessibilite.numerique.gouv.fr/obligations/champ-application/)
[S12 ISO/IEC 27001:2022, management de la sécurité](https://www.iso.org/standard/27001)
[S13 ISO/IEC 27701:2025, management de la vie privée](https://www.iso.org/standard/27701)
[S14 ANSSI, NIS 2, qualification des entités](https://messervices.cyber.gouv.fr/nis2)
[S15 CNIL, chapitre III du RGPD, droits des personnes](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre3)
[S16 CNIL, notifier une violation de données personnelles](https://www.cnil.fr/fr/services-en-ligne/notifier-une-violation-de-donnees-personnelles)
[S17 CNIL, intérêt légitime et collecte par moissonnage, 19 juin 2025](https://www.cnil.fr/fr/focus-interet-legitime-collecte-par-moissonnage)
[S18 CNIL, protection des données dans la collecte et la gestion, 8 avril 2024](https://www.cnil.fr/fr/tenir-compte-de-la-protection-des-donnees-dans-la-collecte-et-la-gestion-des-donnees)
