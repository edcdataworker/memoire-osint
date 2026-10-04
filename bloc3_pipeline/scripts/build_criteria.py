"""Copy all exact Bloc 3 criteria and attach localized, candid implementation evidence."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = Path("/Users/ed/.codex/skills/memoire-osint/references/bloc-3.md")
criteria = []
for line in source.read_text().splitlines():
    if line.startswith("| B3-"):
        fields = [s.strip() for s in line.split("|")[1:-1]]
        criteria.append({"id": fields[0], "source": fields[1], "critere_exact": fields[2]})
assert len(criteria) == 33
content = {
    "1.1": (
        "testé",
        "Durée du processus complet, volumes et débit mesurés sur corpus réel et trois volumes synthétiques.",
        "Preuves/Benchmark_pipeline.json;Preuves/Corpus_execution_finale.jsonl",
        "Un passage par taille, poste unique ; aucune garantie de temps en production.",
        "Répéter les mesures sur la cible d’exploitation si déploiement.",
    ),
    "1.2": (
        "testé",
        "Une ligne JSONL invalide est isolée ; seuil configurable de rejets ; journal et alerte conservés ; erreur bloquante rejouée automatiquement.",
        "Preuves/Tests_pipeline.json;pipeline/worker.py;pipeline/scheduler.py",
        "Les retries sont bornés ; erreur permanente nécessite correction.",
        "Expliquer différence rejet local et panne bloquante.",
    ),
    "1.3": (
        "testé",
        "Validation du schéma, types, dates, texte, hash et URL ; nettoyage brut reproduisant exactement les 21676 id/date/text de référence ; offsets Unicode figés.",
        "Preuves/Benchmark_pipeline.json;pipeline/transform.py;Preuves/Tests_pipeline.json",
        "Pas de vérification factuelle des affirmations TASS ni de quasi-doublons.",
        "Faire montrer une provenance et un hash à Edouard.",
    ),
    "1.4": (
        "testé",
        "JSON tableau et JSONL, corpus brut et nettoyé, 1000/10000/100000 lignes synthétiques ; lecture incrémentale et insertion par lots.",
        "Preuves/Benchmark_pipeline.json;pipeline/source.py",
        "Débit 100k inférieur à 10k dans ce passage ; absence de ralentissement significatif non établie statistiquement ; autres sources à adapter.",
        "Calibrer une cible de débit et répéter les charges représentatives.",
    ),
    "1.5": (
        "testé",
        "Copie secondaire locale vérifiée et basculement automatique de lecture après indisponibilité du fichier principal.",
        "Preuves/Tests_pipeline.json;pipeline/publish.py",
        "Redondance limitée à la publication sur le même hôte ; ingestion/SQLite/hôte sans redondance active.",
        "Prévoir autre domaine de panne pour une continuité de production.",
    ),
    "2.1": (
        "testé",
        "Échéance durable du planificateur et déclenchement réellement observé après first-delay ; collecte du fichier autorisé.",
        "Preuves/Reprise_automatique.jsonl;Preuves/Video_execution.jsonl;pipeline/scheduler.py",
        "Planificateur Python borné testé ; aucun lancement au démarrage système installé.",
        "Installer un superviseur système uniquement dans le déploiement choisi.",
    ),
    "2.2": (
        "testé",
        "Collecte, transformations, validation, stockage et publication se déroulent sans action entre étapes, même UUID.",
        "Preuves/Corpus_execution_finale.jsonl;Preuves/Video_execution.jsonl",
        "Import local ; pas de scraping réseau périodique, inutile pour le corpus fourni.",
        "Présenter le trajet complet de la donnée.",
    ),
    "2.3": (
        "testé",
        "Transactions SQLite puis exports JSON/JSONL versionnés ; current.json remplacé après qualité ; rejeu inchangé et blocage qualité vérifiés.",
        "Preuves/Tests_pipeline.json;pipeline/publish.py",
        "Le coordinateur a vérifié ingestion et réindexation des 21 676 articles B2 ; preuves transversales distinctes.",
        "Joindre la preuve B2 de la release réellement importée.",
    ),
    "2.4": (
        "testé",
        "Métriques collectées à chaque lot ; alertes locales WORKER_EXIT, QUALITY_BLOCKED, REJECTED_RECORDS et SLOW_BATCH réellement émises.",
        "Preuves/Tests_pipeline.json;Preuves/Capture_reprise.png;pipeline/common.py",
        "Alertes fichier et tableau local ; aucune alerte externe envoyée.",
        "Choisir un canal de notification avec autorisation si exploitation distante.",
    ),
    "2.5": (
        "testé",
        "SIGKILL au record 14 dans un lot non commité ; superviseur relance seul, reprend au curseur 10, termine 40/40 sans doublon.",
        "Preuves/Reprise_automatique.jsonl;Preuves/Tests_pipeline.json;pipeline/worker.py",
        "Le superviseur doit rester vivant ; panne complète d’hôte non simulée.",
        "Montrer les deux worker_start et le même run_id.",
    ),
    "3.1": (
        "testé",
        "Tableau HTTP 127.0.0.1 avec actualisation 1 seconde, métriques SQLite pendant l’exécution et captures réelles.",
        "Demonstration_locale_pipeline.mp4;Preuves/Capture_corpus.png;pipeline/monitor.py",
        "Vue locale ; pas de monitoring distribué.",
        "Rejouer la démonstration contrôlée pour prise en main.",
    ),
    "3.2": (
        "testé",
        "Volumes, durée de lot, débit de traitement, rejets, doublons, tentatives et fraîcheur exposés ; mesure bout en bout séparée.",
        "Preuves/Benchmark_pipeline.json;pipeline/monitor.py;README.md",
        "Le débit du tableau exclut hash et export ; pas de métrique CPU permanente.",
        "Garder unités et périmètres visibles à l’oral.",
    ),
    "3.3": (
        "testé",
        "Tableau lisible sans texte d’article, statut en CLI et documentation ; accès réservé au poste de l’opérateur.",
        "Preuves/Capture_corpus.png;README.md;pipeline/monitor.py",
        "Pas de comptes multiutilisateurs sur ce tableau local, pas de test utilisateur métier.",
        "Recueillir retour d’un analyste avant ouverture multiutilisateur.",
    ),
    "3.4": (
        "testé",
        "Alerte de lot lent avec seuil configurable 5s ; seuil de test 0 pour franchissement ; événements recovery_complete après reprise.",
        "Preuves/Tests_pipeline.json;Preuves/Reprise_automatique.jsonl;pipeline/worker.py",
        "Seuil d’exploitation proposé, pas un SLA validé ; pas de faux envoi externe.",
        "Calibrer les seuils sur charge normale.",
    ),
    "3.5": (
        "implémenté",
        "Métriques structurées event(), projection snapshot(), règles configurables séparées du traitement.",
        "pipeline/common.py;pipeline/monitor.py;config/portable.json;README.md",
        "Point d’extension documenté ; ajout métier réalisé ultérieurement non revendiqué.",
        "Ajouter une règle ou une métrique sur besoin établi.",
    ),
    "4.1": (
        "testé",
        "Séparation sources, transformations, état transactionnel, worker, publication, supervision, droits et CLI.",
        "pipeline/;Preuves/Controle_code.json",
        "Code local Unix, sans architecture multi-hôte.",
        "Faire suivre les imports et responsabilités par Edouard.",
    ),
    "4.2": (
        "implémenté",
        "Docstrings et commentaires sur frontières de commit, point de publication, Unicode, test SIGKILL, reprise et effacement.",
        "pipeline/worker.py;pipeline/publish.py;pipeline/rights.py",
        "Relecture personnelle du candidat non observée.",
        "Relire les sections critiques avant soutenance.",
    ),
    "4.3": (
        "testé",
        "Noms OSINT explicites, modules courts, vocabulaire Books réservé aux crédits, contrôle de style et syntaxe.",
        "Preuves/Controle_code.json;pipeline/",
        "Maîtrise personnelle à démontrer devant jury.",
        "Préparer une explication de process_batch.",
    ),
    "4.4": (
        "implémenté",
        "README : installation sans dépendance, données, commandes, supervision, droits, stockage, planification, dépannage, Docker prévu.",
        "README.md;Plan_pipeline_OSINT.pdf;Code_OSINT_Bloc3.zip",
        "Compose construit et exécuté sur ce poste ; reproduction sur autre poste non constatée.",
        "Tester archive portable sur un autre poste avant remise si possible.",
    ),
    "4.5": (
        "testé",
        "Ruff, formatage, compileall et tests comportements par processus séparés ; bibliothèques standard, paramètres SQL.",
        "Preuves/Controle_code.json;Preuves/Tests_pipeline.json;pyproject.toml",
        "Contrôles ciblés, pas une certification de sécurité exhaustive.",
        "Conserver le manifeste exact de la version remise.",
    ),
    "5.1": (
        "prévu",
        "Trame logique de cinq minutes, trajet d’un article, schéma et preuves localisées.",
        "Preparation_orale_Bloc3.md;Plan_pipeline_OSINT.pdf",
        "Aucune prestation d’Edouard observée.",
        "Répéter devant une personne et recueillir sa compréhension.",
    ),
    "5.2": (
        "prévu",
        "Arguments pour fichier fourni, SQLite de contrôle, deux formats, simplicité et alternatives documentés.",
        "Preparation_orale_Bloc3.md;Plan_pipeline_OSINT.pdf",
        "Capacité du candidat à justifier non observée.",
        "Expliquer oralement chaque choix sans lire le support.",
    ),
    "5.3": (
        "prévu",
        "Questions sur doublons, qualité, provenance, reprise, données personnelles et limites préparées.",
        "Preparation_orale_Bloc3.md",
        "Aucune séance questions/réponses constatée.",
        "S’entraîner à des réponses courtes avec preuve ouverte.",
    ),
    "5.4": (
        "prévu",
        "Méthode de reformulation et reconnaissance des limites prévue.",
        "Preparation_orale_Bloc3.md",
        "Écoute réelle non observable dans le code.",
        "Répétition avec questions imprévues.",
    ),
    "5.5": (
        "prévu",
        "Conseils regard, posture et gestes utiles sur le schéma.",
        "Preparation_orale_Bloc3.md",
        "Communication non verbale non évaluée.",
        "Répéter debout avec observateur.",
    ),
    "5.6": (
        "prévu",
        "Réponses factuelles et respectueuses, distinction entre preuve et projet préparées.",
        "Preparation_orale_Bloc3.md",
        "Professionnalisme du candidat devant jury non observé.",
        "Observer lors d’une répétition sans inventer d’appréciation.",
    ),
    "5.7": (
        "prévu",
        "Schéma, captures de fonctionnement et vidéo réelle, documents structurés et unités visibles.",
        "Plan_pipeline_OSINT.pdf;Demonstration_locale_pipeline.mp4",
        "Utilisation efficace en prestation non observée.",
        "Vérifier lisibilité dans la salle et pointer un seul résultat à la fois.",
    ),
    "5.8": (
        "prévu",
        "Déroulé minuté cible de 5 minutes et vidéo courte.",
        "Preparation_orale_Bloc3.md",
        "Aucun chronométrage d’Edouard réalisé.",
        "Faire une répétition chronométrée réelle.",
    ),
    "6.1": (
        "implémenté",
        "Champs limités à id/date/title/text/url et métadonnées de provenance ; aucun enrichissement de profils ; logs sans texte.",
        "pipeline/transform.py;pipeline/common.py;README.md",
        "Les textes publics peuvent contenir des personnes ; revue de nécessité contextuelle à valider selon B1.",
        "Maintenir finalité et minimisation lors d’une nouvelle source.",
    ),
    "6.2": (
        "testé",
        "Permissions 0700/0600, umask, localhost, aucune clé externe, conteneur testé non privilégié sans réseau, SQL paramétré.",
        "Preuves/Tests_pipeline.json;pipeline/common.py;docker-compose.yml;README.md",
        "SQLite/exports locaux en clair ; volume chiffré et séparation des rôles nécessaires avant production.",
        "Activer protection du volume et organiser comptes/rotation selon cible.",
    ),
    "6.3": (
        "testé",
        "Accès et suppression locale, compactage SQLite/WAL, purge versions, tombstones antiréintroduction et registre B2 importé, tests synthétiques.",
        "Preuves/Tests_pipeline.json;pipeline/rights.py;README.md",
        "Qualification du consentement/base légale relève de B1 ; rectification, sources historiques, sauvegardes et modèles demandent procédure transversale.",
        "Terminer la preuve de propagation B2/B3/B4 et validation de la procédure.",
    ),
    "6.4": (
        "testé",
        "Source SHA256, record index, UUID run, versions nettoyage, hashes texte brut/final, logs acteur local et droits ; filiation brut/nettoyé vérifiée.",
        "Preuves/Benchmark_pipeline.json;pipeline/transform.py;pipeline/common.py;README.md",
        "Ouvertures directes du système de fichiers non auditées ; pas de journal système central.",
        "Configurer audit OS et séparation nominative si ouverture multiutilisateur.",
    ),
    "6.5": (
        "testé",
        "Permissions excessives détectées, alerte locale et confinement chmod ; incident technique relié à qualification B1.",
        "Preuves/Tests_pipeline.json;pipeline/monitor.py;README.md",
        "Exercice technique seulement ; qualification juridique, décision de notification et simulation humaine non réalisées.",
        "Faire un exercice de gestion d’incident avec responsable B1.",
    ),
}
for c in criteria:
    key = c["id"].removeprefix("B3-")
    status, existing, proofs, gap, next_action = content[key]
    c.update(
        statut=status,
        existant=existing,
        preuves=proofs.split(";"),
        ecart=gap,
        prochaine_action=next_action,
    )
(ROOT / "Correspondance_criteres_Bloc3.json").write_text(
    json.dumps(criteria, ensure_ascii=False, indent=2) + "\n"
)
