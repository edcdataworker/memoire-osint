const fs = require('fs');
const secret = name => fs.readFileSync('/run/secrets/' + name, 'utf8').trim();
db.getSiblingDB('admin').createUser({user:'admin',pwd:secret('mongo_admin'),roles:['root']});
const osint = db.getSiblingDB('osint');
osint.createUser({user:'osint_writer',pwd:secret('writer'),roles:[{role:'readWrite',db:'osint'}]});
osint.createUser({user:'osint_reader',pwd:secret('reader'),roles:[{role:'read',db:'osint'}]});
osint.createCollection('documents', {validator: {$jsonSchema: {
 bsonType:'object', required:['_id','published_at','ciphertext','content_sha256','schema_version','synthetic'],
 properties:{_id:{bsonType:'string'},published_at:{bsonType:'date'},ciphertext:{bsonType:'string'},
 content_sha256:{bsonType:'string',pattern:'^[a-f0-9]{64}$'},schema_version:{enum:[1]},synthetic:{bsonType:'bool'}}
}}});
osint.documents.createIndex({published_at:1});
osint.documents.createIndex({run_id:1});
