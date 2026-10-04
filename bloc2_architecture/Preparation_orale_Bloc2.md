# Bloc 2 : trame de présentation sur cinq minutes

Préparation écrite. Aucune répétition chronométrée ni prestation devant jury n’est revendiquée.

| Temps | Message | Preuve à montrer |
| --- | --- | --- |
| 0:00 à 0:35 | Deux utilisateurs explorent des articles et vérifient leurs sources. Le corpus réel comporte 21 676 articles nettoyés. | Cahier des charges et empreinte du corpus. |
| 0:35 à 1:25 | SQL garde les relations et les exécutions, MongoDB les documents variables, Elasticsearch une copie dérivée. | Schéma d’architecture et exemple d’un identifiant partagé. |
| 1:25 à 2:10 | Les bases imposent TLS, les rôles séparent lecture et écriture, les textes et sauvegardes sont chiffrés. | Tests d’accès refusé ; préciser les métadonnées et le disque non chiffrés. |
| 2:10 à 3:00 | Présenter les trois volumes du cours, les durées mesurées et les ressources. | Tableau de mesures ; préciser « synthétique » et « PostgreSQL + MongoDB ». |
| 3:00 à 4:10 | Montrer la lecture dégradée, la reprise d’un lot et la restauration dans des bases de contrôle. | Courte séquence vidéo et résultats des tests. |
| 4:10 à 5:00 | Conclure sur les limites d’un hôte unique et le raccordement des blocs 3 et 4. | Liste des écarts : hors machine, chiffrement disque, exploitation réelle et NER. |

## Questions probables

1. **Pourquoi trois stockages ?** SQL impose les relations et trace les commits ; MongoDB conserve des documents variables ; Elasticsearch sert les accès dérivés et la lecture dégradée. Cette séparation a un coût de cohérence. Pour un usage réduit, deux moteurs peuvent suffire ; le troisième prépare le rendu NER et Kibana du bloc 4.
2. **Le chiffre de 6 millions correspond-il à TASS ?** Non. C’est un test synthétique des deux stockages du cours, avec TLS, contraintes et chiffrement actifs. Il ne mesure ni le NER ni la capacité Elasticsearch à cette taille. Donner les résultats du fichier `benchmarks.json`, sans extrapoler.
3. **Que se passe-t-il pendant une panne ?** La lecture d’un article peut utiliser le dernier index, avec un avertissement de fraîcheur. L’ingestion s’arrête si les autorités ne sont pas disponibles. Une panne du Mac ou de l’application reste une interruption ; le mode dégradé n’est pas une haute disponibilité entre plusieurs machines.
4. **Une suppression peut-elle réapparaître ?** Le registre de suppressions est consulté à la lecture et à l’ingestion ; les restaurations réappliquent les suppressions plus récentes. Les futurs exports, annotations et modèles devront aussi être intégrés à cette procédure.
5. **Tout est-il chiffré ?** Les connexions aux bases, les textes et les sauvegardes le sont dans cette version. Les métadonnées, les fichiers sources et le disque du Mac ne le sont pas tous. Les interfaces d’administration HTTP restent sur la boucle locale. Ne pas annoncer une certification ISO ou une conformité globale.

## Manière de présenter

Commencer par un article et demander : « Si une base tombe, peut-on encore retrouver le passage cité ? » Montrer le chemin normal puis le mode dégradé. Définir SQL, document, index et point de reprise en une phrase. Écouter les questions, reformuler leur portée et distinguer résultat testé et proposition. Si un résultat manque, indiquer le test restant plutôt que choisir un chiffre favorable.
