#!/usr/bin/env bash
# End-to-end test of the local AI path with one real model (CPU, no GPU needed):
#   pinned llama.cpp release (sha256 verified) -> `hscl ai model download` (sha256 verified) -> `hscl ai profile` -> llama-server
#   on 127.0.0.1 -> a real chat completion -> measured tokens/s. Writes evidence JSON; exits non-zero on any failed step.
#
# Usage: scripts/ai-smoke-test.sh [MODEL_ID] [WORKDIR]      (default: qwen3.5-2b-abliterated, ~/hscl1-build/ai-test)
# Needs: network, curl, python3, cargo (to build hscl) or HSCL_BIN pointing at a built binary.
set -Eeuo pipefail

model="${1:-qwen3.5-2b-abliterated}"
work="${2:-$HOME/hscl1-build/ai-test}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
port=8089
mkdir -p "$work/models" "$work/backend"
server_pid=""
trap '[ -z "$server_pid" ] || kill "$server_pid" 2>/dev/null || true' EXIT

pin() { python3 -c "import json,sys; d=json.load(open('$root/ai/backends/llama.json')); a=d['assets']['cpu']; print({'tag':d['tag'],'url':a['url'],'sha':a['sha256'],'name':a['name']}['$1'])"; }

echo "== backend: pinned llama.cpp $(pin tag) (CPU build)"
tarball="$work/backend/$(pin name)"
[ -f "$tarball" ] || curl --location --fail --silent --show-error --output "$tarball" "$(pin url)"
echo "$(pin sha)  $tarball" | sha256sum -c -
rm -rf "$work/backend/unpacked"; mkdir -p "$work/backend/unpacked"
tar -xzf "$tarball" -C "$work/backend/unpacked"
server="$(find "$work/backend/unpacked" -name llama-server -type f | head -n 1)"
[ -x "$server" ] || { echo "llama-server not found in the release archive" >&2; exit 1; }
libdir="$(dirname "$server")"
export LD_LIBRARY_PATH="$libdir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$server" --version 2>&1 | head -n 3 || true

echo "== hscl"
hscl="${HSCL_BIN:-}"
if [ -z "$hscl" ]; then
  CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-$HOME/hscl1-build/target-dev}" cargo build --release -q --manifest-path "$root/Cargo.toml"
  hscl="${CARGO_TARGET_DIR:-$HOME/hscl1-build/target-dev}/release/hscl"
fi

echo "== download $model (verified)"
HSCL_MODELS_DIR="$work/models" "$hscl" ai model download "$model" --accept-warning
HSCL_MODELS_DIR="$work/models" "$hscl" ai model verify "$model"

echo "== plan"
"$hscl" ai profile "$model" --backend "$server" --json > "$work/profile.json"
python3 - "$work" "$port" <<'PY'
import json, sys
work, port = sys.argv[1], sys.argv[2]
prof = json.load(open(f"{work}/profile.json"))
cat = json.load(open("/dev/stdin")) if False else None
args = prof["llama_server_args"]
import glob
ggufs = [g for g in glob.glob(f"{work}/models/*.gguf") if "mmproj" not in g]
assert len(ggufs) == 1, ggufs
args = [ggufs[0] if a == "<MODEL_PATH>" else a for a in args]
args = [port if (i > 0 and args[i - 1] == "--port") else a for i, a in enumerate(args)]
open(f"{work}/server.args", "w").write("\n".join(args))
print("plan:", json.dumps(prof["plan"]))
PY
mapfile -t args < "$work/server.args"

echo "== start llama-server on 127.0.0.1:$port"
"$server" "${args[@]}" > "$work/server.log" 2>&1 &
server_pid=$!
for _ in $(seq 1 120); do
  if curl -s "http://127.0.0.1:$port/health" | grep -q '"status":"ok"'; then break; fi
  kill -0 "$server_pid" 2>/dev/null || { tail -n 30 "$work/server.log"; echo "server exited early" >&2; exit 1; }
  sleep 2
done
curl -s "http://127.0.0.1:$port/health" | grep -q '"status":"ok"' || { tail -n 30 "$work/server.log"; echo "server not healthy" >&2; exit 1; }
ss -tlnp 2>/dev/null | grep ":$port " | grep -q "127.0.0.1" && echo "listening on loopback only: yes" || echo "WARNING: could not confirm loopback-only listening"

echo "== chat completion"
python3 - "$port" "$work" <<'PY'
import json, sys, time, urllib.request
port, work = sys.argv[1], sys.argv[2]
def ask(prompt, n=48):
    body = json.dumps({"messages": [{"role": "user", "content": prompt}], "max_tokens": n, "temperature": 0}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d, time.time() - t0
d, dt = ask("Reply with exactly one word: pong")
text = d["choices"][0]["message"]["content"]
tokens = d["usage"]["completion_tokens"]
timings = d.get("timings", {})
ev = {"model_reply": text.strip()[:200], "completion_tokens": tokens, "seconds": round(dt, 2),
      "tokens_per_second_wall": round(tokens / dt, 2) if dt > 0 else None,
      "predicted_per_second_server": round(timings.get("predicted_per_second", 0), 2) or None,
      "finish_reason": d["choices"][0]["finish_reason"]}
assert text.strip(), "empty reply"
json.dump(ev, open(f"{work}/evidence.json", "w"), indent=2)
print(json.dumps(ev, indent=2))
PY
echo "== OK: evidence in $work/evidence.json"
