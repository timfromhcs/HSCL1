# Local AI

`hscl ai` is a **model runtime manager**, not an assistant that ships with the OS. No model weights are
in the image (the ISO has to stay installable), nothing is downloaded without you asking, and no
request leaves the machine unless you start a server and point a client at it.

The commands below were read from the CLI's own help output; every one of them is resolved by the
doc-command gate, so they exist.

## Quick start

```console
$ hscl ai detect                        # what the machine can do, and what it cannot
$ hscl ai backend list                  # auto / vulkan / cpu / cuda / rocm and why each is available
$ hscl ai model recommend               # catalogue entries that fit this machine, best first
$ hscl ai model download <id>           # SHA-256 verified, licence shown first
$ hscl ai profile <id>                  # backend, offload, context, KV cache, threads
$ hscl ai serve <id>                    # prints the exact llama-server command; starts nothing
$ hscl ai server start <id>             # starts it on 127.0.0.1:8081
$ hscl ai server status
$ hscl ai server stop
```

## Detection

`hscl ai detect` prints CPU model, threads and flags, RAM, every GPU, the Vulkan ICD files and DRM
render nodes, and a recommendation with a reason. `--json` gives the same as machine-readable output.

Two things it deliberately does **not** do:

- It does not infer VRAM from shared memory. An APU's GTT is reported as what it is, not as dedicated VRAM.
- It does not call a GPU "accelerated" because `vulkaninfo` succeeded. `gpu_acceleration_verified` stays
  `false` until a real inference smoke test ran on that device. On a machine without a Vulkan ICD the
  recommendation is `cpu` with the reason spelled out.

## Backends

| Backend | When it is offered |
|---|---|
| `auto` | always; resolves from the detection result and says what it resolved to |
| `vulkan` | only with a usable Vulkan ICD **and** a DRM render node |
| `cpu` | always — the portable fallback, with the best instruction-set path the CPU reports |
| `cuda` | only with an NVIDIA GPU and the runtime present |
| `rocm` | only with a supported AMD GPU and the runtime present |

`hscl ai backend set <name>` records the choice; an unavailable backend is refused instead of silently
falling back, because a silent fallback would make a benchmark meaningless.

## Model catalogue

`hscl ai model list|recommend|info|download|verify|remove|path|add`.

- Every entry carries a licence and a warning; `hscl ai model info <id>` prints both before a download.
- Downloads are SHA-256 verified. `hscl ai model verify <id>` re-checks size and digest later, so a
  truncated or tampered file is caught without re-downloading.
- Models flagged `abliterated` require `--accept-warning`. The current catalogue is **abliterated-only**,
  which is a deliberate but narrow choice: these are modified weights, not the upstream models, and the
  list contains no permissive base variants yet. That is a limitation, not a feature.

Only GGUF is supported. Formats that need arbitrary pickle deserialisation are refused — a model file
is data, never code that gets executed.

## Storage

```console
$ hscl ai storage show
$ hscl ai storage set /mnt/models
```

`set` refuses a relative path, shell metacharacters and a **filesystem root** (writing models next to
`/etc` is never intended). The default lives under the user's home; an external drive is fine.

If the storage path is on a drive that is not mounted, the CLI reports that instead of showing an empty
library, and it never deletes a model because the drive was absent.

## Fitting a model

```console
$ hscl ai fit path/to/model.gguf --ctx 8192
$ hscl ai profile <id> --low-vram
```

`fit` reads only the GGUF metadata and estimates RAM/VRAM for a context size — an estimate, not a
measurement. `profile` turns that into a run plan (backend, offload layers, context, KV cache type,
threads) for this machine. `--low-vram` forces partial offload and a denser KV cache.

No token-per-second number is promised anywhere, because a throughput claim without a benchmark on the
user's hardware is a guess.

## The server

`hscl ai serve` prints the exact `llama-server` command line and starts nothing. `hscl ai server start`
runs it, bound to `127.0.0.1` (default port 8081) — never to a LAN address.

- The API key is read from a **file** (`ai-server.key` by default), never from the command line, so it
  does not end up in `ps` or a shell history.
- `--router-dir` serves several models from the storage directory with on-demand loading and
  `--models-max 1|2`; `--metrics` adds the Prometheus endpoint.
- `--kv-in-ram` keeps the KV cache in system RAM while the weights stay on the GPU (the APU case).
- `hscl ai server status` reports the port, model and process state; `stop` shuts it down and removes
  only HSCL1-owned temporary files.

## Safety boundaries

- No root: nothing in `hscl ai` needs it.
- No telemetry and no remote model routing; the server is loopback-only.
- The feature is a runtime manager, not an autonomous agent. Nothing here lets a model run commands.
- `hscl ai server start` is the only command that opens a socket, and it refuses to bind anything but
  loopback.

## What is not verified

| Claim | State |
|---|---|
| GPU acceleration on this hardware | **not verified** — no Vulkan ICD or render node on the test machine, so `gpu_acceleration_verified` stays false |
| TurboQuant / MTP support | only reported if the backend binary advertises it; not claimed by HSCL1 |
| Measured tokens/second | never claimed; no benchmark is shipped |
| Catalogue breadth | abliterated-only, no permissive base models |
| External-drive hot-unplug during a download | handled by refusing to write, not by resuming |
