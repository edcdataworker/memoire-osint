"""Bounded public TASS requests and source-preserving article extraction."""

import gzip
import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from ..transform import normalize

SECTIONS = {
    "defense": "Militaire et défense",
    "world": "Monde",
    "politics": "Politique russe",
    "economy": "Économie",
}
VERSION = "tass-html-v1"
MAX_RESPONSE = 4_000_000


def bounds(start, end):
    left = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    right = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    if left >= right or left.year < 1990 or right.year > 2101:
        raise ValueError("Période invalide : le début doit précéder ou égaler la fin.")
    return int(left.timestamp()), int(right.timestamp())


def parameters(data):
    if not isinstance(data, dict):
        raise ValueError("Commande JSON invalide.")
    if not isinstance(data.get("start"), str) or not isinstance(data.get("end"), str):
        raise ValueError("Dates manquantes ou invalides.")
    if data.get("section") not in SECTIONS:
        raise ValueError("Rubrique non prise en charge.")
    bounds(data.get("start", ""), data.get("end", ""))
    limit = data.get("limit", 50)
    if type(limit) is not int or not 1 <= limit <= 2000:
        raise ValueError("Choisir une limite de 1 à 2 000 articles.")
    keywords = data.get("keywords", "")
    if not isinstance(keywords, str) or len(keywords) > 500:
        raise ValueError("Les mots-clés doivent contenir au plus 500 caractères.")
    return {
        "section": data["section"],
        "start": data["start"],
        "end": data["end"],
        "limit": limit,
        "keywords": [k.strip().casefold() for k in keywords.split(",") if k.strip()],
    }


def canonical(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "tass.com" or parsed.query or parsed.fragment:
        raise ValueError("URL TASS invalide.")
    if not re.fullmatch(r"/[a-z-]+/\d+", parsed.path):
        raise ValueError("Chemin d’article TASS invalide.")
    return "https://tass.com" + parsed.path


class Stopped(Exception):
    pass


class Client:
    def __init__(self, emit, stopped=lambda: False, interval=0.7):
        self.emit, self.stopped, self.interval = emit, stopped, interval
        self.last = 0.0
        self.robot = None

    def pause(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.stopped():
                raise Stopped()
            time.sleep(min(0.1, max(0, deadline - time.monotonic())))

    def request(self, url, body=None, robots=True):
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "tass.com"
            or parsed.path.startswith("/search")
        ):
            raise ValueError("Destination réseau non autorisée.")
        if robots and self.robot is not None and not self.robot.can_fetch("MemoireOSINT", url):
            raise ValueError("Accès exclu par robots.txt.")
        encoded = json.dumps(body).encode() if body is not None else None
        for attempt in range(3):
            self.pause(max(0, self.interval - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                req = Request(
                    url,
                    data=encoded,
                    headers={
                        "User-Agent": "MemoireOSINT/1.0 (local educational collector)",
                        "Accept-Encoding": "identity",
                        "Content-Type": "application/json",
                        "Referer": "https://tass.com/",
                    },
                )
                with urlopen(req, timeout=15) as response:
                    if urlparse(response.url).netloc != "tass.com":
                        raise ValueError("Redirection hors TASS.")
                    data = response.read(MAX_RESPONSE + 1)
                if len(data) > MAX_RESPONSE:
                    raise ValueError("Réponse trop volumineuse.")
                if data[:2] == b"\x1f\x8b":
                    # Bound decompression as well as transferred bytes.
                    import io

                    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                        data = stream.read(MAX_RESPONSE + 1)
                    if len(data) > MAX_RESPONSE:
                        raise ValueError("Réponse décompressée trop volumineuse.")
                return data.decode("utf-8")
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                code = getattr(exc, "code", None)
                self.emit(
                    "network_error", url=url, attempt=attempt + 1, code=code or type(exc).__name__
                )
                if attempt == 2 or code in (400, 401, 403, 404, 410):
                    raise
                wait = 2**attempt
                if code == 429:
                    try:
                        wait = min(60, max(wait, int(exc.headers.get("Retry-After", "0"))))
                    except ValueError:
                        pass
                self.pause(wait)

    def initialize(self, section):
        robot = RobotFileParser()
        robot.parse(self.request("https://tass.com/robots.txt", robots=False).splitlines())
        self.robot = robot
        markup = self.request("https://tass.com/" + section)
        match = re.search(r"sectionId\s*=\s*(\d+)", markup)
        if not match:
            raise ValueError("La rubrique ne fournit plus son identifiant de pagination.")
        return int(match[1])

    def discover(self, section_id, cursor, excluded):
        data = json.loads(
            self.request(
                "https://tass.com/userApi/categoryNewsList",
                {
                    "sectionId": section_id,
                    "limit": 20,
                    "type": "all",
                    "excludeNewsIds": excluded,
                    "imageSize": 434,
                    "timestamp": cursor,
                },
            )
        )
        if not isinstance(data, dict) or not isinstance(data.get("newsList"), list):
            raise ValueError("Contrat de pagination TASS modifié.")
        return data


class ArticleParser(HTMLParser):
    """Only text-blocks inside text-content; unrelated page text is never NER input."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.parts, self.metadata = [], [], []
        self.script, self.buffer = False, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        inherited = self.stack[-1][1:] if self.stack else (False, False, False)
        content, block, excluded = inherited
        classes = attrs.get("class", "").split()
        content = content or "text-content" in classes
        block = block or (content and "text-block" in classes)
        excluded = (
            excluded
            or tag in ("script", "style", "nav", "aside")
            or any(s in attrs.get("class", "").lower() for s in ("advert", "recommend", "adfox"))
        )
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script, self.buffer = True, []
        if tag not in ("br", "img", "meta", "link", "input", "hr", "source", "wbr"):
            self.stack.append((tag, content, block, excluded))
        elif block and tag == "br":
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag == "script" and self.script:
            try:
                self.metadata.append(json.loads("".join(self.buffer)))
            except ValueError:
                pass
            self.script = False
        if self.stack and self.stack[-1][2] and tag in ("p", "div", "li"):
            self.parts.append(" ")
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.script:
            self.buffer.append(data)
        elif self.stack and self.stack[-1][2] and not self.stack[-1][3]:
            self.parts.append(data)


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def extract(markup, url, run_id):
    url = canonical(url)
    parser = ArticleParser()
    parser.feed(markup)
    news = next(
        (
            item
            for value in parser.metadata
            for item in objects(value)
            if item.get("@type") == "NewsArticle"
        ),
        None,
    )
    if not news or not news.get("datePublished"):
        raise ValueError("Métadonnées de publication absentes.")
    published = datetime.fromisoformat(news["datePublished"].replace("Z", "+00:00"))
    if published.tzinfo is None:
        raise ValueError("Fuseau de publication absent.")
    text = "".join(parser.parts)
    if len(text) > 100_000:
        raise ValueError("Article trop long pour le contrat NER.")
    checksum = hashlib.sha256(markup.encode()).hexdigest()
    result = normalize(
        {
            "id": int(url.rsplit("/", 1)[1]),
            "date": int(published.timestamp()),
            "title": news.get("headline", ""),
            "text": text,
            "url": url,
        },
        checksum,
        0,
        run_id,
        "raw",
    )
    result["provenance"]["collection"] = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "url_requested": url,
        "extractor_version": VERSION,
        "page_sha256": checksum,
        "date_modified_source": news.get("dateModified"),
    }
    return result
