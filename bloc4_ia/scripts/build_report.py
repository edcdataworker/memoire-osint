"""Build the academic report from measured artifacts and actual screenshots."""

import json
import re
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image,
)

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / name).read_text())


train = load("Preuves/training_run.json")
bench = load("Preuves/benchmark.json")
ci = load("Preuves/ci_local.json")
full = load("Preuves/inference_full.json")
count = load("Preuves/corpus_predictions_summary.json")
diagnostic = load("Preuves/Diagnostic_annotations_IA_42_articles.json")
assert diagnostic["model_sha256"] == full["model_sha256"], "Diagnostic/model mismatch"
assert diagnostic["documents"] == 42 and diagnostic["global"]["support"] == 254
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="TitleX",
        fontName="Helvetica-Bold",
        fontSize=29,
        leading=35,
        textColor=colors.HexColor("#173b50"),
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="HeadX",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=23,
        textColor=colors.HexColor("#173b50"),
        spaceAfter=13,
    )
)
styles.add(
    ParagraphStyle(
        name="SubX",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=17,
        textColor=colors.HexColor("#173b50"),
        spaceBefore=12,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(name="BodyX", fontName="Helvetica", fontSize=10.6, leading=15.5, spaceAfter=10)
)
styles.add(
    ParagraphStyle(
        name="SmallX",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#50616f"),
        spaceAfter=8,
    )
)
story = []


def p(text, style="BodyX"):
    # Keep exact artifact paths and URLs while spacing surrounding prose.
    protected = {}

    def protect(match):
        key = "@@FILE" + chr(65 + len(protected)) + "@@"
        protected[key] = match.group()
        return key

    text = re.sub(r"\S*[_/]\S*", protect, text)
    text = re.sub(r"(?<=[a-zà-ÿ])(?=\d)", " ", text)
    text = re.sub(r"(?<=\d)(?=[a-zà-ÿ])", " ", text)
    for key, original in protected.items():
        text = text.replace(key, original)
    story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles[style]))


def heading(text):
    p(text, "HeadX")


def sub(text):
    p(text, "SubX")


def page():
    story.append(PageBreak())


def table(rows, widths=None):
    data = [[Paragraph(escape(str(v)), styles["SmallX"]) for v in row] for row in rows]
    t = Table(data, colWidths=widths or [240, 240], repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5edf2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173b50")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#b7c5cf")),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))


def img(path, width=475, maxh=380):
    from PIL import Image as PILImage

    if not Path(path).exists():
        return
    w, h = PILImage.open(path).size
    scale = min(width / w, maxh / h)
    story.append(Image(str(path), width=w * scale, height=h * scale, hAlign="LEFT"))
    story.append(Spacer(1, 10))


def footer(c, doc):
    c.setStrokeColor(colors.HexColor("#173b50"))
    c.setLineWidth(0.6)
    c.line(54, 49, 541, 49)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#50616f"))
    c.drawString(54, 35, "Edouard Cappaert | Mémoire OSINT | Bloc 4 | 4 octobre 2026")
    c.drawRightString(541, 35, str(doc.page))


p("Solution d’intelligence artificielle\nMémoire OSINT", "TitleX")
p("Solution IA OSINT sur le corpus TASS", "HeadX")
story.append(Spacer(1, 30))
p(
    "Extraction de mentions WEAPON, MIL_UNIT et MIL_ORG\nDéveloppement, déploiement et exploitation locale",
    "SubX",
)
p("Edouard Cappaert\nMSc 2025-2026", "BodyX")
sub("État de la solution livrée")
p(
    f"{full['documents']:,} articles traités localement. Modèle spaCy à supervision faible. Infrastructure de démonstration raccordée aux Blocs 2 et 3. Modèle NER opérationnel ; évaluation exploratoire sur une référence générée par IA.".replace(
        ",", " "
    )
)
p(
    "Les textes sont issus de TASS. Ce dossier local ne constitue ni une publication du corpus ni une validation des faits rapportés.",
    "SmallX",
)
page()
heading("Sommaire et contexte")
table(
    [
        ["Partie", "Page"],
        ["Introduction et besoins", "2"],
        ["Pipeline et modèle", "3"],
        ["Dashboard et passage source", "4"],
        ["Elasticsearch et Kibana", "5"],
        ["Métriques et choix techniques", "6"],
        ["Automatisation et livraison", "7"],
        ["Sécurité, accessibilité et droits", "8"],
        ["Note d’analyse et références", "9"],
    ],
    [380, 100],
)
sub("1. Introduction")
p(
    "Le projet facilite la recherche de mentions militaires dans 21 676 articles anglophones du corpus TASS. La source présente un cadrage éditorial spécifique. L’outil conserve les passages permettant de contrôler chaque prédiction et de la confronter à d’autres sources."
)
sub("1.1 Problématique")
p(
    "Comment automatiser la localisation de mentions militaires sourcées tout en rendant visibles les erreurs possibles, les versions utilisées et le niveau réel de validation ?"
)
sub("1.2 Utilisateurs et accessibilité")
p(
    "Camille, analyste de veille, recherche un terme, filtre une période puis vérifie un passage. Alex, responsable de cellule, contrôle l’origine des chiffres et l’état du modèle avant utilisation. Ces personas hypothétiques servent à définir les besoins et le parcours de la plateforme."
)
p(
    "Le parcours comporte six étapes : lire le statut, filtrer, comparer les volumes, ouvrir un article, consulter la source, proposer une correction documentée. Les formulaires sont étiquetés, le focus visible, les résultats lisibles dans des tableaux et le texte agrandissable. Les contrôles réalisés et leurs limites figurent page 8."
)
page()
heading("2. Pipeline technique et modèle")
table(
    [
        ["Étape", "Implémentation et preuve"],
        ["Données", "Contrat B3 schéma 1, ID/date/URL/texte/empreinte. Aucun renettoyage."],
        ["Préannotation", "Règles lexicales locales, supervision faible."],
        [
            "Séparation",
            "Groupes ID/URL/texte canonique/titre ; 240 train, 60 dev, diagnostic IA sur 42 articles de test.",
        ],
        [
            "Entraînement",
            "spaCy 3.8.7, NER vierge, trois labels, graine 42, six époques, dropout 0.2, lots de 16.",
        ],
        [
            "Inférence",
            "Texte complet, offsets Unicode, source, hash texte et modèle. Articles sans entités conservés.",
        ],
        [
            "Restitution",
            "Index de mentions distinct dans Elasticsearch TLS, dashboard Kibana et UI locale accessible.",
        ],
    ],
    [115, 365],
)
sub("2.1 Annotation et séparation")
p(
    "WEAPON couvre les systèmes nommés. MIL_UNIT couvre les unités nommées ou numérotées, flottes incluses. MIL_ORG couvre les organisations militaires de haut niveau. Les positions sont validées strictement, début inclus et fin exclue. La ponctuation sans espace est tokenisée sans changer les caractères source."
)
p(
    "Les 27 000 paires entre train, dev et test élargi ne présentent ni groupe commun ni doublon au seuil Jaccard de 0,8 : maximum 0,374. Cette vérification ne garantit pas l’indépendance sémantique de récits d’un même événement. La référence IA conserve sept articles sans mention proposée."
)
sub("2.2 Méthode d’entraînement")
p(
    "Le modèle apprend à repérer WEAPON, MIL_UNIT et MIL_ORG à partir de règles lexicales, en supervision faible. Le contrôle complémentaire par IA porte sur 42 articles réservés au test, dont 24 ajoutés par sélection déterministe en trois classes de longueur."
)
p(
    'L’entraînement utilise un pipeline anglais initialisé avec spacy.blank("en"), auquel est ajouté le composant NER. Ses poids sont initialisés aléatoirement, puis ajustés sur les 240 articles d’entraînement. La configuration, les DocBin et le modèle sont livrés avec leurs empreintes.',
    "SmallX",
)
page()
heading("3. Dashboard et passage source")
img(ROOT / "Preuves/captures/dashboard_full.png", maxh=360)
p(
    "Capture réelle de l’interface locale, reliée au modèle livré. Les nombres affichés comptent des prédictions expérimentales. Les articles et mentions disposent de dénominateurs distincts.",
    "SmallX",
)
p(
    "Le filtre d’année UTC s’applique aux tops, aux volumes et à la liste d’articles. Un filtre de label agit sur les mentions et le classement, tandis que le compteur d’articles avec entités reste explicitement tous labels. Les graphies différentes ne sont pas fusionnées sans règle justifiée."
)
p(
    "L’ouverture d’un article restitue le texte complet, les mentions surlignées, la catégorie et les offsets. Le lien TASS permet de revenir à la source. Le NER ne fournit pas de raisonnement interne lisible : l’explication proposée porte sur le passage détecté, la tâche et ses limites."
)
p(
    "L’interface ne prétend ni calibrer une confiance de prédiction ni garantir l’exactitude d’un nom. Le code utilise textContent pour afficher les chaînes non fiables, et le serveur est limité à la lecture sur127.0.0.1.",
    "SmallX",
)
page()
heading("4. Elasticsearch et Kibana")
kib = ROOT.parent / "00_Pilotage/Integration_transversale/Preuves/Kibana_corpus_complet.png"
if not kib.exists():
    kib = ROOT.parent / "00_Pilotage/Integration_transversale/Preuves/Kibana_500.png"
img(kib, maxh=360)
p(
    "Capture réelle Kibana du corpus complet : 39 511 mentions expérimentales. Les objets exportés sont dans 00_Pilotage/Integration_transversale/Preuves/Kibana_OSINT.ndjson.",
    "SmallX",
)
p(
    "L’index osint-entities-v1 contient une occurrence par document, avec ID de l’article, date epoch, texte exact de l’entité, label, offsets, empreinte de texte et de modèle. Il préserve l’index chiffré des articles du Bloc2. Le mapping strict évite un changement silencieux de schéma."
)
p(
    "Le tableau de labels présente la distribution des prédictions, le top classe les graphies observées, et la série temporelle suit les mentions datées. Le filtrage temporel porte sur chaque occurrence. L’import utilise TLS et un rôle d’écriture limité au nouvel index."
)
p(
    "La compatibilité de format, le contrôle des spans, l’import et la suppression d’une fixture sont des preuves d’intégration. Ils ne transforment pas les annotations faibles en vérité de référence.",
    "SmallX",
)
page()
heading("5. Métriques et justification des choix")
table(
    [
        ["Mesure de fonctionnement", "Résultat observé"],
        ["Entraînement 240 articles / 6 époques", f"{train['duration_seconds']} s, CPU local"],
        ["Inférence complète", f"{full['documents']} articles en {full['seconds']} s"],
        ["Débit complet", f"{full['documents_per_second']} articles/s"],
        [
            "Mémoire maximale du processus",
            f"{full['max_rss_bytes_macos'] / 1048576:.1f} MiB (macOS ru_maxrss)",
        ],
        ["Mentions prédites", str(count["mentions"])],
        ["Articles avec prédiction", str(count["articles_with_entities"])],
        [
            "Diagnostic sur 42 articles (référence IA)",
            f"Précision {diagnostic['global']['precision'] * 100:.2f} % / rappel {diagnostic['global']['recall'] * 100:.2f} % / F1 {diagnostic['global']['f1'] * 100:.2f} %".replace(
                ".", ","
            ),
        ],
    ],
    [260, 220],
)
sub("5.1 Ce que les métriques permettent de dire")
p(
    "Le débit et la mémoire décrivent cette exécution sur ce poste, avec un processus et un thread numérique. Les essais10, 50 et 200 articles se situent autour de80 articles/s. Ils ne prouvent aucun SLA multi-utilisateur. Des entrées vides, mal typées ou supérieures à100 000 caractères sont rejetées. Un texte bruité et un texte long de40 000 caractères ont été traités, sans mesure de justesse sur ces perturbations."
)
sub("5.2 Évaluation exploratoire par IA")
p(
    "Le scorer exige le même label et les deux frontières exactes, calcule précision, rappel et F1 micro et par label, puis exporte les erreurs. Les dénominateurs nuls donnent null. Les labels dev issus des mêmes règles ne produisent aucun score de qualité annoncé. Les résultats des tests unitaires synthétiques vérifient seulement les formules."
)
p(
    "La référence Codex comprend 254 mentions sur 42 articles de test : 54 vrais positifs, 22 faux positifs et 200 faux négatifs. Le F1 est de 32,73 %. Les 24 textes ajoutés couvrent trois classes de longueur, sans sélection par prédiction ; leurs propositions ont été figées avant l’inférence. Le diagnostic initial sur 18 textes reste à 44,93 %. Le changement de référence explique cet écart, sans modification du modèle. Les erreurs IA et l’échantillonnage limitent l’extrapolation.",
    "SmallX",
)
page()
heading("6. Réentraînement, dérive et livraison")
sub("6.1 Déclenchement réellement exécuté")
p(
    "L’ordonnanceur surveille les empreintes des jeux. Un lot de24 articles déclenche un candidat en2,865s, puis le cycle inchangé est ignoré. Une modification à25 articles déclenche un second candidat. Ce sont des essais de mécanisme à supervision faible. Le mode normal exige les annotations revues."
)
p(
    "Le registre conserve les versions et refuse automatiquement la production lorsque les conditions de provenance et de qualité ne sont pas remplies. Le diagnostic IA reste distinct des scores utilisés pour la promotion. Le retour arrière est vérifié dans l’environnement de démonstration. Les erreurs produisent un journal et une alerte locale, et un code de sortie non nul. Un verrou abandonné après SIGKILL nécessite la procédure opérateur documentée."
)
sub("6.2 Distribution et qualité")
p(
    "La divergence Jensen-Shannon compare les classes de longueur des textes. Un seuil exploratoire de0,1 produit une demande de revue. Une baisse F1 de0,05 exige des scores comparables sur la même référence admise par le contrôle de qualité. Le diagnostic IA ponctuel ne démontre pas une baisse de qualité dans le temps. Le cas de décalage synthétique teste la réaction, sans prouver une dérive réelle de qualité."
)
sub("6.3 Chaîne locale de livraison")
p(
    f"La chaîne finale a pris{ci['duration_seconds']}s : dépendances, lint, tests, construction wheel, installation isolée, démarrage HTTP, contrôle santé et pointeur atomique. La release précédente est redémarrée pour le test de retour arrière. Les logs identifient le commit et les hashes des wheels."
)
p(
    "Le workflow commun GitHub verification.yml a terminé trois jobs avec succès au commit 02bf729 : contrôles B2, tests B3 et IA, build puis service HTTP éphémère sur données synthétiques. Preuves/GitHub_workflow_final.json identifie le run. Les révisions locales ultérieures ne sont pas attribuées à cette exécution. Le service de contrôle démarre puis s’arrête ; aucune continuité de service public n’est démontrée."
)
sub("6.4 Reproductibilité")
p(
    "Deux entraînements terminés, avec la même graine et les mêmes données, produisent le même hash du modèle dans cet environnement. L’identité inter-plateformes reste à vérifier.",
    "SmallX",
)
page()
heading("7. Sécurité, accessibilité et droits")
sub("7.1 Contrôles techniques")
p(
    "Le serveur écoute en local et en lecture. Les routes, POST, Host distant, injections et requêtes trop longues sont testés ; la CSP limite les scripts et Elasticsearch utilise TLS. Les copies B4 inventoriées, corpus, modèles, annotations, prédictions et archives de remise, ont été migrées vers le volume AES-256 avec contrôle des empreintes et lecture après migration. Les chemins habituels restent des liens. FileVault est désactivé ; les profils navigateur et copies externes ne sont pas couverts. Voir Protection_copies_B4.json."
)
sub("7.2 Accessibilité vérifiée et limites")
p(
    "La matrice Chromium couvre320, 390, 560, 700, 775, 850, 1024, 1280 et 1440 pixels. Le texte est agrandi à125 %, 150 % et 200 %. Les contrôles ont un nom accessible, le focus reste visible et les résultats ont une alternative tabulaire. Cette méthode teste le reflow et l’agrandissement CSS, pas tous les zooms natifs ni les lecteurs d’écran. Aucun test avec utilisateur handicapé n’est déclaré."
)
sub("7.3 Données personnelles et suppression")
p(
    "Les textes publics peuvent contenir des noms de personnes. Les finalités, bases légales, conservation, droits d’usage et droits des personnes renvoient au Bloc1. Leur validation juridique n’est pas remplacée par un test informatique. Aucune certification ISO 27001 n’est revendiquée pour ce prototype académique."
)
p(
    "Les exports et inférences appliquent le registre d’exclusion. La commande locale erase retire un article d’un fichier et écrit un journal. Une suppression complète doit également atteindre les annotations, HTML de revue, stockage navigateur, index, sauvegardes et modèles concernés. Un modèle entraîné sur une donnée retirée doit être bloqué puis réentraîné selon la décision du responsable."
)
sub("7.4 Reproductibilité et remise")
p(
    "Le zip du code exclut les données et secrets. Les artefacts locaux regroupent le modèle et les jeux nécessaires, avec leurs empreintes. Les versions du code et les modalités d’accès figurent dans le complément de remise Publication_et_diagnostic.md.",
    "SmallX",
)
page()
heading("8. Note d’analyse")
sub("Objet : fiabilité d’une analyse de mentions militaires")
p(
    f"Le corpus complet produit{count['mentions']} prédictions sur{full['documents']} articles, dont{count['articles_with_entities']} avec au moins une entité. Ces nombres décrivent la sortie du modèle expérimental. Ils ne quantifient ni des matériels déployés ni des faits militaires établis."
)
p(
    "L’inspection technique de sorties révèle des erreurs visibles : NATO et Pentagon peuvent être classés WEAPON alors que les consignes du projet les rattachent aux organisations. Une distribution globale ou un classement d’armes peut donc être contaminé par des erreurs de label. Les variantes de casse peuvent aussi diviser les comptes d’une même organisation."
)
p(
    "Les volumes temporels combinent les choix éditoriaux de TASS, la couverture du corpus et les erreurs d’extraction. Une hausse de mentions ne permet pas à elle seule de conclure à une hausse réelle de capacité ou d’activité militaire. Une absence de mention détectée ne prouve pas l’absence de l’entité dans les textes ou sur le terrain."
)
p(
    "La décision défendable consiste à utiliser les tableaux pour naviguer vers des passages à vérifier. Une conclusion analytique nécessite revue humaine, recoupement de sources et évaluation adaptée au sous-ensemble étudié. La comparaison de modèles exige une référence figée, contrôlée et un protocole commun. Le diagnostic sur annotations générées par IA reste une mesure exploratoire."
)
sub("Références et éléments vérifiables")
p(
    "Les configurations, jeux d’entraînement et de développement, modèle et journaux d’exécution sont fournis dans les artefacts et preuves du projet. Ils permettent de relier les résultats aux données et au protocole utilisés.",
    "SmallX",
)
p(
    "Sources officielles consultées le4octobre2026 : spaCy, Training Pipelines & Models (https://spacy.io/usage/training) ; EntityRecognizer (https://spacy.io/api/entityrecognizer) ; CNIL, Réutilisation des données (https://www.cnil.fr/fr/assurer-que-le-traitement-est-licite-reutilisation-des-donnees).",
    "SmallX",
)
p(
    "Preuves locales : Preuves/training_run.json, inference_full.json, benchmark.json, Diagnostic_annotations_IA.json, quality_gate.json, retraining_events.jsonl, reproducibility.json, ci_local.json et ci_tests.xml. La matrice Correspondance_criteres_Bloc4.json couvre les41critères exacts.",
    "SmallX",
)
# Normalize accidental joined numeric prose while preserving paths and identifiers.
for flow in story:
    if isinstance(flow, Paragraph):
        pass
SimpleDocTemplate(
    str(ROOT / "Rapport_solution_IA_OSINT.pdf"),
    pagesize=A4,
    rightMargin=54,
    leftMargin=54,
    topMargin=52,
    bottomMargin=65,
    title="Solution IA OSINT",
    author="Edouard Cappaert",
).build(story, onFirstPage=footer, onLaterPages=footer)
print(ROOT / "Rapport_solution_IA_OSINT.pdf")
