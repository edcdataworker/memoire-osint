# Guide oral Bloc 4

Durée visée : cinq minutes de présentation, suivies de dix minutes de questions selon le directeur. La répétition réelle et le chronométrage par Edouard restent à effectuer.

## Trame proposée

1. 0:00 à 0:35. Besoin : retrouver des mentions militaires dans 21 676 articles TASS, avec source et contexte. Expliquer qu’un nombre de mentions ne démontre pas un événement.
2. 0:35 à 1:20. Chaîne : corpus B3 inchangé, préannotations locales, split par groupes, spaCy, sortie avec offsets et empreintes, index de mentions distinct dans Elasticsearch. Montrer les trois labels.
3. 1:20 à 2:05. Modèle : 240 articles train, 60 dev, six époques CPU, initialisation aléatoire. La revue historique est déclarée dans le notebook, mais ses artefacts ne sont pas retrouvés. La nouvelle baseline a ses propres versions. Aucune métrique qualité actuelle n’est revendiquée.
4. 2:05 à 3:05. Démonstration : filtrer une année, lire un top, ouvrir un article, montrer les offsets et la source. Signaler un exemple d’erreur de catégorie, tel que NATO prédit WEAPON, et expliquer pourquoi cela interdit des conclusions stratégiques automatiques.
5. 3:05 à 4:15. Exploitation : un changement de données déclenche un candidat, la promotion de production refuse l’absence de référence humaine. Distinguer alerte de distribution et baisse qualité. Montrer CI/CD locale, wheel, test santé et retour à la version précédente.
6. 4:15 à 5:00. Résultats et limites : débit mesuré, intégration locale, couverture des tests. Priorité suivante : retrouver les annotations historiques ou faire documenter une nouvelle revue, élargir la référence indépendante et valider avec les utilisateurs. Donner la main au jury.

## Questions probables

**Pourquoi le rapport historique parle-t-il de Haiku alors que le notebook parle de Mistral ?** Le rapport p.4 et la configuration N06 divergent. Je conserve leurs provenances et ne réécris pas l’historique sans artefacts. La nouvelle baseline locale utilise des règles et ne prétend reproduire aucun de ces résultats.

**Une relecture humaine a-t-elle déjà eu lieu ?** N05 la déclare explicitement. Les IDs, corrections et fichiers correspondants ne sont pas disponibles dans les artefacts récupérés. Je distingue ce qui a été déclaré de ce que je peux vérifier aujourd’hui. L’interface de revue nouvelle est préparée sans attestation préremplie.

**Quel F1 pouvez-vous défendre ?** Aucun F1 du nouveau modèle tant que le jeu humain indépendant manque. Le scorer exact et ses tests synthétiques fonctionnent, mais leur réussite ne mesure pas la qualité sur TASS. Les chiffres historiques 34, 49,82 et 56,55 correspondent à des sources différentes.

**Pourquoi pas le transfert d’apprentissage du cours ?** Cette reconstruction de démonstration part d’un NER vierge pour obtenir un mécanisme local reproductible sans réutiliser des poids historiques absents. La configuration et les poids le prouvent. Une comparaison avec `en_core_web_sm` doit utiliser les mêmes labels et la même référence humaine, sans annoncer un gain non mesuré.

**Comment éviter une fuite entre train et test ?** Je regroupe même ID, URL, texte canonique ou titre, puis affecte le groupe entier. Je teste ensuite les 19 800 paires des sélections par triplets de mots. Cela empêche les doublons détectés, sans garantir que deux textes ne parlent pas d’un même événement.

**Que fait l’automatisation si le nouveau modèle est mauvais ?** Elle stocke un candidat et passe le contrôle de promotion. La baseline actuelle reste bloquée faute de référence humaine. Le modèle précédent demeure disponible. Le mécanisme de retour arrière est testé séparément en démonstration.

**Votre service est-il en production ?** C’est une démonstration locale réellement exécutée. Les tests de build, installation, démarrage et santé ne constituent pas une preuve de fonctionnement continu dans une organisation ni dans le cloud.

**Comment traiter une suppression ?** Les frontières appliquent un registre d’exclusion. Il faut aussi purger textes, annotations, revue, index et sauvegardes selon la procédure transverse, puis traiter les modèles entraînés sur les données retirées. La commande locale ne prétend pas désapprendre un modèle.

**Qui a réalisé ce mémoire ?** Edouard Cappaert porte le mémoire et doit en maîtriser les choix. Les travaux de cours collectifs gardent leurs crédits. Les adaptations ont bénéficié d’une assistance Codex documentée. Aucune relecture humaine n’est attribuée à l’assistant.
