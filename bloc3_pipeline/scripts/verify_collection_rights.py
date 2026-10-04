"""B3/B2 rights drill restricted to newly allocated fictional article IDs."""

import contextlib
import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.collection import rights, store
from pipeline.common import atomic_json, now


def main():
    b2 = ROOT.parent / "02_Bloc_2_Architecture"
    if not b2.exists():
        b2 = ROOT.parent / "bloc2_architecture"
    identifier = "rights-fixture-" + uuid.uuid4().hex
    report = {
        "at": now(),
        "article_id": identifier,
        "data": "fictional fixture",
        "real_articles_deleted": 0,
    }
    evidence = ROOT / "Preuves/Collecte_TASS"
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="memoire-rights-") as folder:
        state = Path(folder) / "state"
        store.initialize(state)
        row = {
            "id": identifier,
            "date": 1701000000,
            "title": "Fixture droits",
            "text": "Fictional obsolete text. Ω",
            "url": "https://tass.com/defense/99000001",
        }
        source = Path(folder) / "source.json"
        atomic_json(source, [row])
        config = {
            "state": str(state),
            "corpus": str(source),
            "tombstone_files": [],
            "b2_root": str(b2),
        }
        store.bootstrap(state, config)
        prefix = [
            "docker",
            "compose",
            "run",
            "--rm",
            "-T",
            "--volume",
            folder + ":/rights:ro",
            "ops",
        ]

        def docker(arguments):
            if arguments[0] != "python":
                arguments = ["python", "-m", "osint.cli", *arguments]
            with (evidence / "Droits_B3_B2.log").open("a") as log:
                subprocess.run(
                    prefix + arguments, cwd=b2, check=True, stdout=log, stderr=log, timeout=120
                )

        def assert_b2(text, present=True):
            code = """from osint.storage import pg,mongo,decrypt,es,INDEX,rectifications
import json,sys
k=sys.argv[1]; expected=sys.argv[2]; present=sys.argv[3]=='True'
with pg() as sql:
 count=sql.execute('SELECT count(*) FROM articles WHERE article_id=%s',(k,)).fetchone()[0]
 versions=sql.execute('SELECT count(*) FROM article_revisions WHERE article_id=%s',(k,)).fetchone()[0]
assert count==int(present) and versions==0
d=mongo().documents.find_one({'_id':k})
assert bool(d)==present
assert mongo().document_revisions.count_documents({'article_id':k})==0
if d: assert decrypt(d['ciphertext'],k)['text']==expected
assert es('POST',INDEX+'/_count',{'query':{'term':{'article_id':k}}})['count']==int(present)
assert es('POST','osint-entities-v1/_count',{'query':{'term':{'id':k}}})['count']==0
if k in rectifications(): assert expected not in json.dumps(rectifications())
print(json.dumps({'rights_fixture_verified':True}))
"""
            docker(["python", "-c", code, identifier, text, str(present)])

        def seed_fictional_mention():
            code = """from osint.storage import es
import sys
k=sys.argv[1]
es('PUT','osint-entities-v1/_doc/'+k+'-mention?refresh=true',{'id':k})
assert es('POST','osint-entities-v1/_count',{'query':{'term':{'id':k}}})['count']==1
"""
            docker(["python", "-c", code, identifier])

        try:
            docker(["ingest", "--file", "/rights/source.json"])
            spec = importlib.util.spec_from_file_location(
                "b2_backup", b2 / "scripts/backup_restore.py"
            )
            backup = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(backup)
            backup.EVIDENCE = evidence / "Restauration_B2"
            backup.EVIDENCE.mkdir(exist_ok=True)
            archive = backup.backup()
            seed_fictional_mention()
            with (evidence / "Droits_B3_B2.log").open("a") as log, contextlib.redirect_stdout(log):
                rights.rectify(
                    state, config, identifier, {"text": "Fictional corrected text. Ω"}, "FIX-001"
                )
                rights.propagate_b2(state, config, identifier, "FIX-001")
            assert_b2("Fictional corrected text. Ω")
            docker(["ingest", "--file", "/rights/source.json"])
            assert_b2("Fictional corrected text. Ω")
            report.update(
                rectification_sql_mongo_index=True,
                rectification_invalidates_indexed_mentions=True,
                encrypted_correction_ledger=True,
                old_versions_purged=True,
                original_reimport_keeps_correction=True,
            )
            backup.restore(archive)
            restored = json.loads((backup.EVIDENCE / "restore.json").read_text())
            assert restored["reapplied_rectifications"] >= 1
            expression = (
                'JSON.stringify(db.getSiblingDB("osint_restore_test").documents.findOne({_id:'
                + json.dumps(identifier)
                + "}))"
            )
            restored_doc = json.loads(
                backup.mongo_command("mongosh", "--quiet --eval " + shlex.quote(expression))
            )
            encrypted = backup.base64.b64decode(restored_doc["ciphertext"])
            data_key = backup.base64.b64decode((b2 / ".secrets/data_key").read_bytes())
            restored_text = json.loads(
                backup.AESGCM(data_key).decrypt(encrypted[:12], encrypted[12:], identifier.encode())
            )
            assert restored_text["text"] == "Fictional corrected text. Ω"
            code = """from osint.storage import pg,decrypt
import sys,json
k=sys.argv[1]
with pg(db='osint_restore_test') as sql:
 assert sql.execute('SELECT count(*) FROM articles WHERE article_id=%s',(k,)).fetchone()[0]==1
 assert sql.execute('SELECT count(*) FROM article_revisions WHERE article_id=%s',(k,)).fetchone()[0]==0
print(json.dumps({'restored_corrected_fixture':True}))
"""
            docker(["python", "-c", code, identifier])
            report["b2_restore_reapplies_correction"] = True
            seed_fictional_mention()
            with (evidence / "Droits_B3_B2.log").open("a") as log, contextlib.redirect_stdout(log):
                rights.erase(state, config, identifier, "FIX-002")
                rights.propagate_b2(state, config, identifier, "FIX-002", True)
            docker(["ingest", "--file", "/rights/source.json"])
            assert_b2("", False)
            report.update(
                erasure_sql_mongo_index=True,
                reimport_blocked=True,
                erasure_invalidates_indexed_mentions=True,
            )
            backup.restore(archive)
            code = """from osint.storage import pg
import sys,json
with pg(db='osint_restore_test') as sql:
 assert sql.execute('SELECT count(*) FROM articles WHERE article_id=%s',(sys.argv[1],)).fetchone()[0]==0
print(json.dumps({'restored_erasure_fixture_absent':True}))
"""
            docker(["python", "-c", code, identifier])
            report["b2_restore_reapplies_erasure"] = True
        finally:
            private_log = state / "b2-rights.log"
            if private_log.exists():
                with (evidence / "Droits_B3_B2.log").open("a") as log:
                    log.write(private_log.read_text())
            docker(["erase", identifier])
            if "archive" in locals():
                archive.unlink(missing_ok=True)
    atomic_json(evidence / "Droits_B3_B2.json", report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
