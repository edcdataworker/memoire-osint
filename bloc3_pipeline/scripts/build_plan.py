"""Generate the PDF and editable Markdown, preserving the Books document structure."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
B = json.loads((ROOT / "Preuves/Benchmark_pipeline.json").read_text())
TEST = json.loads((ROOT / "Preuves/Tests_pipeline.json").read_text())
C = colors.HexColor("#86152c")
G = colors.HexColor("#626262")
LIGHT = colors.HexColor("#f6f0f1")
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleRed",
        fontName="Helvetica",
        fontSize=32,
        leading=37,
        textColor=C,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="Sub",
        fontName="Helvetica",
        fontSize=18,
        leading=23,
        textColor=G,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
)
styles["Heading1"].fontName = "Helvetica-Bold"
styles["Heading1"].fontSize = 19
styles["Heading1"].leading = 23
styles["Heading1"].textColor = C
styles["Heading1"].spaceAfter = 15
styles["Heading2"].fontSize = 12
styles["Heading2"].leading = 15
styles["Heading2"].textColor = C
styles["BodyText"].fontSize = 10
styles["BodyText"].leading = 14
styles["BodyText"].spaceAfter = 9
styles.add(ParagraphStyle(name="SmallText", fontSize=8.4, leading=11, textColor=G, spaceAfter=7))
styles.add(ParagraphStyle(name="TableText", fontSize=8.5, leading=11))
styles.add(ParagraphStyle(name="CaptionText", fontSize=8.7, leading=12, textColor=G, spaceAfter=10))
flow = []
md = []


def p(text, style="BodyText"):
    flow.append(Paragraph(escape(text).replace("\n", "<br/>"), styles[style]))
    md.append(text + "\n")


def h(text, level=1):
    flow.append(Paragraph(escape(text), styles["Heading" + str(level)]))
    md.append("#" * (level + 1) + " " + text + "\n")


def page(title):
    flow.append(PageBreak())
    h(title)


def table(headers, rows, widths):
    data = [[Paragraph(escape(str(c)), styles["TableText"]) for c in headers]] + [
        [Paragraph(escape(str(c)), styles["TableText"]) for c in row] for row in rows
    ]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), C),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c7c7c7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(t)
    flow.append(Spacer(1, 12))
    md.append(
        "| "
        + " | ".join(headers)
        + " |\n| "
        + " | ".join(["---"] * len(headers))
        + " |\n"
        + "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in rows)
        + "\n"
    )


def code(s):
    flow.append(
        Preformatted(
            s,
            ParagraphStyle(
                name="CodeLocal",
                fontName="Courier",
                fontSize=7.8,
                leading=10,
                backColor=colors.HexColor("#f4f4f4"),
                borderPadding=8,
                spaceAfter=12,
            ),
        )
    )
    md.append("```python\n" + s + "\n```\n")


def picture(name, caption, height=None):
    f = ROOT / "Preuves" / name
    im = Image(str(f))
    w = 480
    im.drawHeight = im.imageHeight * w / im.imageWidth
    im.drawWidth = w
    flow.append(im)
    p(caption, "CaptionText")
    md.append(f"![{caption}](Preuves/{name})\n")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(G)
    canvas.drawString(48, 27, "Data Pipelines for AI | Mémoire OSINT | Bloc 3")
    canvas.drawRightString(547, 27, str(doc.page))
    canvas.restoreState()


flow.append(Spacer(1, 60))
p("EUGENIA SCHOOL", "Sub")
flow.append(Spacer(1, 28))
p("Livrable", "TitleRed")
p("Data Pipelines for AI", "Sub")
p("Pipeline du corpus TASS", "Sub")
flow.append(Spacer(1, 20))
table(
    ["Repère", "Version présentée"],
    [
        ["Sujet", "Collecte, qualité, publication et reprise automatique"],
        ["Auteur", "Edouard Cappaert, adaptation préparée avec l’assistance de Codex"],
        ["Enseignant / modèle", "Matthieu Larboullet ; rendu Books du 02/06/2026"],
        ["Code", "Dossier pipeline/ et archive Code_OSINT_Bloc3.zip"],
        ["Date", "04/10/2026"],
        ["Statut", "Prototype local exécuté ; aucune exploitation externe de production attestée"],
    ],
    [110, 370],
)
p(
    "Le corpus et les preuves réels sont distingués des fixtures synthétiques. Aucune validation humaine des annotations ni performance orale n’est inventée.",
    "SmallText",
)
page("Sommaire")
for n, title in [
    (3, "Introduction et analyse des données"),
    (4, "Schéma du pipeline et stack technique"),
    (5, "Code principal et reprise automatique"),
    (6, "Problèmes rencontrés, droits et sécurité"),
    (7, "Analyse des données et résultats mesurés"),
    (8, "Captures d’exécution et monitoring"),
    (9, "Documentation d’utilisation"),
    (10, "Conclusion, soutenance et sources"),
]:
    p(f"{title}  ........................................  {n}")
h("Lire les états de preuve", 2)
p(
    "Prévu : décrit mais non exécuté. Implémenté : présent dans le code ou les documents. Testé : vérifié par une exécution identifiée. Démontré au jury : dépend de la prestation et de l’appréciation du jury ; le présent dossier ne l’attribue pas à sa place."
)
p(
    "Les 33 critères exacts de Bloc 3!A6:A38 sont repris dans Correspondance_criteres_Bloc3.json, avec preuve, écart et prochaine action. Les huit critères de l’oral restent préparés, sans observation de prestation."
)
h("Périmètre vérifié", 2)
p(
    f"{TEST['passed']} scénarios synthétiques, un import réel nettoyé et un import réel brut, plusieurs tailles et les formats JSON/JSONL. La construction et l’exécution Docker locales ont aussi été vérifiées avec une reprise au checkpoint 21 676. Le système n’envoie pas d’alertes à des tiers."
)
page("Introduction et analyse des données")
h("Contexte et problématique", 2)
p(
    "Le mémoire construit une plateforme de veille OSINT pour une cellule fictive. Le Bloc 3 prépare des articles TASS fiables et traçables pour l’architecture du Bloc 2 et la reconnaissance d’entités du Bloc 4 : WEAPON, MIL_UNIT et MIL_ORG."
)
p(
    "Comment automatiser un import qui tolère les erreurs isolables, protège la dernière publication valide et reprend après une panne sans perdre de données ni décaler les offsets ? La démarche ETL et le plan du rendu Books sont conservés, avec des champs et contrôles adaptés au texte journalistique."
)
h("Source et transformations", 2)
p(
    "Le corpus brut retrouvé contient 21 742 articles. La provenance pédagogique locale et les empreintes sont documentées dans 00_Pilotage/Recuperation_artefacts.md. Le pipeline reproduit les 66 rejets sans texte et les 21 676 articles du corpus nettoyé reconstitué. Il ne lance aucun nouveau scraping."
)
table(
    ["Champ", "Contrat"],
    [
        ["id, date", "Valeurs et types source conservés ; epoch en secondes, date lisible UTC."],
        [
            "title, text, url",
            "Titre éventuellement vide, texte obligatoire, URL HTTPS ; champs additionnels exclus.",
        ],
        ["text_sha256", "Hash du texte UTF-8 figé, distinct du hash JSON de B2."],
        [
            "provenance",
            "Fichier SHA-256, index source, UUID run, version et changements de nettoyage.",
        ],
        ["offset_unit", "unicode_codepoint ; intervalle [start,end) dans ce texte exact."],
    ],
    [112, 368],
)
p(
    "En mode raw, les espaces sont normalisés et les caractères de contrôle retirés avant annotation. En mode clean, le texte doit déjà satisfaire le contrat et n’est pas transformé. Toute correction ultérieure du texte exige une nouvelle version des annotations. Les clés B2/B4 peuvent convertir id en chaîne à leur frontière."
)
page("Schéma du pipeline et stack technique")
d = Drawing(480, 255)
boxes = [
    (12, 185, "Fichier autorisé", "JSON / JSONL"),
    (174, 185, "Lecture et validation", "types, texte, URL"),
    (336, 185, "Lot transactionnel", "articles + curseur"),
    (336, 90, "Contrôle qualité", "taux rejets, volume"),
    (174, 90, "Publication atomique", "JSON + JSONL"),
    (12, 90, "B2 et B4", "stockage / NER"),
]
for x, y, a, b in boxes:
    d.add(Rect(x, y, 132, 52, rx=5, ry=5, fillColor=LIGHT, strokeColor=C))
    d.add(
        String(
            x + 66,
            y + 31,
            a,
            textAnchor="middle",
            fontName="Helvetica-Bold",
            fontSize=9,
            fillColor=C,
        )
    )
    d.add(
        String(
            x + 66, y + 15, b, textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=G
        )
    )


def arrow(x1, y1, x2, y2):
    d.add(Line(x1, y1, x2, y2, strokeColor=C, strokeWidth=1.4))
    if x2 > x1:
        d.add(Polygon([x2, y2, x2 - 6, y2 + 3, x2 - 6, y2 - 3], fillColor=C, strokeColor=C))
    elif x2 < x1:
        d.add(Polygon([x2, y2, x2 + 6, y2 + 3, x2 + 6, y2 - 3], fillColor=C, strokeColor=C))
    else:
        d.add(Polygon([x2, y2, x2 - 3, y2 + 6, x2 + 3, y2 + 6], fillColor=C, strokeColor=C))


arrow(144, 211, 174, 211)
arrow(306, 211, 336, 211)
arrow(402, 185, 402, 142)
arrow(336, 116, 306, 116)
arrow(174, 116, 144, 116)
d.add(
    String(
        240,
        47,
        "Planificateur + processus enfant + retries + alertes locales",
        textAnchor="middle",
        fontSize=10,
        fillColor=C,
    )
)
d.add(
    String(
        240,
        27,
        "Registre des suppressions B2 relu avant import et publication",
        textAnchor="middle",
        fontSize=9,
        fillColor=G,
    )
)
flow.append(d)
md.append("Schéma : fichier → lecture/validation → lot SQLite → qualité → JSON/JSONL → B2/B4.\n")
h("Des responsabilités limitées et explicites", 2)
p(
    "Python 3.12 et sa bibliothèque standard suffisent au traitement. SQLite WAL est un journal local de staging et de reprise. Il ne remplace pas PostgreSQL et MongoDB, autorités métier B2. JSONL facilite la lecture séquentielle de B4 ; le tableau JSON reste compatible avec l’import B2 actuel."
)
p(
    "Le planificateur Python enregistre la prochaine échéance, lance un worker et surveille sa sortie. Le tableau HTTP local lit les métriques chaque seconde. Les publications possèdent un miroir local vérifié pour continuer la lecture si un fichier principal devient indisponible."
)
p(
    "Alternative : un orchestrateur distribué faciliterait plusieurs hôtes, mais ajouterait un service sans besoin démontré pour ce corpus. Le Dockerfile et Compose ont été construits et exécutés localement par le coordinateur. Aucun service B2 n’a été manipulé par le développement B3."
)
page("Code principal et reprise automatique")
h("Une transaction, un point de reprise", 2)
p(
    "Les articles acceptés et les rejets du lot sont écrits avant de déplacer le curseur, dans le même contexte transactionnel. Le curseur désigne le prochain index source, et non le nombre d’articles publiés. Ainsi les lignes rejetées sont elles aussi prises en compte."
)
code(
    'with db:  # commit ou rollback du lot entier\n    # validation, insertion des articles et motifs de rejet\n    db.execute(\n        "UPDATE runs SET checkpoint=? WHERE run_id=?",\n        (batch[-1][0] + 1, run_id),\n    )\n# Le code complet ajoute compteurs et durée : worker.py.'
)
p(
    "L’extrait illustre la frontière de transaction du code complet. L’empreinte du fichier et celle du contrat retrouvent automatiquement une exécution interrompue. Une nouvelle source ne peut donc pas reprendre le curseur d’une ancienne. Le parseur relit les entrées jusqu’au curseur ; cette relecture a un coût sur une très grande source."
)
h("Scénario réellement exécuté", 2)
table(
    ["Étape synthétique", "Observation du test"],
    [
        ["Départ", "40 articles, lots de 10, curseur 0."],
        ["Panne", "SIGKILL au record 14, au milieu d’une transaction."],
        ["État durable", "Seuls les 10 premiers articles sont validés."],
        ["Reprise autonome", "Le superviseur relance ; worker_start reprend au checkpoint 10."],
        ["Fin", "Même run, 2 tentatives, 40 acceptés, aucun doublon."],
    ],
    [115, 365],
)
p(
    "Preuve : Preuves/Reprise_automatique.jsonl et Tests_pipeline.json. Un autre test verrouille réellement SQLite pendant 2,5 secondes ; le worker échoue puis le superviseur reprend après libération. Les retries sont bornés : une panne permanente finit en alerte et code non nul."
)
h("Publication après qualité", 2)
p(
    "L’activation remplace uniquement current.json après préparation complète des deux exports et du miroir. Le taux de rejet de 0,5 % est un choix du prototype. Le test de source dégradée vérifie l’identité de la publication précédente après refus de la nouvelle."
)
page("Problèmes rencontrés, droits et sécurité")
table(
    ["Point rencontré", "Réponse et limite"],
    [
        [
            "Titres vides réels",
            "Six titres vides avaient été rejetés par une validation trop stricte. Le contrat a été corrigé : le texte, nécessaire au NER, reste obligatoire.",
        ],
        [
            "Publication Books avant qualité",
            "L’ordre a été inversé dans cette adaptation : validation globale avant activation.",
        ],
        [
            "Relance sans reprise",
            "Le point durable est validé avec chaque lot et retrouvé par le worker suivant.",
        ],
        ["Offsets fragiles", "Nettoyage uniquement avant annotation ; hash du texte exact publié."],
        [
            "Panne de publication",
            "Miroir de lecture local testé ; même hôte et même disque, sans haute disponibilité complète.",
        ],
    ],
    [125, 355],
)
h("Droits et minimisation", 2)
p(
    "Seuls les champs utiles sont sélectionnés. Les articles publics peuvent contenir des personnes ; leur caractère public ne dispense pas de qualification selon B1. Aucun consentement n’est supposé acquis. Les journaux évitent textes et valeurs invalides complètes."
)
p(
    "Le registre B2 peut être lu avant traitement et publication. Les suppressions créent des tombstones durables, retirent les textes de SQLite et des exports, puis compactent la base et son journal. Accès, suppression et non-réintroduction sont testés sur fixtures. Les sources historiques et les modèles demandent une propagation transversale ; la rectification nécessite une source et des annotations nouvelles."
)
h("Protection et incidents", 2)
p(
    "Permissions privées 0700/0600, serveur sur 127.0.0.1, absence de secret externe et requêtes SQL paramétrées limitent l’exposition locale. Les données B3 restent en clair au repos : un volume chiffré est une action nécessaire avant une exploitation réelle. Les accès directs au disque ne sont pas journalisés par l’application."
)
p(
    "Le test de permissions 0755 déclenche une alerte locale et un retour à 0700. Cela prouve un signal et un confinement techniques. La qualification d’une violation, son risque et d’éventuelles notifications doivent être décidés dans la procédure B1 ; aucun envoi externe n’est effectué."
)
page("Analyse des données et résultats mesurés")
rows = []
for r in B["results"]:
    rows.append(
        [
            "Synthétique" if r["data_kind"] == "synthetic" else "TASS brut",
            str(r["input_records"]),
            r["format"],
            f"{r['duration_end_to_end_s']:.3f} s",
            f"{r['rows_per_second_end_to_end']:.0f}",
        ]
    )
table(["Jeu", "Lignes lues", "Format", "Durée totale", "Lignes/s"], rows, [110, 80, 70, 110, 110])
p(
    "Mesure du processus complet : empreinte source, lecture, validation, transactions, export des deux formats et copies locales. Chaque taille a été exécutée une seule fois sur un poste partagé, avec services et capture navigateur actifs. Les données synthétiques sont plus courtes et répétitives que TASS. Aucun débit de production n’est garanti ni extrapolé à de grands corpus réels.",
    "CaptionText",
)
h("Qualité du corpus réel", 2)
p(
    "21 742 articles bruts lus ; 66 textes vides rejetés ; 21 676 articles publiés. Les listes (id, date, text) sont strictement identiques à celles du corpus reconstitué. Aucun doublon exact d’ID ni de texte n’a été détecté dans cette publication. Six titres vides sont conservés sans invention."
)
h("Variations de charge", 2)
p(
    "Les formats JSON et JSONL sont tous deux vérifiés. La mémoire du parseur dépend surtout du lot et de la taille d’un article. Le débit varie avec les écritures et la taille du stockage ; l’absence de ralentissement significatif n’est pas établie par une seule mesure. Le besoin d’une cible de performance reste à définir avec l’exploitant."
)
h("Erreurs et continuité", 2)
p(
    f"Les {TEST['passed']} scénarios automatisés couvrent : identité texte/hash/provenance, idempotence, doublons, données invalides, qualité bloquante, erreurs isolées tolérées, déclenchement planifié et SIGKILL, miroir indisponibilité, SQLite occupé, alerte lenteur, permissions, droits et registre B2, ainsi que JSON malformé. Les preuves détaillent les cas sans les confondre avec le corpus réel."
)
p(
    "Versions : Python "
    + B["environment"]["python"]
    + ", SQLite "
    + TEST["environment"]["sqlite"]
    + ". Les hashes de fichiers et la distinction entre la release figée et la version finale du code sont dans Preuves/Manifest.json. Les sorties ne constituent pas des labels NER ni une validation humaine. Le coordinateur a également importé et réindexé les 21 676 articles dans B2, avec vérification complète des textes et métadonnées."
)
page("Captures d’exécution et monitoring")
p(
    "La vidéo montre une capture de navigateur réelle et continue : reprise d’un jeu synthétique de 80 articles, puis import de 21 676 articles TASS. La panne intervient au record 24 ; le checkpoint conservé est 20. Les pauses de lisibilité sont documentées, sans servir à mesurer les performances."
)
picture(
    "Capture_corpus.png",
    "Figure 2. Tableau local après l’import réel ; le run synthétique et son alerte restent visibles.",
)
h("Interpréter le tableau", 2)
p(
    "Actualisation : une seconde. Le débit du tableau mesure le traitement en transaction ; le benchmark inclut toute l’exécution. La fraîcheur est le temps depuis le dernier changement de statut. Le compteur de tentatives permet d’identifier la reprise ; les alertes conservent date, code et run sans texte d’article."
)
p(
    "Preuves : Demonstration_locale_pipeline.mp4, Preuves/Video_description.json, Video_execution.jsonl et Capture_reprise.png. Le serveur et le navigateur d’essai sont arrêtés après la capture. La vidéo prouve l’exécution locale, pas une disponibilité de production externe."
)
page("Documentation d’utilisation")
h("Rejouer sur un poste macOS ou Linux", 2)
p(
    "Extraire Code_OSINT_Bloc3.zip dans un dossier accessible. Python 3.12 ou ultérieur suffit. La fixture synthétique est incluse, le corpus réel et les données d’état sont exclus."
)
code(
    "python3 -m pipeline schedule --config config/portable.json \\\n  --first-delay 2\npython3 -m pipeline status --state .state-portable\npython3 -m pipeline serve --state .state-portable --port 18743\npython3 tests/integration.py"
)
p(
    "Ouvrir http://127.0.0.1:18743 puis arrêter par Ctrl+C après consultation. Le planificateur sort après un cycle par défaut. La prochaine échéance est durable : utiliser worker pour un import immédiat ; une planification continue doit être demandée explicitement par --cycles 0."
)
h("Configuration et sorties", 2)
table(
    ["Élément", "Usage"],
    [
        ["config/portable.json", "Chemins relatifs ; fixture 5 articles ; seuil zéro rejet."],
        [
            "config/corpus_clean.json",
            "Chemins du poste Mémoire ; corpus réel et registre de suppressions B2.",
        ],
        [".state/pipeline.sqlite", "Journal des runs, staging, rejets et tombstones."],
        [".state/current.json", "Pointeur et empreintes de la release active."],
        ["published/ et mirror/", "Deux formats, copie locale, manifestes."],
        ["events.jsonl, alerts.jsonl", "Diagnostic de traitement et alertes locales."],
    ],
    [150, 330],
)
h("Dépanner sans détruire le point de reprise", 2)
p(
    "Lire l’alerte et le run concerné. Une indisponibilité temporaire peut être absorbée automatiquement. Une donnée malformée exige une source corrigée, avec nouvelle empreinte. Ne pas supprimer SQLite ou son WAL pour relancer. Si le primaire publié manque, export retourne le miroir vérifié ; si les deux sont perdus, une restauration ou un retraitement contrôlé est nécessaire."
)
p(
    "Dockerfile et Compose ont été testés localement, avec utilisateur non privilégié, source en lecture seule et réseau coupé. Les cas UID sans /etc/passwd et SQLite sans espace temporaire ont été corrigés. Le tmpfs /tmp est borné à 64 Mo. Une reprise au checkpoint 21 676 publie les 21 676 articles ; preuve Docker_B3_reprise.log."
)
page("Conclusion, soutenance et sources")
h("Résultat actuel", 2)
p(
    "Le prototype importe le corpus réel, conserve une filiation vérifiable et publie des textes stables après validation. Les scénarios de panne montrent une reprise autonome au dernier lot validé. Les alertes et la lecture sur un miroir sont observables. Le plan documentaire et la progression pédagogique de Books ont été conservés, avec un code réorganisé pour le besoin OSINT."
)
h("Limites à défendre", 2)
p(
    "Les protections sont locales et l’ingestion n’est pas redondante entre plusieurs hôtes. Les exports B3 ne sont pas chiffrés au repos. Compose est vérifié localement, sans conteneur permanent après essai. Le parcours complet des demandes de droits et la validation de la base légale doivent être coordonnés avec B1/B2/B4. Le NER et les annotations humaines ne sont pas prouvés par ce bloc. Les critères d’oral demandent une prestation réelle."
)
h("Cinq minutes de présentation", 2)
table(
    ["Temps cible", "Preuve à montrer"],
    [
        ["0:00 à 1:30", "Besoin, source, schéma et contrat figé."],
        ["1:30 à 2:30", "Contrôle qualité avant publication ; extrait transactionnel."],
        ["2:30 à 3:35", "Vidéo de reprise, puis parcours du corpus réel."],
        ["3:35 à 4:20", "Mesures et indicateurs, avec leurs périmètres."],
        ["4:20 à 5:00", "Droits, limites et résultat vérifié."],
    ],
    [105, 375],
)
h("Sources et crédits", 2)
p(
    "Grille remise : RNCP38777, Bloc 3!A6:A38 (33 critères). Consignes du directeur : plan pipeline, code et capture vidéo, 5 minutes de présentation et 15 minutes de questions. Cours Data Pipelines for AI de Matthieu Larboullet : p. 6 à 12, 17 à 21, 25 à 30. Modèle documentaire : livrable Books d’Edouard Cappaert, 02/06/2026, huit pages. Le cours AI Deployment p. 22 et la reconstitution N04 motivent le nettoyage minimal."
)
p(
    "Références techniques : sqlite.org/atomiccommit.html ; sqlite.org/wal.html ; docs.python.org/3/library/os.html, consultées le 04/10/2026. L’adaptation OSINT et ses documents ont été préparés avec l’assistance de Codex ; la relecture et la maîtrise personnelles d’Edouard restent à exercer. Aucun crédit historique n’est attribué à une contribution nouvelle sans preuve.",
    "SmallText",
)
SimpleDocTemplate(
    str(ROOT / "Plan_pipeline_OSINT.pdf"),
    pagesize=(595.28, 841.89),
    leftMargin=48,
    rightMargin=47,
    topMargin=47,
    bottomMargin=46,
    title="Plan pipeline OSINT - Bloc 3",
    author="Edouard Cappaert",
).build(flow, onFirstPage=footer, onLaterPages=footer)
(ROOT / "Plan_pipeline_OSINT.md").write_text(
    "# Plan pipeline OSINT, Bloc 3\n\n" + "\n".join(md), encoding="utf-8"
)
