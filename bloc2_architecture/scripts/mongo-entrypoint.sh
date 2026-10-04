#!/bin/bash
set -euo pipefail
chown -R mongodb:mongodb /data/db
install -o mongodb -g mongodb -m 600 /run/secrets/mongo.pem /tmp/mongo.pem
if [ ! -f /data/db/.osint_initialized ]; then
  gosu mongodb mongod --bind_ip 127.0.0.1 --port 27017 --dbpath /data/db \
    --logpath /tmp/init-mongo.log --fork --wiredTigerCacheSizeGB 0.25
  mongosh --quiet --file /bootstrap/init.js
  gosu mongodb mongod --dbpath /data/db --shutdown
  touch /data/db/.osint_initialized
fi
exec gosu mongodb mongod --bind_ip_all --auth --tlsMode requireTLS \
 --tlsCertificateKeyFile /tmp/mongo.pem --tlsCAFile /run/secrets/ca.crt \
 --tlsAllowConnectionsWithoutCertificates --wiredTigerCacheSizeGB 0.25
