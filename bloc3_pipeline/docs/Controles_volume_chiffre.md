# Contrôles B3 sur le volume chiffré

## Performance observée

100 : 2.89 s (34.5 articles/s), 1000 : 14.29 s (70.0 articles/s), 2000 : 26.17 s (76.4 articles/s).

Doubler le lot de 1 000 à 2 000 multiplie la durée par 1.83 et fait varier le débit de +9.2 %.

18 mesures validées, avec trois répétitions par taille et catalogue. Toutes vérifient les comptes, les empreintes des textes et l’égalité JSON/JSONL. Le catalogue réel conserve son empreinte. Deux index SQL évitent les tris et scans de tâches répétés, sans changer le contrôle des droits.

La durée comprend création du job, vérification initiale, découverte, téléchargement simulé, extraction, checkpoints, export et secours complet. Les étapes instrumentées n’incluent pas toute la préparation interne du worker, ce qui explique un écart avec le total. Les médianes d’étapes ne s’additionnent pas nécessairement à la médiane du total.

Poste partagé, caches non neutralisés, pas de réseau ni de mesure isolée du chiffrement. La série exploratoire avant index est incomplète et reste identifiée comme telle. L’absence générale de ralentissement significatif n’est pas garantie. Limite de 2 000 candidats par collecte.

## Cycle physique restant

Arrêt sans tâche active et checkpoint WAL exécutés. Docker refuse le démontage normal car il conserve des fichiers B4 ouverts sur le volume. Serveur B3 remis en service ; cycle complet et refus volume fermé encore à observer. Aucun démontage forcé ni arrêt des autres conteneurs.

## Critères et limites

Les critères B3-1.1 et B3-1.4 disposent des nouvelles mesures. Le complément de preuve B3-4.4/B3-6.2 sur le cycle complet reste ouvert. Leur statut « testé » décrit ces scénarios ; la décision de conformité reste celle du jury. Les huit critères oraux restent « prévu ». Le cycle protège les états B3, sans démontrer le chiffrement du Mac entier ni une récupération après perte du poste.

Preuves : verification/Benchmark_chiffre.json, Benchmark_chiffre_avant_index.json, Cycle_volume_chiffre.json et Version_finale.json.
