"""The one-page UI served from the same origin as the API.

No external URL, no ``innerHTML`` (results are written with ``textContent``), the token is
read from the URL fragment (never sent to the server) and removed from the address bar.
The CSP allows exactly the inline script and style by hash.
"""

from __future__ import annotations

import base64
import hashlib

_STYLE = """
body{font:16px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:42rem;padding:0 1rem;background:#12141a;color:#e8eaf0}
label{display:block;margin-top:1rem}
input{width:100%;box-sizing:border-box;padding:.5rem;font:inherit;background:#1c1f28;color:inherit;border:1px solid #3a4052;border-radius:6px}
button{margin-top:1rem;padding:.55rem 1.1rem;font:inherit;border-radius:6px;border:0;background:#6d7cff;color:#fff;cursor:pointer}
button:focus-visible,input:focus-visible{outline:3px solid #ffd166;outline-offset:2px}
pre{background:#1c1f28;padding:1rem;border-radius:6px;overflow:auto;white-space:pre-wrap}
.err{color:#ff8b8b}
"""

_SCRIPT = """
(function () {
  var token = new URLSearchParams(location.hash.slice(1)).get("token");
  history.replaceState(null, "", location.pathname);
  var out = document.getElementById("out");
  document.getElementById("go").addEventListener("click", function () {
    out.className = "";
    out.textContent = "...";
    fetch("/api/v1/symbolic/differentiate", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + (token || "") },
      body: JSON.stringify({
        expression: document.getElementById("expr").value,
        variable: document.getElementById("var").value
      })
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.status === "ok") {
        out.textContent = "d/d" + document.getElementById("var").value + " ( " + j.normalized_expression +
          " ) = " + j.result_expression + "\\nexactness: " + j.exactness + "   engine: " + j.engine +
          "\\nrun: " + j.run_id;
      } else {
        out.className = "err";
        out.textContent = j.status + ": " + (j.error || j.detail || "");
      }
    }).catch(function () { out.className = "err"; out.textContent = "request failed"; });
  });
})();
"""


def _hash(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


CSP = (
    "default-src 'none'; "
    f"script-src {_hash(_SCRIPT)}; "
    f"style-src {_hash(_STYLE)}; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
CSP = CSP.replace("default-src 'none'", "default-src 'self'", 1)

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HCSEASYMATH</title><style>{_STYLE}</style></head>
<body><main>
<h1>HCSEASYMATH</h1>
<p>Exact derivative (SymPy). Powers use <code>**</code>. Made with love by hcsmedia.</p>
<label for="expr">Expression</label>
<input id="expr" value="x**3 - 3*x**2 + 2*x" autocomplete="off" spellcheck="false">
<label for="var">Variable</label>
<input id="var" value="x" autocomplete="off" spellcheck="false">
<button id="go" type="button">Differentiate</button>
<pre id="out" aria-live="polite"></pre>
</main><script>{_SCRIPT}</script></body></html>
"""
