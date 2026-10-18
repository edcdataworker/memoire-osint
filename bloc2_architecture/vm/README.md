# Serveur virtuel du Bloc 2

Le serveur retenu est une VM Ubuntu 24.04 locale via Multipass : 4 CPU, 8 Go de RAM et 30 Go de disque. Le provisionnement installe Docker et Compose. Le fichier cloud-init utilise l’en-tête requis puis une structure JSON compatible YAML. Cette cible constitue une étape distincte des conteneurs Docker Desktop déjà testés.

Depuis la racine du Bloc 2 :

```sh
python3 scripts/virtual_server.py plan
python3 scripts/virtual_server.py up
python3 scripts/virtual_server.py verify
```

`plan` fonctionne sans fournisseur. `up` crée uniquement une nouvelle VM nommée et refuse de remplacer une instance existante. Il ne copie ni corpus, ni secret, ni modèle. `verify` attend cloud-init puis exige un moteur Docker fonctionnel. Conserver sa sortie comme preuve après exécution réussie. Prévoir les ressources indiquées et une connexion pour télécharger Ubuntu et les paquets.

Sur le poste vérifié le 18 octobre, Multipass est absent : le plan est vérifié, le déploiement VM reste à démontrer. L'installation du fournisseur, la création de la VM puis le déploiement applicatif sur ses volumes protégés sont les étapes restantes. Les chemins de montages Compose désignent le disque du serveur Docker, donc une copie de configuration macOS ne suffit pas dans la VM. Ne pas exposer les bases sur le réseau ni copier un état privé vers un disque non chiffré. Aucun arrêt ou effacement automatique de VM n'est prévu.

La structure `docker/` contient le déploiement applicatif, `scripts/` ses opérations, `vm/` le provisionnement du serveur. Terraform et Kubernetes ne sont pas nécessaires à cette cible unique. Les preuves de Docker Desktop ne valent pas validation de cette VM.

Sources : [Canonical, lancement et cloud-init](https://canonical.com/multipass/docs/stable/how-to-guides/manage-instances/launch-customized-instances-with-multipass-and-cloud-init/), [Docker, chemins des montages](https://docs.docker.com/engine/storage/bind-mounts/).
