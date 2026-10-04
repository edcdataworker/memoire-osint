#!/bin/zsh
set -eu
cd "${0:A:h}"
if [[ ! -d /Volumes/MemoireOSINT ]]; then
  print 'Déverrouiller le volume MemoireOSINT avant la revue. Aucun fichier en clair ne sera créé.'
  exit 1
fi
exec .venv/bin/python -m osint_ner.human_review \
  --reference /Volumes/MemoireOSINT/B4/Evaluation_42_articles/reference_42.jsonl \
  --manifest .state/data/split_manifest.jsonl \
  --run .state/runs/baseline \
  --directory /Volumes/MemoireOSINT/B4/Revue_humaine_42 \
  --encrypted-root /Volumes/MemoireOSINT --port 8767
