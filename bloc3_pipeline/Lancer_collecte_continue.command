#!/bin/zsh
set -eu
collection_root="${0:A:h}"
exec "$collection_root/Lancer_Observatoire_TASS.command" --watch-config "$collection_root/config/collecte_continue.json"
