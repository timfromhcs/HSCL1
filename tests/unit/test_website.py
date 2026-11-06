"""Static website: structure, trilingual parity, honest download page, internal links resolve."""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build_website.py"
LANGS = ["en", "de", "fr"]
FORBIDDEN = re.compile(r"unhackable|military|certified|zero-trace|fully secure|100% secure|untraceable", re.I)


def build(tmp, site=None):
    env = {"PATH": __import__("os").environ["PATH"], "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    if site:
        env["SITE_URL"] = site
    out = tmp / "dist"
    subprocess.run([sys.executable, str(SCRIPT), str(out)], check=True, env=env, capture_output=True)
    return out


class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.links = []
        self.imgs = []
        self.lang = None
        self.hreflang = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag in ("a", "link") and a.get("href"):
            self.links.append(a["href"])
        if tag == "link" and a.get("hreflang"):
            self.hreflang.append(a["hreflang"])
        if tag == "img":
            self.imgs.append(a)
        if tag == "link" and a.get("rel") == "stylesheet":
            self.links.append(a["href"])


def scan(p):
    s = Scan()
    s.feed(p.read_text(encoding="utf-8"))
    return s


@pytest.fixture(scope="module")
def dist(tmp_path_factory):
    return build(tmp_path_factory.mktemp("web"))


def pages(dist):
    return [dist / "index.html", dist / "download/index.html", dist / "de/index.html", dist / "de/download/index.html",
            dist / "fr/index.html", dist / "fr/download/index.html",
            dist / "security/index.html", dist / "de/security/index.html", dist / "fr/security/index.html",
            dist / "install/vm/index.html", dist / "de/install/vm/index.html", dist / "fr/install/vm/index.html"]


def test_all_pages_exist_with_one_h1_and_correct_lang(dist):
    for p in pages(dist):
        s = scan(p)
        assert s.h1 == 1, p
        want = p.relative_to(dist).parts[0] if p.relative_to(dist).parts[0] in LANGS else "en"
        assert s.lang == want, p


def test_internal_links_and_assets_resolve(dist):
    for p in pages(dist):
        s = scan(p)
        for href in s.links:
            if href.startswith(("http://", "https://", "#")):
                continue
            t = dist / href.lstrip("/")
            if t.is_dir():
                t = t / "index.html"
            assert t.exists(), f"{p.name}: broken link {href}"
        for img in s.imgs:
            assert "alt" in img, "image without alt attribute"
            assert img["alt"] or "hscl1-mark" in img["src"], "only the decorative logo may have empty alt"
            assert (dist / img["src"].lstrip("/")).exists()


def test_translations_have_identical_structure():
    def shape(x):
        if isinstance(x, dict):
            return {k: shape(v) for k, v in x.items()}
        if isinstance(x, list):
            return [shape(v) for v in x]
        return None
    data = {l: json.loads((ROOT / f"website/content/{l}.json").read_text(encoding="utf-8")) for l in LANGS}
    assert shape(data["de"]) == shape(data["en"]) and shape(data["fr"]) == shape(data["en"])
    for l in LANGS:
        for v in json.dumps(data[l], ensure_ascii=False).split('"'):
            assert not FORBIDDEN.search(v), (l, v)


def test_download_links_are_only_real_release_assets(dist):
    rel = json.loads((ROOT / "website/data/release.json").read_text(encoding="utf-8"))["release"]
    assert rel, "release.json must describe the real release (run scripts/fetch_release_meta.py)"
    real = {a["url"] for a in rel["assets"]} | {rel["url"]}
    for p in pages(dist):
        for href in scan(p).links:
            if "github.com" in href and "/releases/" in href:
                assert href in real, href
    assert rel["whole_image"]["sha256"] in (dist / "download/index.html").read_text(encoding="utf-8")


def test_no_release_means_no_download_button(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bw", SCRIPT)
    bw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bw)
    c = json.loads((ROOT / "website/content/en.json").read_text(encoding="utf-8"))
    assert "btn\" href=\"/download/" not in bw.home("en", c, None)
    assert "not published yet" in bw.download("en", c, None)


def test_canonical_and_hreflang_only_with_site_url(tmp_path, dist):
    assert scan(dist / "index.html").hreflang == []
    assert not (dist / "sitemap.xml").exists()
    out = build(tmp_path, "https://example.test")
    assert sorted(scan(out / "de/download/index.html").hreflang) == ["de", "en", "fr", "x-default"]
    assert "https://example.test/fr/download/" in (out / "sitemap.xml").read_text(encoding="utf-8")


def test_security_page_states_the_limits_and_links_the_private_reporting_page(dist):
    for lang, prefix in [("en", ""), ("de", "de/"), ("fr", "fr/")]:
        text = (dist / prefix / "security/index.html").read_text(encoding="utf-8")
        assert "https://github.com/timfromhcs/HSCL1/security" in text
        assert "SHA256SUMS" in text and "Tails" in text


def test_vm_page_lists_only_tested_hypervisor_settings_and_marks_the_rest_untested(dist):
    for prefix in ["", "de/", "fr/"]:
        text = (dist / prefix / "install/vm/index.html").read_text(encoding="utf-8")
        assert "WHPX" in text and ("40 GB" in text or "40 Go" in text) and "VirtualBox" in text
        assert "/dev/sd" not in text  # never a guessed block device
