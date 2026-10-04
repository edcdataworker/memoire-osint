"""Reproduce a frozen AI-reference diagnostic, without training or promotion."""

import argparse
import json
import re
from pathlib import Path

from osint_ner.contracts import (
    atomic_json,
    file_sha,
    read_records,
    validate_spans,
    utcnow,
    write_records,
)
from osint_ner.metrics import score
from osint_ner.model import Predictor


# Codex read each complete source before the new predictions were computed.
# Exact surfaces are proposals, not independent ground truth.
PROPOSALS = {
    1006759: {"MIL_ORG": ["Russia’s Navy", "Russian Navy"]},
    1647503: {
        "MIL_ORG": ["Ukrainian army", "Defense Ministry", "Ukrainian armed forces"],
        "MIL_UNIT": ["33rd and 65th mechanized brigades"],
    },
    1887515: {},
    1663405: {"WEAPON": ["Admiral-Aircraft Carrier", "Admiral"]},
    1142513: {},
    1214737: {},
    1036353: {
        "MIL_UNIT": ["Southern Military District"],
        "MIL_ORG": ["Abkhaz Ministry of Defense"],
    },
    1702235: {
        "MIL_ORG": ["Russian Defense Ministry", "Ukrainian armed forces"],
        "MIL_UNIT": [
            "65th Mechanized Brigade",
            "33rd and 118th mechanized brigades",
            "82nd Air Assault Brigade",
        ],
        "WEAPON": ["M777"],
    },
    1122361: {
        "MIL_UNIT": ["201st military base", "Central Military District"],
        "WEAPON": ["2A46", "T-72", "BTR-82A", "Grad", "Gvozdika", "Akatsiya"],
    },
    1226971: {
        "WEAPON": ["Project 885M", "Kazan", "Yasen-M", "Kalibr", "Kalibr-PL", "Oniks"],
        "MIL_UNIT": ["Northern Fleet", "White Sea naval base"],
        "MIL_ORG": ["Russian Navy"],
    },
    1068385: {
        "MIL_UNIT": ["Northern Fleet", "Severomorsk naval base"],
        "WEAPON": ["Admiral Gorshkov", "Ka-27"],
    },
    999996: {"WEAPON": ["S-80FP", "RMG", "ODAB-500 PMV"]},
    1113983: {"WEAPON": ["Pantsir-S", "Pantsir"], "MIL_ORG": ["Russian Ministry of Defense"]},
    1612969: {},
    936322: {
        "MIL_ORG": ["NATO", "Royal Norwegian Navy"],
        "WEAPON": ["Fridtjof Nansen-class", "AEGIS", "Globus II"],
    },
    1493879: {
        "MIL_ORG": ["Collective Security Treaty Organization", "CSTO", "CSTO Joint Staff"],
        "MIL_UNIT": ["collective rapid response forces", "Northern Fleet"],
    },
    1067906: {},
    1595959: {"MIL_ORG": ["Ukrainian army"]},
    1393795: {
        "MIL_ORG": [
            "Belarusian General Staff",
            "Belarusian Air Force and Air Defense Troops",
            "Russian Aerospace Force",
        ]
    },
    1498067: {"MIL_ORG": ["Japan’s Self-Defense Forces", "Japan’s Defense Ministry", "NATO"]},
    1527837: {
        "WEAPON": [
            "Yars",
            "Tula",
            "project 667BDRM",
            "Tu-95MS",
            "Sineva",
            "Karelia",
            "Kalibr",
            "Iskander",
            "Kinzhal",
            "MiG-31",
            "Tsirkon",
            "B-52",
            "B-52s",
        ],
        "MIL_ORG": ["General Staff", "NATO"],
        "MIL_UNIT": ["Kleine-Brogel airbase"],
    },
    1055135: {
        "WEAPON": [
            "Belgorod",
            "Project 949A",
            "Antey",
            "Project 949AM",
            "Project 09852",
            "Project 941",
            "Akula",
            "Status-6",
            "Khabarovsk",
            "Poseidon",
        ],
        "MIL_ORG": ["Russia’s Defense Ministry", "Russian Navy"],
    },
    1913641: {
        "WEAPON": [
            "Su-57E",
            "Su-57",
            "Pantsyr-S1M",
            "Lancet-E",
            "Gardenia",
            "S-400 Triumf",
            "Tor",
            "Tor-M2KM",
            "Tor-E2",
            "Tor-M2K",
        ],
        "MIL_UNIT": ["Yelahanka Air Force base"],
    },
    1494323: {"MIL_ORG": ["NATO", "AUKUS"]},
}


def proposed(row):
    spans = []
    for label, names in PROPOSALS[row["id"]].items():
        for name in names:
            matches = list(re.finditer(re.escape(name), row["text"]))
            if not matches:
                raise ValueError(f"Proposed surface missing from article {row['id']}: {name}")
            spans.extend(
                {"start": m.start(), "end": m.end(), "label": label, "text": m.group()}
                for m in matches
            )
    selected = []
    for span in sorted(spans, key=lambda s: (-(s["end"] - s["start"]), s["start"])):
        if all(
            span["end"] <= other["start"] or span["start"] >= other["end"] for other in selected
        ):
            selected.append(span)
    return {
        **row,
        "entities": validate_spans(row["text"], selected),
        "annotation_status": "ai_proposed",
        "proposed_by": "Codex (IA)",
        "proposal_method": "Complete-text reading before new predictions, fixed named-entity conventions; exact-surface expansion with longest-match overlap resolution.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--initial-reference", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    directory = Path(args.directory)
    rows = list(read_records(directory / "selection_24.jsonl"))
    assert {r["id"] for r in rows} == set(PROPOSALS)
    initial = list(read_records(args.initial_reference))
    manifest = {str(r["id"]): r for r in read_records(args.split_manifest)}
    additional = [proposed(r) for r in rows]
    reference = initial + additional
    assert len(reference) == 42 and len({str(r["id"]) for r in reference}) == 42
    for row in reference:
        saved = manifest[str(row["id"])]
        assert saved["split"] == row["split"] == "test"
        assert saved["text_sha256"] == row["text_sha256"] and saved["group_id"] == row["group_id"]
    assert len({r["group_id"] for r in reference}) == 42
    # Freeze and identify every proposed span before loading the model.
    write_records(directory / "reference_24.jsonl", additional)
    write_records(directory / "reference_42.jsonl", reference)
    frozen_sha = file_sha(directory / "reference_42.jsonl")
    frozen_at = utcnow()
    predictor = Predictor(args.run)
    predictions = list(predictor.predict(reference))
    write_records(directory / "predictions_42.jsonl", predictions)
    assert file_sha(directory / "reference_42.jsonl") == frozen_sha
    result = score(reference, predictions)
    result.update(
        at_utc=utcnow(),
        status="exploratory_agreement_with_ai_reference",
        model_sha256=predictor.meta["model_sha256"],
        model_version=predictor.meta["model_version"],
        reference_sha256=frozen_sha,
        reference_frozen_at_utc=frozen_at,
        reference_provenance="Codex (IA): 18 initial drafts retained and 24 new full-text proposals prepared before new inference.",
        initial_reference_sha256=file_sha(args.initial_reference),
        selection=json.loads((directory / "selection_manifest.json").read_text()),
        initial_18=score(reference[:18], predictions[:18]),
        additional_24=score(reference[18:], predictions[18:]),
        additional_by_length={
            band: score(
                [r for r in additional if r["length_stratum"] == band],
                [p for p in predictions[18:] if p["length_stratum"] == band],
            )
            for band in ("court", "moyen", "long")
        },
        negative_documents=sum(not r["entities"] for r in reference),
        script_sha256=file_sha(__file__),
        predictions_sha256=file_sha(directory / "predictions_42.jsonl"),
        model_retrained=False,
        eligible_for_model_promotion=False,
        limitation="AI proposals may contain omissions or boundary/class errors. Initial 18 retain selection/anchoring bias. Additional 24 are length-stratified, unweighted, limited to <=4500 codepoints; no corpus-wide accuracy inferred. A changed score reflects a different reference, not model improvement.",
    )
    atomic_json(args.output, result)
    print(
        json.dumps(
            {
                "documents": result["documents"],
                "global": result["global"],
                "negative_documents": result["negative_documents"],
                "additional_24": result["additional_24"]["global"],
            }
        )
    )


if __name__ == "__main__":
    main()
