"""Run with python3 reports/check-plan.py; checks offline plan consistency."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

PLAN = Path(__file__).resolve().parents[1]
ROOT = PLAN.parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.dialogs = set()
        self.modal_ids = set()
        self.assets = []
        self.hash_json = ""
        self.in_hashes = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            assert values["id"] not in self.ids, f"Duplicate ID: {values['id']}"
            self.ids.add(values["id"])
        if tag == "dialog":
            self.dialogs.add(values["id"])
            assert values.get("aria-labelledby"), "Unlabelled dialog"
        if "data-modal" in values:
            self.modal_ids.add(values["data-modal"])
        if tag in {"script", "img", "iframe", "link"}:
            self.assets.extend(values[key] for key in ("src", "href") if key in values)
        self.in_hashes = values.get("id") == "phase-source-hashes"

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_hashes = False

    def handle_data(self, data):
        if self.in_hashes:
            self.hash_json += data


phases = sorted(PLAN.glob("phase-*.md"))
assert len(phases) == 4
link_count = 0
for file in [PLAN / "plan.md", *phases, *sorted((PLAN / "reports").glob("*.md"))]:
    content = file.read_text()
    assert not re.search(r"_TBD_|Requirement A|\[UNVERIFIED\]", content), file
    for dest in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
        parsed = urlsplit(dest)
        if parsed.scheme or not parsed.path:
            continue
        resolved = (file.parent / unquote(parsed.path)).resolve()
        assert resolved.is_relative_to(ROOT), f"Nonportable link: {dest}"
        assert resolved.exists(), f"Broken link in {file.name}: {dest}"
        link_count += 1
page = Page()
html = (PLAN / "plan.html").read_text()
page.feed(html)
assert len(page.dialogs) == 4
assert page.modal_ids == page.dialogs
assert all(asset.startswith("data:") for asset in page.assets), page.assets
assert "@import" not in html
assert not re.search(r"url\(\s*['\"]?https?://", html)
assert "prefers-reduced-motion" in html
assert "<svg" in html and 'class="ak-diagram-root"' in html
hashes = json.loads(page.hash_json)
for file in phases:
    assert hashes[file.name] == hashlib.sha256(file.read_bytes()).hexdigest(), file.name
print(f"PASS: {link_count} local links, 4 source-matched dialogs, offline assets, compiler fragment")
