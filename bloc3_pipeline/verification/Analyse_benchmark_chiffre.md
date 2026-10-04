# Mesures sur APFS AES-256

18 exécutions achevées. Trois répétitions par taille et catalogue ; corpus réel inchangé.

| Catalogue | Articles | Médiane (s) | Min. (s) | Max. (s) | Écart type (s) | Articles/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vide | 100 | 0.784494 | 0.690861 | 1.385001 | 0.3766532745417196 | 127.47 |
| Vide | 1000 | 12.382151 | 12.293275 | 12.755486 | 0.2452607368094886 | 80.76 |
| Vide | 2000 | 24.92026 | 23.962634 | 26.045515 | 1.0425641172178974 | 80.26 |
| 21 701 articles | 100 | 2.894075 | 2.822032 | 2.945151 | 0.061856338648516834 | 34.55 |
| 21 701 articles | 1000 | 14.288904 | 14.12142 | 14.98192 | 0.45621309284733746 | 69.98 |
| 21 701 articles | 2000 | 26.17471 | 26.071206 | 30.258006 | 2.3879319344582117 | 76.41 |

Deux index sur les tâches évitent le tri répété par statut et le parcours complet par identifiant lors de la propagation des suppressions. Les contrôles de droits restent exécutés avant chaque téléchargement.

Les deux passages exploratoires initiaux de 2 000 articles sur catalogue rempli duraient 57,60 et 63,92 secondes. La série initiale a été interrompue pour corriger les index ; elle ne constitue pas trois répétitions validées pour toutes les tailles. La nouvelle série complète donne 26,17 secondes de médiane pour cette taille. Ce poste partagé et ses caches ne permettent pas une estimation isolée du coût du chiffrement.

Préparation des copies et création des index exclues du chronométrage. Création du job, découverte, extraction, checkpoints, exports et secours inclus. catalog_bytes exclut un éventuel WAL ; mirror_bytes donne la taille de la copie complète. Pas de réseau, SLA ni extrapolation au-delà de 2 000 candidats. Les durées par étape et volumes sont dans Benchmark_chiffre.json.

Provenance : Benchmark_chiffre.json (hash du store et du script), Benchmark_chiffre_avant_index.json (version initiale), Version_finale.json (version livrée).
