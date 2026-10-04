"""Assistant-proposed labels and diagnostic scores; never attest human review."""

import json
import re
from pathlib import Path

from osint_ner.contracts import atomic_json, file_sha, read_records, utcnow, write_records
from osint_ner.metrics import score
from osint_ner.model import Predictor

ROOT = Path(__file__).resolve().parents[1]

# These proposals follow the full-text reading performed by Codex.
# They are subject to correction by a named human, especially the noted cases.
PROPOSALS = {
    1457869: {
        "MIL_UNIT": ["Black Sea Fleet", "Novorossiysk naval base"],
        "MIL_ORG": [
            "Russian armed forces",
            "armed forces of the Donetsk People’s Republic",
            "Russian Defense Ministry",
        ],
    },
    1621041: {
        "WEAPON": [
            "Kalibr", "Club-S", "Club-N", "Rubezh-ME", "Pantsyr-ME",
            "Project 22356", "Project 20382", "Project 22160", "Karakurt-E-class",
            "SS-N-27 Sizzler", "S-10 Granat",
        ],
        "MIL_ORG": ["NATO", "Russian Defense Ministry"],
    },
    1746719: {"MIL_ORG": ["Russia's Ministry of Defense"]},
    1248529: {
        "MIL_UNIT": ["120th mechanized infantry brigade"],
        "MIL_ORG": ["Defense Ministry", "Belarusian Defense Ministry"],
    },
    1627073: {
        "MIL_UNIT": ["Baltic Fleet"],
        "WEAPON": ["Su-24M", "Su-30SM", "Su-30SM2", "P50-T"],
    },
    1042755: {
        "MIL_ORG": [
            "Russian Air Force", "Defense Ministry", "Russian Defense Ministry",
            "NATO", "Air Defense Force", "US Air Force", "Russia’s Defense Ministry",
            "Aerospace Force",
        ],
        "WEAPON": ["Su-27", "Flanker", "P-8A Poseidon", "P-8 Poseidon"],
    },
    1936261: {
        "MIL_UNIT": ["battlegroup West"],
        "WEAPON": ["RAM II"],
        "MIL_ORG": ["Ukrainian armed forces"],
    },
    1427999: {"MIL_ORG": ["DPR People’s Militia", "People’s Militia"]},
    1802423: {
        "MIL_UNIT": [
            "battlegroup North", "42nd Mechanized Brigade", "36th Marines Brigade",
            "13th Brigade",
        ],
        "MIL_ORG": ["Ukrainian National Guard"],
    },
    1070736: {
        "MIL_ORG": ["Russia’s Navy", "Defense Ministry"],
        "WEAPON": [
            "Stary Oskol", "Admiral Grigorovich", "Pytlivyi", "Velikiy Ustyug", "Uglich",
            "Su-24M", "Su-34", "Su-35", "Mi-8AMTSh", "Mi-35M",
        ],
    },
    1970201: {
        "MIL_ORG": [
            "Defense Ministry", "Russian Defense Ministry",
            "Rubicon Center of Advanced Unmanned Technologies",
        ],
        "WEAPON": ["KVN"],
    },
    # Civilian foreign-intelligence agencies are outside this military schema.
    1321147: {},
    1197711: {
        "MIL_UNIT": ["Northern Fleet"],
        "MIL_ORG": [
            "Royal Norwegian Air Force", "Russian National Defense Control Center",
            "National Defense Control Center",
        ],
        "WEAPON": ["MiG-31", "Orion", "P-3S Orion"],
    },
    1057825: {
        "MIL_ORG": ["Russian army"],
        "WEAPON": ["Kinzhal", "Peresvet", "Avangard", "Sarmat"],
    },
    1714499: {"MIL_ORG": ["Pentagon"]},
    1826693: {},
    1243265: {
        "MIL_ORG": ["Russian Defense Ministry"],
        "MIL_UNIT": ["15th separate motorized rifle brigade", "Central Military District"],
    },
    1067653: {
        "MIL_ORG": ["India’s Air Force"],
        "WEAPON": ["Su-30MKI", "MiG-29", "T-90"],
    },
}

DECISIONS = {
    1457869: "Vérifier le classement MIL_UNIT de la base navale nommée.",
    1621041: "Vérifier les modèles de navires et alias comme WEAPON. La formulation coordonnée « armed forces of Russia, India and China » reste une ambiguïté à trancher.",
    1042755: "Vérifier les frontières des branches militaires et l’alias Flanker.",
    1070736: "Proposition : les navires militaires nommés sont du matériel WEAPON. Confirmer cette convention.",
    1970201: "Vérifier le classement MIL_ORG du centre Rubicon.",
    1321147: "SVR et CIA sont exclus comme services civils de renseignement. Confirmer le périmètre.",
    1197711: "Vérifier les aliases Orion et P-3S Orion et les noms complets d’organisations.",
    1243265: "Vérifier le classement MIL_UNIT du district militaire régional.",
}


def proposal(row):
    spans = []
    for label, names in PROPOSALS[row["id"]].items():
        for name in names:
            matches = list(re.finditer(re.escape(name), row["text"]))
            if not matches:
                raise ValueError(f"Missing proposed surface in article {row['id']}: {name}")
            spans.extend(
                {"start": m.start(), "end": m.end(), "label": label, "text": m.group()}
                for m in matches
            )
    selected = []
    for span in sorted(spans, key=lambda s: (-(s["end"] - s["start"]), s["start"])):
        if all(span["end"] <= e["start"] or span["start"] >= e["end"] for e in selected):
            selected.append(span)
    return {
        **row,
        "entities": sorted(selected, key=lambda s: s["start"]),
        "annotation_status": "ai_proposed_pending_human",
        "proposed_by": "Codex (IA)",
        "proposed_at": utcnow(),
        "review_note": DECISIONS.get(row["id"], "Relire toutes les mentions, omissions et frontières."),
        "review_method": "Assistant full-text proposal, not a human attestation",
    }


def main():
    source = ROOT / ".state/data/review_queue.jsonl"
    output = ROOT / "Artefacts_locaux/Propositions_annotations_IA.jsonl"
    rows = list(read_records(source))
    if {r["id"] for r in rows} != set(PROPOSALS):
        raise ValueError("Reserved review sample changed; reread the source texts")
    proposed = [proposal(row) for row in rows]
    write_records(output, proposed)
    predictor = Predictor(ROOT / ".state/runs/baseline")
    diagnostic = score(proposed, list(predictor.predict(proposed)))
    result = {
        **diagnostic,
        "at": utcnow(),
        "status": "diagnostic_against_ai_proposals_not_validated_quality",
        "reference_provenance": "Codex (IA), full-text draft with unresolved decisions",
        "reference_sha256": file_sha(output),
        "source_sha256": file_sha(source),
        "model_sha256": predictor.meta["model_sha256"],
        "model_version": predictor.meta["model_version"],
        "human_reviewed_documents": 0,
        "human_decisions_required": sorted(DECISIONS),
        "limitation": "18 selected short articles, AI draft, anchoring and selection bias. Not human gold, not production quality, not eligible for promotion.",
    }
    atomic_json(ROOT / "Preuves/Diagnostic_annotations_IA.json", result)
    template = (ROOT / "web/review_template.html").read_text()
    template = template.replace(
        "Ces propositions viennent de règles lexicales et peuvent omettre des entités.",
        "Ces propositions ont été retravaillées par Codex (IA), avec des décisions à confirmer dans les notes. Elles peuvent omettre ou mal classer des entités.",
    )
    html = template.replace("__DATA__", json.dumps(proposed, ensure_ascii=False).replace("</", "<\\/"))
    html = html.replace("osint-review-v1-", "osint-review-ai-proposal-v1-")
    (ROOT / "Revue_annotations_assistee_IA.html").write_text(html)
    print(json.dumps({"documents": len(proposed), "diagnostic": diagnostic["global"]}))


if __name__ == "__main__":
    main()
