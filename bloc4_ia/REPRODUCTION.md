# Bloc 4 : développement et déploiement

Le développement se trouve dans `src/osint_ner/`, avec les tests dans `tests/`. La livraison locale est mise en œuvre dans `scripts/ci_local.py`. Le workflow commun du dépôt est `../.github/workflows/verification.yml`.

Depuis la racine d’une extraction neuve du dépôt, installer Python 3.12 puis exécuter :

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r bloc4_ia/requirements.lock.txt
.venv/bin/python -m pip install --no-deps -e bloc4_ia
cd bloc4_ia
../.venv/bin/python scripts/prepare_ci_demo.py
../.venv/bin/python scripts/ci_local.py
```

Le générateur utilise exclusivement des textes fictifs. Il refuse de remplacer un modèle déjà présent. Le script vérifie les dépendances, le code et les tests, construit un wheel, l’installe dans une release identifiée par empreinte et vérifie le service sur `127.0.0.1:8765`. Le service est arrêté après contrôle. Les résultats sont écrits dans `Preuves/ci_local.json` et les journaux associés. La CI télécharge ces preuves dans l’artefact `preuves-ci-ia`.

Les commandes démontrent les mécanismes de livraison et la santé d’un service éphémère. Elles ne déploient pas un hébergement public permanent, ne promeuvent pas le modèle TASS et ne mesurent pas sa qualité métier. Le corpus réel, les états de revue et les secrets sont exclus du dépôt.

Les archives `Code_Developpement_Bloc4.zip` et `Code_Deploiement_Bloc4.zip` fournies dans Drive sont autonomes : créer le venv dans le dossier extrait, puis utiliser `.venv/bin/python` au lieu de `../.venv/bin/python`. Leur notice identifie le commit publié et les empreintes du code.
