# Diagnostic NER et revue assistée du 4 octobre 2026

Les 18 articles réservés au test ont été relus par Codex, une IA, afin de proposer des annotations plus complètes que les règles lexicales initiales. Aucune attestation humaine n’a été ajoutée. Les propositions conservent les identifiants, textes, groupes et empreintes de la file de revue initiale. Le modèle n’a pas été réentraîné sur ces propositions.

## Résultat du diagnostic

Le modèle `weak-efc7c759e0-s42-e6`, SHA-256 `f35d2e57acb16d96b802c1b578b3c9e780ea53114dcd28c7cb8d65b54fc5f918`, est confronté à 104 mentions proposées par l’IA. La correspondance exige le label et les deux frontières exacts. Ces résultats mesurent l’accord avec ce brouillon, pas une qualité validée humainement.

| Périmètre | TP | FP | FN | Précision | Rappel | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Global micro | 31 | 3 | 73 | 91,18 % | 29,81 % | 44,93 % |
| WEAPON | 17 | 3 | 38 | 85,00 % | 30,91 % | 45,33 % |
| MIL_UNIT | 4 | 0 | 9 | 100,00 % | 30,77 % | 47,06 % |
| MIL_ORG | 10 | 0 | 26 | 100,00 % | 27,78 % | 43,48 % |

Les dénominateurs sont petits : les 100 % ne prouvent pas une précision parfaite en usage réel. Les 18 textes courts ont été sélectionnés avec aide des règles initiales et ne constituent pas un échantillon représentatif uniforme. Les omissions dominent le diagnostic. Les trois faux positifs et les 73 faux négatifs sont localisés dans `Preuves/Diagnostic_annotations_IA.json`, avec le protocole, l’empreinte de référence et l’identité du modèle.

## Décisions à confirmer

Le brouillon propose d’inclure le matériel militaire nommé, y compris modèles et noms de navires, d’annoter les branches militaires nommées et d’exclure les services civils de renseignement du schéma militaire. Le classement des bases navales, districts militaires et centres spécialisés exige une décision de périmètre. Les formes coordonnées et les alias doivent être vérifiés. Huit articles comportent une note de décision spécifique. Ces choix ne sont pas attribués à une personne ni à l’école.

## Faire la relecture humaine

1. Ouvrir `Revue_annotations_assistee_IA.html`, renseigner son nom et relire chaque texte intégralement.
2. Confirmer ou corriger les frontières, labels, omissions et décisions notées. Conserver aussi les articles sans entité.
3. Attester uniquement les articles réellement relus, puis exporter `human-reviewed.jsonl`.
4. Exécuter `evaluate` selon le mode d’emploi B4, avec le modèle livré et le manifeste test figé. Le contrôle refuse les annotations sans provenance humaine et les données qui recouvrent le train ou le dev.

Le fichier `Artefacts_locaux/Propositions_annotations_IA.jsonl` est un brouillon identifiable, avec le statut `ai_proposed_pending_human`. Le HTML initial est conservé pour distinguer les propositions lexicales des propositions retravaillées. Les sessions des deux outils ont des clés de stockage différentes afin de préserver la provenance.

Les métriques qualité validées restent nulles dans le rapport du modèle, et la promotion de production reste bloquée. Les F1 historiques ne sont pas modifiés. La relecture humaine d’un échantillon demandée par AI Deployment p. 24 reste à réaliser ou à documenter avec les preuves historiques correspondantes.
