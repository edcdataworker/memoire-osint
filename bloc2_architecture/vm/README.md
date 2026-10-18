# Serveur virtuel du Bloc 2

La VM locale `memoire-osint-bloc2` est déployée et vérifiée le 18 octobre 2026 : Ubuntu 24.04.5 LTS, 4 CPU, 8 Go de RAM demandés et un disque virtuel de 30 Go, sous Multipass 1.16.4 avec QEMU. Elle est laissée démarrée. Elle reste installée jusqu’à sa suppression et peut être arrêtée pour libérer les ressources de calcul.

## Résultat vérifié

Cloud-init termine sans erreur. Docker et Compose fonctionnent dans la VM. PostgreSQL, MongoDB et l’API sont sains ; 100 documents fictifs sont ingérés dans les deux bases. La lecture HTTPS authentifiée restitue un document et une requête sans authentification reçoit 401. La connexion PostgreSQL utilise TLS 1.3. L’API utilise aussi le client MongoDB configuré en TLS.

Le redémarrage complet de la VM change son identifiant de démarrage. Les trois services reprennent automatiquement et les 100 documents restent lisibles. Trois relevés de ressources après redémarrage ne déclenchent aucune alerte. Les empreintes de 22 fichiers publics déployés correspondent aux sources locales. Preuves : `Preuves/VM_20261018/Validation_VM_Bloc2.json`, `Verification_services.json`, `Conteneurs_verifies.json`, `Monitoring_VM.jsonl` et `Manifest_code_final_VM.json`.

Les ports des bases ne sont pas publiés. L’API est liée uniquement à `127.0.0.1:18443` à l’intérieur de la VM, avec utilisateur 10001 et racine du conteneur en lecture seule. Cette adresse n’est pas celle du navigateur macOS. Les certificats et secrets sont créés dans la VM, sans importer les secrets existants du Mac.

## Utilisation courante

Depuis la racine du Bloc 2 sur le Mac :

```sh
multipass start memoire-osint-bloc2
python3 scripts/virtual_server.py verify
python3 vm/deploy_synthetic.py verify --proofs Preuves/VM_controle_local
multipass shell memoire-osint-bloc2
```

Attendre la santé des conteneurs après un démarrage avant de lancer le contrôle applicatif. Quitter le shell avec `exit`. Pour arrêter proprement la VM depuis le Mac :

```sh
multipass stop memoire-osint-bloc2
```

La VM arrêtée conserve ses disques. Aucun arrêt planifié, accès Internet public, transfert TASS ou déploiement Elasticsearch/Kibana n’est inclus dans cet essai. Aucun redémarrage du Mac, test de perte du poste, sauvegarde hors machine ni chiffrement intégral du disque VM n’est attesté. La validation sur 100 fixtures ne remplace pas les essais volumétriques du cours, exécutés séparément sur leurs environnements identifiés.

## Reproduction sur un environnement neuf

Installer Multipass avec le paquet officiel signé, puis, depuis la racine du Bloc 2 :

```sh
python3 scripts/virtual_server.py plan
python3 scripts/virtual_server.py up
python3 vm/deploy_synthetic.py deploy --proofs Preuves/VM_nouvel_essai
```

`up` refuse de remplacer une VM existante. `deploy` refuse un dossier applicatif existant avant tout transfert. Il transmet uniquement une liste de fichiers publics, normalise leurs droits de lecture pour Linux et génère 100 documents fictifs. Aucun corpus, modèle, guide oral, vidéo ou secret existant n’est transféré. Les répertoires d’état sont réservés à l’UID 10001 et l’ingestion utilise cette identité. Les opérations ultérieures d’écriture de l’état doivent conserver cette identité pour rester lisibles par l’API.

Le premier essai a révélé une conversion du champ de permissions du marqueur public en entier YAML par Multipass, puis des droits trop restrictifs à l’extraction du code. La configuration corrigée omet ce champ facultatif et le déploiement fixe explicitement les dossiers publics à 0755 et leurs fichiers à 0644, avant la création des secrets et de l’état. Les diagnostics initiaux sont conservés dans le pilotage local.

La structure `docker/` contient l’entrée du déploiement applicatif, `scripts/` ses opérations et `vm/` le provisionnement et l’essai dédié. Terraform et Kubernetes ne sont pas utilisés sur cette cible locale.

Sources : [Canonical, installation de Multipass](https://canonical.com/multipass/docs/latest/how-to-guides/install-multipass/), [Canonical, cloud-init](https://canonical.com/multipass/docs/stable/how-to-guides/manage-instances/launch-customized-instances-with-multipass-and-cloud-init/), [Docker, chemins des montages](https://docs.docker.com/engine/storage/bind-mounts/).

Dans le dépôt public, les preuves locales `Preuves/VM_20261018/` sont disponibles dans [verification/VM_20261018](../verification/VM_20261018). La CI contrôle le code et les garde-fous ; le redémarrage de la VM du Mac est attesté par ces preuves locales distinctes.
