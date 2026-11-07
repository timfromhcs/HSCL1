# Trademarks and naming rules (mechanical part)

HSCL1 is an independent derivative. It is **not** Kali Linux, **not** Tails, and not endorsed by OffSec, the Tails project or Canonical.
This file records the rules that are enforced by `scripts/check_trademarks.py`, so the mechanical part cannot regress. The legal
review of the product name and of the derivative-distribution wording is still owner work (see `docs/KNOWN_LIMITATIONS.md`).

## Kali Linux

Source: <https://www.kali.org/docs/policy/trademark/> (updated 2025-06-16). Requirements relevant to us:

1. The first mention in a document carries the symbol and the attribution sentence:
   `KALI LINUX ™ is a trademark of OffSec.` (The policy's own example wording.)
2. The mark is not abbreviated, modified, or combined with other words - so never "Kali Edition", "HSCL1 Kali", "Kali-based HSCL1".
3. The mark is set apart from surrounding text (capitalised or emphasised).
4. The mark is not used in a domain name.
5. No OffSec artwork (the Kali logo, the Kali dragon or the NetHunter marks) is redistributed or displayed by HSCL1.

What HSCL1 actually does: it runs **unmodified official Kali Linux container images** in rootless containers. Descriptive use is
therefore "Kali Linux™ tools in isolated containers", with the attribution sentence in the same document.

## Tails

Tails is a separate project and a separate distribution. HSCL1 does not redistribute a modified Tails image and does not claim
equivalence, anonymity or forensic invisibility.

* Wording: "the official Tails ISO, downloaded and verified by the user, launched by HSCL1" - never "HSCL1 Tails", "Tails Edition"
  or "HSCL1 is Tails".
* Any page that discusses privacy must contain the sentence that HSCL1 is **not affiliated with or endorsed by the Tails project**
  and that the official Tails release is recommended where strong anonymity matters.
* No Tails artwork is bundled.

## Ubuntu / Kubuntu / KDE

The base is an unmodified Ubuntu 26.04 LTS / Kubuntu package set plus HSCL1 overlay packages. HSCL1 does not use the Ubuntu, Kubuntu,
KDE or Plasma logos as its own product mark and does not describe itself as an official flavour. Canonical's trademark policy is the
governing document for the base name mentions; the review is an owner item.

## What the gate checks

`python scripts/check_trademarks.py` (also `--check`, the default in the test suite) fails when:

* a forbidden pattern appears anywhere in tracked text files (`HSCL1 Kali`, `Kali Edition`, `Kali-based HSCL1`, `HSCL1 Tails`,
  `Tails Edition`, `HSCL1 is Tails`);
* an image asset name looks like Kali or Tails artwork (`kali-logo`, `kali-dragon`, `kali-nethunter`, `tails-logo`);
* a **user-facing** file (README, website content, shipped package files) mentions the mark without the attribution sentence;
* `README.md`, `website/` privacy content or `docs/PRIVACY_MODE.md` mentions Tails without the non-affiliation sentence.

The gate proves wording, not legal safety. When it passes, that means the mechanical rules above hold - not that a lawyer looked at it.
