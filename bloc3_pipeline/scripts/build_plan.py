"""Generate the OSINT pipeline PDF and editable Markdown."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, Rect, String
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
    canvas.drawString(48, 27, "Mémoire OSINT | Pipeline de données | Bloc 3")
    canvas.drawRightString(547, 27, str(doc.page))
    canvas.restoreState()


FINAL = ROOT / "Preuves/Collecte_TASS"
bench = json.loads((FINAL / "Benchmark_chiffre.json").read_text())
cycle = json.loads((FINAL / "Cycle_volume_chiffre.json").read_text())
volume_file = FINAL / "Volume_chiffre.json"
volume = (
    json.loads(volume_file.read_text())
    if volume_file.exists()
    else {"encrypted_volume": False, "status": "Mot de passe et migration à réaliser"}
)
flow.append(Spacer(1, 60))
p("MÉMOIRE OSINT", "Sub")
p("Livrable", "TitleRed")
p("Pipeline de données pour l’IA", "Sub")
p("Collecte TASS et corpus historique", "Sub")
table(
    ["Repère", "Version présentée"],
    [
        ["Auteur", "Edouard Cappaert"],
        ["Code", "Code_OSINT_Bloc3.zip et dépôt GitHub memoire-osint"],
        ["Date", "04/10/2026"],
        [
            "Statut",
            "Application locale testée, collecte réseau bornée et essais fictifs identifiés",
        ],
    ],
    [110, 370],
)
p(
    "Les preuves distinguent corpus historique, collecte réelle et fixtures synthétiques. La soutenance personnelle et la validation du jury restent à observer.",
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
    "Prévu : préparé sans exécution observée. Implémenté : présent dans le code. Testé : scénario exécuté et rattaché à une version. Démontré au jury dépend de la prestation réelle. Les 33 critères exacts de Bloc 3!A6:A38 sont reliés à leur preuve dans Correspondance_criteres_Bloc3.json."
)
p(
    "La chaîne locale automatise découverte, téléchargement, validation, publication et suivi après le déclenchement du formulaire. L’import dans B2 est une action explicite sur une sélection validée. Le bloc 4 conserve ses modèles ; choisir une période ne déclenche pas un entraînement."
)
page("Introduction et analyse des données")
h("Contexte et problématique", 2)
p(
    "La cellule fictive de veille documentaire recherche des mentions WEAPON, MIL_UNIT et MIL_ORG. Le pipeline prépare des textes stables pour l’architecture B2 et l’inférence B4. Il doit tolérer les erreurs isolables, préserver la dernière publication valide et reprendre sans perte ni doublon."
)
h("Deux sources identifiées", 2)
p(
    "Le corpus historique provient du JSON fourni : 21 742 entrées brutes, 66 textes vides rejetés et 21 676 textes nettoyés. L’extension découvre les URLs sur les rubriques publiques TASS anglais, puis extrait le corps et les métadonnées des pages d’articles. Le catalogue observé avant finalisation compte 21 681 articles après cinq nouveaux articles réels."
)
p(
    "La pagination /userApi/categoryNewsList est le point d’entrée utilisé par les pages du site ; ce n’est pas une API publique contractuelle. Les bornes portent sur la date de publication UTC, avec début et fin inclusifs. La couverture dépend des archives accessibles, des pages et de la limite d’articles."
)
table(
    ["Champ", "Contrat"],
    [
        ["id, date, URL", "Identifiant conservé, epoch et date lisible UTC, URL HTTPS TASS."],
        [
            "title, text",
            "Titre et corps éditorial ; pas d’images, profils ou coordonnées collectés séparément.",
        ],
        ["text_sha256", "Empreinte du texte UTF-8 exact utilisé pour les offsets."],
        [
            "provenance, version",
            "Source, exécution, normalisation, date de collecte et empreinte de révision.",
        ],
        ["offset_unit", "unicode_codepoint ; intervalle start inclus, end exclu."],
    ],
    [120, 360],
)
page("Schéma du pipeline et stack technique")
d = Drawing(480, 210)
boxes = [
    (12, 140, "TASS / JSON fourni", "découverte, provenance"),
    (174, 140, "Extraction et qualité", "texte, date, erreurs"),
    (336, 140, "Catalogue validé", "SQLite et versions"),
    (336, 45, "JSON et JSONL", "sélection temporelle"),
    (174, 45, "B2 puis inférence B4", "import explicite"),
    (12, 45, "Suivi et secours", "logs, lecture seule"),
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
            fontSize=8.5,
            fillColor=C,
        )
    )
    d.add(
        String(
            x + 66, y + 15, b, textAnchor="middle", fontName="Helvetica", fontSize=8, fillColor=G
        )
    )
for x1, y1, x2, y2 in [
    (144, 166, 174, 166),
    (306, 166, 336, 166),
    (402, 140, 402, 97),
    (336, 71, 306, 71),
    (174, 71, 144, 71),
]:
    d.add(Line(x1, y1, x2, y2, strokeColor=C, strokeWidth=1.4))
flow.append(d)
md.append(
    "Schéma : TASS / JSON fourni → extraction → qualité → catalogue versionné → JSON/JSONL → import B2 → inférence B4. Suivi, droits et secours accompagnent chaque étape.\n"
)
h("Séparation des responsabilités", 2)
p(
    "Python 3.12 et sa bibliothèque standard : source pour accès et extraction, store pour persistance, worker pour checkpoints et publication, service pour interface et supervision, rights/security/resilience pour les contrôles transversaux. SQLite est un catalogue local ; PostgreSQL et MongoDB restent les stockages métier B2."
)
p(
    "Le serveur écoute sur 127.0.0.1, vérifie l’hôte et protège les commandes par session CSRF. Les textes et exports gérés sont destinés au volume chiffré. Une copie SQLite cohérente et vérifiée maintient la lecture en cas de panne du catalogue principal ; les écritures sont alors bloquées."
)
page("Code principal et reprise automatique")
h("Checkpoints persistants", 2)
p(
    "La découverte enregistre URLs et curseur ; chaque article téléchargé possède un statut durable. Une interruption permet de reprendre les seules unités restantes. Le superviseur relance automatiquement un worker détruit, avec trois tentatives au maximum. L’arrêt volontaire reste une pause manuelle."
)
code(
    'with database(state) as db, db:\n    db.execute("UPDATE tasks SET status=?,payload=? "\n               "WHERE job_id=? AND url=?",\n               (status, normalized_payload, key, url))\n# worker.py : aucun déplacement du checkpoint avant persistance.'
)
h("Qualité avant activation", 2)
p(
    "Le taux de rejet maximal du collecteur est configurable, 20 % par défaut. Il s’agit d’un choix du projet. Si le contrôle bloque un lot, la dernière publication valide est conservée. Les formats JSON et JSONL proviennent du même instantané transactionnel. Le seuil historique de 0,5 % concerne l’import de fichiers."
)
table(
    ["Scénario", "Preuve actuelle"],
    [
        ["Erreur HTTP", "Nouvelles tentatives bornées, rejet isolé et alerte conservée."],
        [
            "Worker détruit",
            "Processus relancé automatiquement ; checkpoints réutilisés sans doublon.",
        ],
        ["Recollecte", "Articles inchangés évités, révisions distinctes conservées."],
        ["Droits", "Correction persistante et suppression prioritaires sur la recollecte."],
    ],
    [130, 350],
)
p(
    "Preuves : Tests_collecte_final.log, Tests_cloture_final.log et Frontend_tests.log. Les fixtures servent aux pannes et aux droits ; elles ne constituent pas des faits journalistiques.",
    "SmallText",
)
page("Problèmes rencontrés, droits et sécurité")
table(
    ["Point", "Réponse vérifiée ou limite"],
    [
        [
            "Failed to fetch persistant",
            "Le bandeau disparaît après reconnexion ; aucune commande incertaine n’est rejouée automatiquement.",
        ],
        [
            "Rectification",
            "Texte normalisé, nouvelle empreinte, anciennes versions incorrectes purgées et décision prioritaire sur les futurs imports.",
        ],
        [
            "Suppression",
            "Catalogue, tâches, versions, exports gérés et secours purgés ; checkpoint WAL et compactage SQLite.",
        ],
        [
            "Stockage indisponible",
            "Consultation et export du dernier catalogue validé ; collecte et import B2 bloqués.",
        ],
        [
            "Incidents",
            "Signal de permissions et d’intégrité, confinement et dossier d’exercice fictif relié à I01.",
        ],
    ],
    [125, 355],
)
h("Protection au repos", 2)
p(
    "Le lanceur exige le volume macOS chiffré AES-256 et ne crée aucun état en clair si le volume est fermé. État observé : "
    + (
        (
            "volume activé, migration et cycle arrêt, démontage, déverrouillage personnel et relance vérifiés. Les 21 701 articles, tables et exports sont conservés par empreinte. Démarrage strict refusé lorsque le volume est fermé (Cycle_volume_chiffre.json)."
            if cycle.get("complete")
            else "volume activé et migration vérifiée. Arrêt et relance observés, mais démontage refusé : Docker garde des fichiers B4 ouverts sur le volume. Le cycle complet reste à vérifier (Cycle_volume_chiffre.json)."
        )
        if volume.get("encrypted_volume")
        else "préparation disponible ; saisie personnelle du mot de passe et migration à terminer."
    )
)
h("Traçabilité et coordination", 2)
p(
    "Consultations, exports et droits enregistrent compte système, date, résultat et références opaques, sans texte, secret ou mots-clés libres. Le compte du serveur ne distingue pas des personnes partageant une session. Les journaux gérés sont purgés au-delà de six mois calendaires ; les décisions actives de droits sont séparées."
)
p(
    "La fixture Droits_B3_B2.json vérifie correction, purge et refus de réimport dans SQL/Mongo/index. Les annotations, sources historiques et copies déjà téléchargées ailleurs demandent une coordination. Aucun effacement physique garanti d’un SSD ni validation juridique n’est revendiqué."
)
page("Analyse des données et résultats mesurés")
table(
    ["Catalogue initial", "Articles ajoutés", "Médiane", "Articles/s", "Minimum / maximum"],
    [
        [
            "Vide" if r["mode"] == "empty" else "21 701 articles",
            r["articles"],
            f"{r['median_s']:.2f} s",
            f"{r['median_articles_per_second']:.1f}",
            f"{r['min_s']:.2f} / {r['max_s']:.2f} s",
        ]
        for r in bench["summary"]
    ],
    [105, 80, 80, 65, 150],
)
p(
    "18 exécutions sur le même volume APFS AES-256, trois répétitions par taille et catalogue. Copies isolées du catalogue rempli, corps HTML fictifs d’environ 1, 10 et 50 Kio. Préparation des copies exclue ; découverte, extraction, checkpoints, exports et copie de secours inclus. Comptes, empreintes et égalité JSON/JSONL vérifiés. Détail, dispersion et volumes : Benchmark_chiffre.json.",
    "CaptionText",
)
h("Interprétation", 2)
p(
    "La publication recopie le catalogue entier vers le secours : son coût fixe pénalise les petits lots. Les durées et débits sont à comparer entre tailles et catalogues ; aucun seuil d’absence de ralentissement significatif n’est fixé par la grille. Poste partagé, caches non neutralisés, collecte bornée à 2 000 candidats. Sans réseau ni mesure isolée du coût du chiffrement. Les anciens benchmarks restent historiques."
)
h("Qualité et archives", 2)
p(
    "Le corpus historique est identifié par empreinte ; les textes normalisés conservent les IDs, dates et offsets. Les vérifications réseau sont bornées et séparées dans Reseau_final.json. Une période vide ou une limite atteinte ne prouve pas l’absence d’autres publications. Les mentions extraites reflètent le corpus éditorial, pas un inventaire militaire réel."
)
p(
    "Les tests de restauration utilisent une ancienne copie fictive et vérifient l’application des droits avant retour à la lecture. La continuité démontrée porte sur la lecture locale ; la collecte ne continue pas en cas de défaillance du stockage principal."
)
page("Captures d’exécution et monitoring")
p(
    "La vidéo actualisée montre une exécution de l’interface, ses compteurs, les événements et le passage en lecture de secours après une panne de catalogue simulée. Le type de données, la version et les événements sont explicités dans Video_cloture.json. La démonstration fictive reste distincte des vérifications TASS réelles."
)
image = FINAL / "Cloture_suivi.png"
if image.exists():
    picture(
        "Collecte_TASS/Cloture_suivi.png",
        "Figure 2. Suivi dans l’interface actuelle ; nature fictive de la démonstration identifiée.",
    )
h("Indicateurs et extension", 2)
p(
    "Actualisation chaque seconde : découvert, téléchargé, validé, nouveau, modifié, inchangé, filtré, supprimé, rejeté, durée, débit, tentatives, étape et dernière activité. Le statut indique aussi backend, fraîcheur du secours et sécurité. Les événements stage_duration ajoutent les durées par étape sans modifier le contrat des articles."
)
p(
    "Une alerte SLOW_ARTICLE est déclenchée par franchissement d’un seuil configurable. SECURITY_PERMISSIONS signale et contient des droits trop ouverts ; CATALOG_INTEGRITY signale la bascule. Les alertes restent locales, sans destinataire externe. Preuves : Tests_cloture_final.log et Incident_simule.json."
)
page("Documentation d’utilisation")
h("Application personnelle sur le Mac", 2)
p(
    "Préparer Preparer_volume_chiffre.command dans Terminal, saisir le mot de passe, puis ouvrir Lancer_Observatoire_TASS.command. Le service doit être arrêté pendant migration et restauration. Le lanceur garde un pointeur privé vers l’état chiffré."
)
code(
    "python3 -m pipeline collect-ui --state /Volumes/MemoireOSINT/B3 \\\n  --require-encrypted --slow-article-seconds 10 --open\npython3 -m pipeline collect-check-security \\\n  --state /Volumes/MemoireOSINT/B3 --require-encrypted\npython3 -m pipeline collect-restore --state /Volumes/MemoireOSINT/B3"
)
h("Collecte, consultation et droits", 2)
p(
    "Choisir rubrique, période UTC, mots-clés OU et limite. La limite concerne les candidats vérifiés, même déjà connus. Le catalogue publie automatiquement après qualité ; Importer dans B2 est une action explicite. Les fichiers JSON/JSONL téléchargés en dehors du volume redeviennent des copies sous responsabilité de leur destinataire."
)
code(
    "python3 -m pipeline collect-rectify ID --request-ref DOSSIER-001 \\\n  --changes /Volumes/MemoireOSINT/correction.json \\\n  --state /Volumes/MemoireOSINT/B3 --propagate-b2\npython3 -m pipeline collect-erase ID --request-ref DOSSIER-002 \\\n  --state /Volumes/MemoireOSINT/B3 --propagate-b2"
)
p(
    "Une erreur de propagation B2 conserve un état d’échec et peut être rejouée. Le mode de secours bloque les modifications ; restaurer hors serveur après diagnostic. Pour reproduire sur Linux, utiliser exclusivement les fixtures et suivre Collecte_TASS.md ; l’outil de volume est propre à macOS."
)
page("Conclusion, soutenance et sources")
h("Résultat et limites", 2)
p(
    "La collecte, la qualité, les versions, la reprise et le suivi sont implémentés. Les droits sont testés jusqu’à B2 sur une fixture ; la lecture de secours et la restauration sont vérifiées. Le volume chiffré et la migration sont décrits par leur état de preuve réel, sans confondre préparation et activation."
)
p(
    "La machine demeure un domaine unique de panne. Le miroir maintient la lecture mais ne constitue pas une haute disponibilité complète. Les archives TASS peuvent être partielles. L’import B2 conserve une commande explicite et B4 requiert une inférence sur le texte identifié, sans réentraînement automatique."
)
table(
    ["Temps", "Preuve à expliquer"],
    [
        ["0:00 à 0:45", "Besoin, source TASS et bornes UTC."],
        ["0:45 à 1:45", "Diagramme, contrat du texte et séparation B2/B4."],
        ["1:45 à 3:00", "Qualité, logs et reprise au checkpoint."],
        ["3:00 à 4:20", "Monitoring, benchmark et lecture de secours."],
        ["4:20 à 5:00", "Droits, protection et limites observées."],
    ],
    [100, 380],
)
p(
    "Les huit critères d’oral restent prévus jusqu’à une répétition réelle. Questions : comment éviter la réintroduction d’un texte corrigé ? Que continue-t-on lors d’une panne SQLite ? Pourquoi un nouveau corpus ne demande-t-il pas un nouvel entraînement ?"
)
p(
    "Sources : grille fournie RNCP38777, Bloc 3!A6:A38 ; consignes du directeur ; code et preuves de cette version. Dépôt : https://github.com/edcdataworker/memoire-osint. Les documents descriptifs ne remplacent pas les tests OSINT.",
    "SmallText",
)
SimpleDocTemplate(
    str(ROOT / "Plan_pipeline_OSINT.pdf"),
    pagesize=(595.276, 841.89),
    rightMargin=48,
    leftMargin=48,
    topMargin=48,
    bottomMargin=45,
    title="Pipeline TASS et corpus historique",
    author="Edouard Cappaert",
).build(flow, onFirstPage=footer, onLaterPages=footer)
(ROOT / "Plan_pipeline_OSINT.md").write_text("# Plan pipeline OSINT, Bloc 3\n\n" + "\n".join(md))
