#!/bin/zsh
set -eu
collection_root="${0:A:h}"
cd "$collection_root"
if [[ -x "../04_Bloc_4_IA/.venv/bin/python" ]]; then
  collection_python="../04_Bloc_4_IA/.venv/bin/python"
else
  collection_python="python3"
fi
collection_image="$HOME/Library/Application Support/MemoireOSINT/CollecteTASS.sparseimage"
if [[ ! -f "$collection_image" ]]; then
  print "Préparez d’abord le volume avec Preparer_volume_chiffre.command. Aucun catalogue en clair ne sera créé."
  read "?Appuyez sur Entrée pour fermer."
  exit 1
fi
if [[ ! -d /Volumes/MemoireOSINT ]]; then
  hdiutil attach "$collection_image"
fi
if [[ ! -f .collection-location.json ]]; then
  print "Migration à terminer avec Preparer_volume_chiffre.command."
  exit 1
fi
collection_state=$("$collection_python" -c 'import json; print(json.load(open(".collection-location.json"))["state"])')
exec "$collection_python" -m pipeline collect-ui --state "$collection_state" --require-encrypted --open
