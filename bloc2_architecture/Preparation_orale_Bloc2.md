# Bloc 2 : trame de présentation sur cinq minutes

Version 1.1 du 4 octobre 2026. Préparation écrite ; aucune répétition chronométrée ni prestation devant jury attestée.

| Temps | Message | Preuve à montrer |
| --- | --- | --- |
| 0:00 à 0:30 | L’Observatoire enrichit le corpus TASS : 21 676 articles initiaux et 5 nouveaux au raccordement. | Plan p. 2 ; Contrat_collecte_TASS.json. |
| 0:30 à 1:30 | Navigateur, collecteur et SQLite B3 publient un export figé. SQL valide les métadonnées, Mongo conserve les textes, Elasticsearch dérive les index. | Schéma p. 5 ; courte séquence de Demonstration_raccordement_Observatoire.mp4. |
| 1:30 à 2:10 | Un article modifié garde sa version précédente ; le rejeu évite les doublons. Les filtres portent sur la publication UTC, avec dates inclusives. | Schémas p. 3 et 4 ; Revisions_collecte_TASS.json. |
| 2:10 à 2:50 | B2 impose TLS, rôles et chiffrement des textes. B3 a ses propres copies et protections ; CSRF ne signifie pas comptes individuels. | Cartographie p. 17 ; contrôle du montage chiffré à effectuer. |
| 2:50 à 3:30 | Les trois volumes du cours sont synthétiques, avec une version mesurée identifiée. | Tableau p. 11 ; benchmarks.json. |
| 3:30 à 4:30 | La lecture peut utiliser le dernier index pendant une panne. La restauration B2 est isolée ; elle ne restaure pas automatiquement SQLite B3. | Vidéo de panne ; Collecte_TASS/restore.json. |
| 4:30 à 5:00 | Un poste local et une seule source. Les cinq articles nouveaux n’ont pas d’inférence NER dans cette recette. | Limites p. 15 et 18. |

## Questions probables

1. **Pourquoi SQLite en plus des bases B2 ?** SQLite est l’état opérationnel du collecteur : jobs, checkpoints, catalogue et versions. PostgreSQL et MongoDB portent les données publiées importées. Leurs copies ont des rôles et une sauvegarde distincts.
2. **Que se passe-t-il si TASS modifie un article ?** L’identifiant reste stable ; les empreintes permettent de reconnaître une modification. B2 archive le texte chiffré et ses métadonnées précédentes. Les prédictions NER ne s’appliquent qu’à la version de texte identifiée.
3. **Le chiffre de 6 millions couvre-t-il le scraping ?** Il mesure des écritures synthétiques SQL/Mongo avec TLS et chiffrement, sur la version relevée. Il ne mesure pas TASS, l’interface, les révisions ni le NER.
4. **Une panne du Mac est-elle couverte ?** Non. Lecture dégradée, miroir SQLite et reprise de worker restent sur le même hôte. Sauvegarde hors machine et scénario de sinistre complet restent à organiser.
5. **Un effacement peut-il réapparaître ?** Les exclusions durables bloquent le réimport et la recollecte. Les versions gérées sont purgées ; les restaurations réappliquent les décisions. Copies externes, annotations et modèle nécessitent une action coordonnée.
6. **Tout est-il chiffré ?** B2 chiffre textes et sauvegardes. Le lanceur B3 exige un volume chiffré monté, à vérifier avant usage ; après montage, SQLite et JSON restent lisibles par le processus. Les copies exportées ailleurs ne bénéficient pas automatiquement de cette protection.

Présenter le parcours d’un même article, expliquer ce que chaque preuve établit et annoncer les limites. La trame totalise 300 secondes prévues ; elle ne constitue pas une mesure de prestation.
