# Besoin utilisateur et solution

## Personas de conception, à confronter au terrain

Camille, analyste de veille, veut retrouver rapidement les passages où une arme ou une unité est citée, comparer des périodes et conserver la source. Elle craint les faux positifs et une confusion entre publication et réalité opérationnelle. Elle utilise parfois le clavier seul.

Alex, responsable de cellule, veut connaître la version des données et du modèle, la qualité mesurée et les limites avant d’utiliser un tableau de bord. Il craint une mise à jour opaque ou un chiffre non reproductible. Il consulte les résultats sur écran étroit et peut agrandir le texte.

Ces personas sont hypothétiques. Aucun entretien, test avec une personne en situation de handicap ni validation utilisateur n’est inventé.

Problématique : comment faciliter la recherche de mentions militaires sourcées dans TASS tout en rendant visibles les erreurs possibles et l’état réel de validation du modèle ?

## Parcours en six étapes

1. L’analyste ouvre l’interface et lit le statut du modèle.
2. Il choisit une période et un label, puis recherche un terme.
3. Il compare les volumes et tops avec leurs dénominateurs.
4. Il ouvre un article et vérifie la mention dans le texte complet.
5. Il suit le lien source et confronte l’information à d’autres sources hors outil.
6. Il signale une erreur, alimente une revue humaine documentée puis attend une évaluation avant toute promotion.

## Exigences, fonctionnalités et vérification

| Besoin | Réponse implémentée | Preuve et limite |
| --- | --- | --- |
| Extraire trois catégories | NER spaCy, labels stricts | Modèle sérialisé et inférence ; qualité réelle inconnue |
| Retour à l’origine | ID, URL, texte complet, empreinte, offsets | Tests de spans et UI ; source unique |
| Filtrer les mêmes périodes | Paramètre année commun aux agrégations | Tests API et dashboard local ; dates UTC |
| Inclure les articles sans entités | Conservation de toutes les sorties | Compteurs total et avec entités séparés |
| Lire au clavier et agrandir | Formulaires étiquetés, focus visible, lien d’évitement, tables, texte fluide | Matrice Chromium ; lecteur d’écran et usages réels non évalués |
| Comprendre la qualité | Valeurs indisponibles explicitement affichées | Gate qualité et rapport d’entraînement |
| Réentraîner sans écraser | Détection d’empreinte, candidat immuable, promotion bloquée | Journaux d’ordonnanceur et rollback |
| Appliquer une exclusion | Registre IDs aux frontières et purge d’export | Tests dédiés ; purge totale et désapprentissage nécessitent procédure transverse |
| Pouvoir maintenir | Modules, README, Git, tests, wheel | CI/CD locale ; aucun workflow cloud exécuté |

Les objectifs de charge et de disponibilité restent ceux d’une démonstration locale. Aucun SLA de production n’est revendiqué. L’essai CPU mesure la capacité sur les données disponibles et ne prédit pas à lui seul les ressources d’un service multi-utilisateur.
