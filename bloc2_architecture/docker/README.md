# Infrastructure Docker du Bloc 2

La définition canonique est `../docker-compose.yml`. L'entrée `compose.yaml` l'inclut sans copier sa configuration. Depuis la racine du Bloc 2 :

```sh
docker compose -f docker/compose.yaml config --quiet
python3 scripts/infrastructure.py deploy
```

Docker Compose 2.20.3 ou ultérieur est nécessaire pour `include`. La version testée est relevée dans les preuves du complément. Les chemins des volumes, secrets et contextes de construction restent relatifs au fichier inclus, comme décrit par [Docker](https://docs.docker.com/reference/compose-file/include/).

Le Dockerfile applicatif reste dans `../app/Dockerfile`, les schémas dans `../sql` et `../mongo`, et l'exploitation dans `../scripts`. Le choix IaC est Docker Compose. Aucun répertoire Terraform ou Kubernetes vide n'est ajouté : ces technologies ne sont pas utilisées.

Le déploiement exécuté est local sous Docker Desktop. Il ne provisionne pas de serveur virtuel autonome, de VM cloud ou d'infrastructure à plusieurs hôtes. Un serveur Linux hébergeant Docker constitue une évolution à préparer, avec stockage, certificats, accès et sauvegarde hors machine adaptés.
