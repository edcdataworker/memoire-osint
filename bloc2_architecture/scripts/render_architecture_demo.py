"""Join genuine browser recordings with explicitly identified explanatory cards."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "Preuves/Video_architecture_20261005"
TARGET = ROOT / "Demonstration_architecture_expliquee.mp4"
W, H = 1600, 900
NAVY = "#102b3b"
MUTED = "#5b6e7b"
GREEN = "#13785d"
AMBER = "#a45913"
PAPER = "#f3f6f8"
FONTS = Path("/System/Library/Fonts/Supplemental")


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("Arial Bold.ttf" if bold else "Arial.ttf")), size)


def text(draw, xy, value, size=28, color=NAVY, bold=False):
    bounds = draw.textbbox(xy, value, font=font(size, bold))
    if bounds[2] > W - 18 or bounds[3] > H - 8:
        raise ValueError("Caption exceeds image bounds: " + value)
    draw.text(xy, value, font=font(size, bold), fill=color)


def card(title, subtitle):
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 12), fill=GREEN)
    text(d, (70, 46), "MÉMOIRE OSINT  /  BLOC 2", 22, GREEN, True)
    text(d, (70, 104), title, 48, bold=True)
    text(d, (70, 173), subtitle, 27, MUTED)
    text(d, (70, 850), "Edouard Cappaert  •  5 octobre 2026  •  Démonstration sur le poste local", 19, MUTED)
    return im, d


def box(d, rect, title, lines, color=GREEN):
    x, y, _, _ = rect
    d.rounded_rectangle(rect, radius=15, fill="white", outline="#c7d4db", width=2)
    d.rectangle((x + 22, y + 24, x + 28, y + 61), fill=color)
    text(d, (x + 43, y + 26), title, 29, color, True)
    for i, line in enumerate(lines):
        text(d, (x + 25, y + 85 + i * 39), line, 26)


def arrow(d, points, color):
    d.line(points, fill=color, width=5)
    x, y = points[-1]
    px, py = points[-2]
    if x > px:
        triangle = [(x, y), (x - 13, y - 8), (x - 13, y + 8)]
    elif x < px:
        triangle = [(x, y), (x + 13, y - 8), (x + 13, y + 8)]
    elif y >= py:
        triangle = [(x, y), (x - 8, y - 13), (x + 8, y - 13)]
    else:
        triangle = [(x, y), (x - 8, y + 13), (x + 8, y + 13)]
    d.polygon(triangle, fill=color)


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=width,height,codec_name,codec_type", "-of", "json", str(path)]))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = json.loads((E / "Stockages.json").read_text())
    capture = json.loads((E / "Capture.json").read_text())
    assert all(capture["checks"].values())
    scenes = []

    def save_still(name, im, seconds, label):
        png = E / (name + ".png")
        im.save(png)
        dest = E / (name + ".mp4")
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-t", str(seconds), "-r", "25", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(dest)])
        scenes.append({"file": dest.name, "label": label, "kind": "explanatory_card", "seconds": seconds})

    im, d = card("Un article reste-t-il accessible pendant une panne ?", "Schéma explicatif de l’architecture réellement exécutée dans les séquences suivantes.")
    box(d, (70, 270, 520, 478), "Application HTTPS", ["Accès authentifié", "Lecture de l’article 2035207", "Mode de lecture annoncé"])
    box(d, (650, 245, 1040, 445), "PostgreSQL", ["Identifiants et métadonnées", "Empreinte du contenu", "Autorité structurée"])
    box(d, (1110, 245, 1530, 445), "MongoDB", ["Document JSON et texte", "Contenu chiffré AES-GCM", "Même identifiant et empreinte"])
    box(d, (650, 560, 1120, 750), "Elasticsearch", ["Index dérivé reconstructible", "Dernier instantané disponible", "Secours de lecture"], AMBER)
    arrow(d, [(520, 310), (650, 310)], GREEN)
    arrow(d, [(520, 430), (565, 430), (565, 480), (1320, 480), (1320, 445)], GREEN)
    arrow(d, [(300, 478), (300, 650), (650, 650)], AMBER)
    text(d, (75, 718), "Chemin normal", 25, GREEN, True)
    text(d, (75, 758), "Chemin de secours", 25, AMBER, True)
    text(d, (1180, 580), "3 moteurs", 32, bold=True)
    text(d, (1180, 629), "des rôles distincts", 27)
    text(d, (1180, 688), "1 même article", 32, bold=True)
    save_still("A_schema", im, 12, "Architecture et rôle de chaque stockage")

    im, d = card("La même donnée dans trois stockages", "Résultats de requêtes réelles du 5 octobre 2026, affichés sous une forme lisible.")
    names = [("sql", "PostgreSQL", "article_id"), ("mongo", "MongoDB", "_id"), ("elasticsearch", "Elasticsearch", "_id")]
    for i, (key, title, id_key) in enumerate(names):
        x = 70 + i * 500
        v = data[key]
        box(d, (x, 260, x + 460, 540), title, [f"{id_key} : {v[id_key]}", f"Volume : {v['count']:,}".replace(",", " "), "Empreinte : identique", "Compte de lecture uniquement"])
    text(d, (70, 587), "SHA-256 commun, vérifié par égalité des trois résultats", 28, GREEN, True)
    text(d, (70, 635), data["sql"]["content_sha256"], 25)
    text(d, (70, 699), "MongoDB et l’index conservent le contenu chiffré ; l’application le déchiffre à la lecture.", 26)
    text(d, (70, 749), "Ce volume décrit les articles stockés. Il ne mesure pas la qualité du modèle NER.", 25, MUTED)
    save_still("B_stockages", im, 15, "Requêtes réelles, identifiant et empreinte communs")

    def browser_scene(name, title, line1, line2):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, W, 80), fill=NAVY)
        d.rectangle((0, 780, W, H), fill=NAVY)
        text(d, (30, 22), title, 30, "white", True)
        text(d, (1280, 29), "CAPTURE RÉELLE / LOCAL", 18, "#b9d9d2")
        text(d, (30, 796), line1, 27, "white")
        text(d, (30, 834), line2, 25, "#c6dbe5")
        overlay = E / (name + "_legende.png")
        im.save(overlay)
        src = E / (name + ".webm")
        dest = E / (name + "_titre.mp4")
        run(["ffmpeg", "-y", "-i", str(src), "-i", str(overlay), "-filter_complex", "[0:v]scale=1600:700,pad=1600:900:0:80:color=0x102b3b[base];[base][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-r", "25", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-an", str(dest)])
        duration = float(probe(dest)["format"]["duration"])
        scenes.append({"file": dest.name, "label": title, "kind": "actual_browser_capture", "seconds": duration, "raw_capture": src.name})

    browser_scene("01_normal", "01  /  Fonctionnement normal", "L’état annonce primary : PostgreSQL valide l’identifiant, MongoDB fournit le document.", "On ouvre ensuite l’article 2035207 et sa source stockée.")

    services = json.loads((E / "Services_panne.json").read_text())
    im, d = card("Panne provoquée : les deux bases sont arrêtées", "Relevé réel de Docker Compose après l’arrêt, avant la capture en mode de secours.")
    d.rounded_rectangle((70, 245, 1530, 335), radius=12, fill=NAVY)
    text(d, (100, 271), "docker compose stop postgres mongo", 32, "white", True)
    for i, service in enumerate(sorted(services, key=lambda x: x["Service"])):
        y = 380 + i * 80
        failed = service["State"] == "exited"
        color = AMBER if failed else GREEN
        text(d, (100, y), service["Service"], 33, bold=True)
        text(d, (650, y), "ARRÊTÉ" if failed else "EN COURS D’EXÉCUTION", 30, color, True)
        text(d, (1320, y), service["State"], 25, MUTED)
    text(d, (70, 753), "Les volumes sont conservés. Seuls postgres et mongo de ce projet ont été arrêtés.", 26)
    save_still("C_panne", im, 10, "États Docker réels après arrêt des bases")
    browser_scene("02_secours", "02  /  Lecture de secours pendant la panne", "degraded_index_snapshot : le même article est relu depuis le dernier index Elasticsearch.", "Le contenu est comparé au résultat initial. L’ingestion est suspendue ; la fraîcheur n’est pas garantie.")
    browser_scene("03_retabli", "03  /  Rétablissement des deux bases", "PostgreSQL et MongoDB sont redémarrés : la lecture repasse en mode primary.", "L’article est identique avant, pendant et après la panne. Les volumes stockés sont conservés.")

    im, d = card("Ce que cette démonstration établit", "Contrôles effectués sur l’exécution enregistrée, avec leurs limites.")
    box(d, (70, 260, 795, 590), "Vérifié pendant l’enregistrement", ["Même identifiant et empreinte dans 3 moteurs", "Article identique dans les 3 états de lecture", "Retour au chemin SQL / MongoDB", "21 681 articles et documents conservés", "Services rétablis après la capture"])
    box(d, (855, 260, 1530, 590), "Limites à expliquer au jury", ["Tous les services restent sur le même Mac", "Une panne de l’hôte n’est pas couverte", "Le secours repose sur un index antérieur", "Aucune garantie de délai de basculement", "Aucune évaluation NER dans ce bloc"], AMBER)
    text(d, (70, 650), "Montage avec coupes entre les étapes. Captures à vitesse réelle, sans voix ajoutée.", 26)
    text(d, (70, 701), "Les schémas et relevés sont des supports explicatifs ; les parcours sont des captures réelles.", 25, MUTED)
    text(d, (70, 762), "Preuves : Stockages.json, Execution.json et Capture.json dans le dossier de cette vidéo.", 23)
    save_still("D_limites", im, 13, "Résultats et limites")

    playlist = E / "montage.txt"
    playlist.write_text("\n".join("file '" + scene["file"] + "'" for scene in scenes) + "\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(playlist), "-c", "copy", "-movflags", "+faststart", str(TARGET)])
    at = 0.0
    for scene in scenes:
        scene["start_seconds"] = round(at, 2)
        at += scene["seconds"]
        scene["end_seconds"] = round(at, 2)
    meta = {"date_utc": datetime.now(timezone.utc).isoformat(), "output": TARGET.name, "sha256": digest(TARGET), "probe": probe(TARGET), "editing": "Three genuine local browser captures, explanatory diagram and actual query/service results; cuts; no acceleration; caption overlays; silent.", "chapters": scenes, "capture": capture, "render_script_sha256": digest(Path(__file__)), "raw_captures_sha256": {p.name: digest(p) for p in sorted(E.glob("*.webm"))}}
    (E / "Montage.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    (ROOT / "Preuves/Video_architecture_expliquee.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(TARGET), "seconds": meta["probe"]["format"]["duration"], "chapters": len(scenes)}))


if __name__ == "__main__":
    main()
