# Guide oral Bloc 4

Durée visée : cinq minutes de présentation, suivies de dix minutes de questions selon le directeur. La répétition réelle et le chronométrage par Edouard restent à effectuer.

## Trame proposée

1. 0:00 à 0:35. Besoin : retrouver des mentions militaires dans 21 676 articles TASS, avec source et contexte. Expliquer qu’un nombre de mentions ne démontre pas un événement.
2. 0:35 à 1:20. Chaîne : corpus B3 inchangé, préannotations locales, split par groupes, spaCy, sortie avec offsets et empreintes, index de mentions distinct dans Elasticsearch. Montrer les trois labels.
3. 1:20 à 2:05. Modèle : 240 articles train, 60 dev, six époques CPU, initialisation aléatoire. Préannotation par règles lexicales et contrôle complémentaire par IA. Le diagnostic élargi porte sur 42 textes réservés au test et 254 mentions proposées par Codex.
4. 2:05 à 3:05. Démonstration : filtrer une année, lire un top, ouvrir un article, montrer les offsets et la source. Signaler un exemple d’erreur de catégorie, tel que NATO prédit WEAPON, et expliquer pourquoi cela interdit des conclusions stratégiques automatiques.
5. 3:05 à 4:15. Exploitation : un changement de données déclenche un candidat, la promotion de production reste protégée par des contrôles de provenance et de qualité distincts du diagnostic IA. Distinguer alerte de distribution et baisse qualité. Montrer CI/CD locale, wheel, test santé et retour à la version précédente.
6. 4:15 à 5:00. Résultats et limites : débit mesuré, raccordement de cinq nouveaux articles, CI/CD locale et run GitHub sur données synthétiques. Présenter le F1 de 32,73 % sur la référence IA élargie. Expliquer les omissions, la migration des copies sur le volume chiffré et les limites de périmètre. Priorité suivante : comparer un candidat sur la même référence et tester les usages. Donner la main au jury.

## Questions probables

**Comment sont obtenues les annotations ?** Le modèle livré apprend sur des règles lexicales locales. Codex propose ensuite une référence complémentaire sur 42 articles de test. Les 24 textes ajoutés sont lus avant le calcul des nouvelles prédictions, avec des conventions de labels explicites.

**Que mesure le contrôle par IA ?** Il compare les prédictions spaCy à 254 mentions proposées par Codex, avec correspondance exacte du label et des offsets. Les scores dépendent des erreurs possibles de cette référence et ne se généralisent pas automatiquement à tout TASS.

**Quel F1 pouvez-vous défendre ?** Le F1 micro exploratoire de 32,73 % sur 42 articles et 254 mentions proposées par Codex. La précision vaut 71,05 % et le rappel 21,26 % ; 200 omissions sont comptées. Le score initial de 44,93 % sur 18 textes reste documenté séparément. Le modèle n’a pas changé : la différence de référence explique l’écart, pas une évolution du modèle.

**Pourquoi pas le transfert d’apprentissage du cours ?** La baseline de démonstration part d’un NER vierge pour obtenir un mécanisme local reproductible. La configuration et les poids le prouvent. Une comparaison avec `en_core_web_sm` doit utiliser les mêmes labels et la même référence identifiée, sans annoncer un gain non mesuré.

**Comment éviter une fuite entre train et test ?** Je regroupe même ID, URL, texte canonique ou titre, puis affecte le groupe entier. Je teste ensuite les 19 800 paires des sélections par triplets de mots. Cela empêche les doublons détectés, sans garantir que deux textes ne parlent pas d’un même événement.

**Que fait l’automatisation si le nouveau modèle est mauvais ?** Elle stocke un candidat et passe le contrôle de promotion. Le diagnostic IA n’autorise pas à lui seul une promotion de production. Le modèle précédent demeure disponible. Le mécanisme de retour arrière est testé séparément en démonstration.

**Votre service est-il en production ?** C’est une démonstration locale réellement exécutée. Les tests de build, installation, démarrage et santé ne constituent pas une preuve de fonctionnement continu dans une organisation ni dans le cloud.

**Comment traiter une suppression ?** Les frontières appliquent un registre d’exclusion. Il faut aussi purger textes, annotations, revue, index et sauvegardes selon la procédure transverse, puis traiter les modèles entraînés sur les données retirées. La commande locale ne prétend pas désapprendre un modèle.

**Qui a réalisé ce mémoire ?** Edouard Cappaert porte le mémoire et doit en maîtriser les choix. Les travaux de cours collectifs gardent leurs crédits. Les adaptations ont bénéficié d’une assistance Codex documentée.

## Revue humaine des 42 articles

Le [parcours de revue](docs/Revue_humaine_42_articles.md) permet de corriger les propositions, enregistrer les décisions sur le volume chiffré, puis calculer la qualité sur le test figé. Les prédictions sont masquées pendant la lecture. Aucun article réel n’est attesté par les tests automatiques ; la revue personnelle reste à effectuer. Démarrer le lanceur Lancer_revue_humaine.command depuis le dossier B4.
