# Security policy

HSCL1 is **pre-alpha** software. Do not use it for anything that needs a security guarantee. It has not been tested on physical
hardware, is not signed, and makes no anonymity or "unhackable" claims.

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** for this repository (Security tab -> "Report a vulnerability"). Do not open a
public issue for a security problem. Include the version (`hscl version`), what you did, what happened, and what you expected.
You will get an answer as soon as a maintainer can read the report; there is no service-level promise at this stage.

## Scope

In scope: code and configuration in this repository (CLI, Control Center, Workshop daemon and respin tool, packaging, build and
release scripts, MCP servers). Out of scope: vulnerabilities in upstream Ubuntu, KDE, Qt, llama.cpp or models - report those upstream.

## What to know about the Workshop

The Workshop (`hscl-workshop`) is a developer tool that is **inert by default** (no enabled unit, no socket, no network listener).
It starts only when a hypervisor provides the virtio port `hscl.api` or `hscl.qa`, or when started by hand. Whoever controls the
hypervisor end of that port can already control the VM, and hooks run as root by design. Do not enable it on a machine you do not
control. Details: `docs/THREAT_MODEL.md` and ADR-004 in `docs/DECISIONS.md`.

## Release integrity

Release assets are published with `SHA256SUMS`. Release signing is **not yet in place** (no signing key has been created); until it
is, verify downloads with the published hashes and treat them as unsigned.
