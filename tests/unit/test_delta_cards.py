"""Plan E1: every abliterated catalog model needs a delta card that says honestly whether anything was measured; none may ship in the image."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import check_delta_cards as dc  # noqa: E402

ABL = {"id": "m-abliterated", "variant": "abliterated", "file": "m-abl.gguf", "warning": "Community-derived 'abliterated' model: x"}
PLAIN = {"id": "m-plain", "variant": "instruct", "file": "m.gguf", "warning": ""}


def card(**kw):
    base = {"measured_by": "none", "refusal_rate": None, "tool_overcall_rate": None, "kl_vs_stock": None, "date": "2026-11-06", "source": "", "note": "not measured"}
    base.update(kw)
    return base


def make(tmp_path, models, cards, shipped_text=None):
    (tmp_path / "ai" / "catalog").mkdir(parents=True)
    (tmp_path / "ai" / "catalog" / "models.json").write_text(json.dumps({"schema": 1, "models": models}), encoding="utf-8")
    (tmp_path / "ai" / "catalog" / "delta-cards.json").write_text(json.dumps({"schema": 1, "cards": cards}), encoding="utf-8")
    (tmp_path / "docs" / "research").mkdir(parents=True)
    (tmp_path / "docs" / "research" / "own.md").write_text("evidence\n", encoding="utf-8")
    if shipped_text is not None:
        (tmp_path / "distro" / "base").mkdir(parents=True)
        (tmp_path / "distro" / "base" / "packages.txt").write_text(shipped_text, encoding="utf-8")
    return tmp_path


OWN = card(measured_by="own", refusal_rate=0.04, tool_overcall_rate=0.2, kl_vs_stock=0.016, source="docs/research/own.md", note="own eval")
THIRD = card(measured_by="third-party", refusal_rate=0.04, tool_overcall_rate=0.43, kl_vs_stock=0.016, source="https://huggingface.co/x/y", note="single source")


def test_unmeasured_card_is_valid_and_reported(tmp_path):
    root = make(tmp_path, [ABL, PLAIN], {"m-abliterated": card()})
    assert dc.check(root) == []
    assert dc.report(root) == {"abliterated": 1, "own": 0, "third-party": 0, "unmeasured": 1}


def test_own_and_third_party_cards_are_valid(tmp_path):
    root = make(tmp_path, [ABL], {"m-abliterated": OWN})
    assert dc.check(root) == []
    root2 = make(tmp_path / "b", [ABL], {"m-abliterated": THIRD})
    assert dc.check(root2) == []


def test_plain_models_need_no_card(tmp_path):
    assert dc.check(make(tmp_path, [PLAIN], {})) == []


def test_missing_card_for_an_abliterated_model_is_an_error(tmp_path):
    errs = dc.check(make(tmp_path, [ABL], {}))
    assert any("m-abliterated" in e and "no delta card" in e for e in errs)


def test_orphan_card_is_an_error(tmp_path):
    errs = dc.check(make(tmp_path, [PLAIN], {"ghost": card()}))
    assert any("ghost" in e and "not an abliterated catalog model" in e for e in errs)


@pytest.mark.parametrize(
    "bad, fragment",
    [
        (dict(measured_by="guess"), "measured_by"),
        (dict(measured_by="own", refusal_rate=None, tool_overcall_rate=0.1, kl_vs_stock=0.1, source="docs/research/own.md"), "refusal_rate"),
        (dict(measured_by="own", refusal_rate=1.5, tool_overcall_rate=0.1, kl_vs_stock=0.1, source="docs/research/own.md"), "refusal_rate"),
        (dict(measured_by="own", refusal_rate=0.1, tool_overcall_rate=-0.1, kl_vs_stock=0.1, source="docs/research/own.md"), "tool_overcall_rate"),
        (dict(measured_by="own", refusal_rate=0.1, tool_overcall_rate=0.1, kl_vs_stock=-1, source="docs/research/own.md"), "kl_vs_stock"),
        (dict(measured_by="own", refusal_rate=0.1, tool_overcall_rate=0.1, kl_vs_stock=0.1, source="docs/research/missing.md"), "source"),
        (dict(measured_by="own", refusal_rate=0.1, tool_overcall_rate=0.1, kl_vs_stock=0.1, source=""), "source"),
        (dict(measured_by="third-party", refusal_rate=0.1, tool_overcall_rate=0.1, kl_vs_stock=0.1, source="not a url"), "source"),
        (dict(measured_by="none", refusal_rate=0.1), "must be null"),
        (dict(date="06.11.2026"), "date"),
        (dict(measured_by="own", refusal_rate=True, tool_overcall_rate=0.1, kl_vs_stock=0.1, source="docs/research/own.md"), "refusal_rate"),
    ],
)
def test_invalid_cards_are_rejected(tmp_path, bad, fragment):
    errs = dc.check(make(tmp_path, [ABL], {"m-abliterated": card(**bad)}))
    assert any(fragment in e for e in errs), errs


def test_an_abliterated_model_in_the_image_sources_is_an_error(tmp_path):
    for text in ("m-abliterated\n", "file: m-abl.gguf\n"):
        errs = dc.check(make(tmp_path / text[:3].strip(":"), [ABL], {"m-abliterated": card()}, shipped_text=text))
        assert any("ships in the image" in e for e in errs), errs


def test_schema_file_lists_the_same_required_fields_as_the_checker():
    schema = json.loads((ROOT / "ai" / "catalog" / "delta-card.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) == set(dc.REQUIRED_FIELDS)


def test_the_real_repository_passes_and_is_honest_about_what_is_unmeasured():
    assert dc.check(ROOT) == []
    r = dc.report(ROOT)
    assert r["abliterated"] >= 1 and r["own"] + r["third-party"] + r["unmeasured"] == r["abliterated"]


def test_cli_exit_codes(tmp_path, capsys):
    root = make(tmp_path, [ABL], {})
    assert dc.main(["--root", str(root)]) == 1
    root2 = make(tmp_path / "ok", [ABL], {"m-abliterated": card()})
    assert dc.main(["--root", str(root2), "--report"]) == 0
    assert "unmeasured" in capsys.readouterr().out
