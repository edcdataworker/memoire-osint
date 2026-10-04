# Préparation orale Bloc 3, cinq minutes

Déroulé préparé sans répétition personnelle observée. B3-5.1 à B3-5.8 restent prévus. Employer ses propres mots et chronométrer réellement une répétition.

## 0:00 à 0:40 : besoin et donnée

« Je prépare des articles TASS traçables pour la NER. Le corpus historique est complété par une collecte locale, selon rubrique et dates UTC. Je distingue corpus disponible et archives accessibles. » Montrer le schéma du PDF. Le corpus historique compte 21 676 articles ; le catalogue avant migration en compte 21 681 avec les cinq précédemment collectés. Aucun compte exhaustif des archives n’est garanti.

## 0:40 à 1:30 : architecture et contrat

« Python sépare source, qualité, catalogue, suivi et droits. SQLite gère checkpoints et versions locales. PostgreSQL et MongoDB restent les stockages B2. JSON et JSONL conservent le contrat B4. Choisir les dates ne réentraîne pas le modèle. » Montrer text_sha256 et les offsets Unicode [start,end). Un texte corrigé nécessite une nouvelle inférence et la coordination des annotations antérieures.

## 1:30 à 2:20 : qualité et reprise

« La découverte est bornée, la qualité précède publication et chaque tâche validée a un checkpoint. Une panne du worker entraîne une relance automatique ; une pause volontaire demande Reprendre. » Montrer Tests_collecte_final.log. Distinguer les tests de destruction de processus de la pause volontaire dans la vidéo. Expliquer rejet, bilan de couverture et choix du seuil.

## 2:20 à 3:25 : suivi, mesures et incident

Montrer la vidéo actuelle sur cinq articles fictifs : compteurs, pause/reprise, secours puis restauration hors serveur. Les lectures restent possibles ; les écritures sont bloquées. Après restauration, le compte reste cinq.

Lire les médianes exactes dans Benchmark_collecteur.json : 100, 1 000 et 2 000 articles, trois répétitions, tailles HTML d’environ 1/10/50 Kio. Poste partagé et baisse de débit avec le volume. Aucune extrapolation ni performance du volume chiffré mesurée. Les 20 extractions TASS réelles sont séparées dans Reseau_final.json.

## 3:25 à 4:25 : droits et sécurité

« Une correction remplace le texte normalisé et son hash, retire l’ancienne version et prévaut sur une recollecte. Une suppression purge catalogue, tâches, versions, exports gérés et secours. La restauration réapplique les décisions avant de servir les données. » Montrer Droits_B3_B2.json, sur un ID fictif : SQL/Mongo/index et restauration. Audits sans textes ni coordonnées. Un compte partagé ne distingue pas les personnes. Chiffrement AES-256 activé, migration physique et service vérifiés dans Volume_chiffre.json.

## 4:25 à 5:00 : limites et résultat

« La continuité couvre la lecture sur le même Mac, sans poursuite des écritures ni protection contre la perte du poste. Copies externes, sources historiques, annotations et modèles demandent une procédure coordonnée. Une alerte technique doit être qualifiée avant décision réglementaire. » Rappeler les résultats vérifiés et les actions personnelles. Aucune validation du jury n’est revendiquée.

## Questions probables

1. Pourquoi SQLite en plus de B2 ? Pour tâches, transactions, checkpoints et catalogue local. B2 conserve les stockages métier.
2. L’API TASS est-elle officielle ? Le point de pagination est celui des pages publiques, sans contrat de stabilité. Un changement provoque une erreur contrôlée et une adaptation.
3. Toutes les archives sont-elles récupérées ? Aucune garantie exhaustive ; le bilan expose dates, limites, erreurs et candidats effectivement vérifiés.
4. Pourquoi garder le modèle B4 ? L’inférence applique les modèles au texte figé. Un changement de domaine ou de qualité peut justifier une évaluation distincte.
5. Que devient une correction après recollecte ? Le registre prévaut. Tests du marqueur ancien dans SQLite, WAL, exports et secours. Aucun effacement physique garanti du SSD.
6. Et une suppression après restauration ? Les registres actuels sont réappliqués avant exposition ; les tests B3 et B2 vérifient l’absence de réapparition.
7. Et si le volume entier disparaît ? Le secours sur ce volume ne couvre pas cette panne. Une copie indépendante relève d’un futur périmètre d’exploitation.
8. Quand notifier la CNIL ? Le responsable qualifie violation et risque selon la procédure B1. L’exercice fictif n’envoie aucune notification.
9. Comment ajouter une métrique ? Timer d’étape, événement sans texte, éventuelle agrégation et libellé UI. stage_duration est l’exemple actuel.
10. Qu’est-ce qui prouve l’oral ? Une prestation observée : temps, compréhension, écoute, posture et usage des supports. Le code et la trame ne suffisent pas.

## Fiche de répétition personnelle

Date, durée observée et observateur : à renseigner. Clarté, choix techniques, réponses, écoute, regard/posture, respect du jury, supports et temps : à observer. Actions d’amélioration : à renseigner. Ne pas compléter fictivement cette fiche.
