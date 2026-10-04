#!/bin/zsh
set -eu
collection_root="${0:A:h}"
cd "$collection_root"
collection_image_dir="$HOME/Library/Application Support/MemoireOSINT"
collection_image="$collection_image_dir/CollecteTASS.sparseimage"
mkdir -p "$collection_image_dir"
chmod 700 "$collection_image_dir"
if [[ ! -f "$collection_image" ]]; then
  print "Choisissez un mot de passe pour le volume TASS. Il reste dans Terminal et n’est pas communiqué à Codex."
  hdiutil create -size 4g -fs APFS -type SPARSE -volname MemoireOSINT -encryption AES-256 "$collection_image"
  chmod 600 "$collection_image"
fi
if [[ ! -d /Volumes/MemoireOSINT ]]; then
  hdiutil attach "$collection_image"
fi
if [[ -x ../04_Bloc_4_IA/.venv/bin/python ]]; then
  collection_python=../04_Bloc_4_IA/.venv/bin/python
else
  collection_python=python3
fi
if [[ -d .state-collection && ! -f .collection-location.json ]]; then
  print "Migration vérifiée du catalogue. Le service Observatoire doit être arrêté."
  "$collection_python" -m pipeline collect-migrate --state .state-collection --destination /Volumes/MemoireOSINT/B3
elif [[ ! -f .collection-location.json ]]; then
  "$collection_python" -c 'from pipeline.common import atomic_json; atomic_json(".collection-location.json", {"state":"/Volumes/MemoireOSINT/B3", "require_encrypted": True})'
fi
print "Volume préparé. Vous pouvez ouvrir Lancer_Observatoire_TASS.command."
read "?Appuyez sur Entrée pour fermer."
