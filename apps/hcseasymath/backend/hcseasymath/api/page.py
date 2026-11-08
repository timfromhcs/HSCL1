"""The one-page UI served from the same origin as the API.

No external URL, no ``innerHTML`` (results are written with ``textContent`` or DOM SVG nodes),
the token is read from the URL fragment (never sent to the server) and removed from the address bar.
The CSP allows exactly the inline script and style by hash.
"""

from __future__ import annotations

import base64
import hashlib

_STYLE = """
body{font:16px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:42rem;padding:0 1rem;background:#12141a;color:#e8eaf0}
label{display:block;margin-top:1rem}
input,select{width:100%;box-sizing:border-box;padding:.5rem;font:inherit;background:#1c1f28;color:inherit;border:1px solid #3a4052;border-radius:6px}
button{margin-top:1rem;padding:.55rem 1.1rem;font:inherit;border-radius:6px;border:0;background:#6d7cff;color:#fff;cursor:pointer}
button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #ffd166;outline-offset:2px}
pre{background:#1c1f28;padding:1rem;border-radius:6px;overflow:auto;white-space:pre-wrap}
.err{color:#ff8b8b}
.field-group{margin-top:1rem}
.hidden{display:none !important}
#plot-svg{width:100%;height:auto;max-height:300px;background:#1c1f28;border-radius:6px;margin-top:1rem}
#plot-svg svg{width:100%;height:auto;display:block}
"""

_SCRIPT = """
(function () {
  var token = "";
  function readToken() {
    var fromHash = new URLSearchParams(location.hash.slice(1)).get("token");
    if (fromHash) {
      token = fromHash;
      try {
        history.replaceState(null, "", location.pathname);
      } catch (e) {}
    }
  }
  readToken();
  window.addEventListener("hashchange", readToken);

  var out = document.getElementById("out");
  var plotSvg = document.getElementById("plot-svg");
  var opSelect = document.getElementById("operation");
  var goBtn = document.getElementById("go");
  var exprInput = document.getElementById("expr");
  var varInput = document.getElementById("var");
  var valueInput = document.getElementById("value");
  var xMinInput = document.getElementById("x_min");
  var xMaxInput = document.getElementById("x_max");
  var pointsInput = document.getElementById("points");

  var opFields = {
    differentiate: ["expr", "var"],
    integrate: ["expr", "var"],
    evaluate: ["expr", "var", "value"],
    simplify: ["expr", "var"],
    solve: ["expr", "var"],
    plot: ["expr", "var", "x_min", "x_max", "points"]
  };

  function showFieldsForOp(op) {
    var allIds = ["expr", "var", "value", "x_min", "x_max", "points"];
    allIds.forEach(function(id) {
      var group = document.getElementById(id + "-group");
      if (group) group.classList.add("hidden");
    });
    (opFields[op] || []).forEach(function(id) {
      var group = document.getElementById(id + "-group");
      if (group) group.classList.remove("hidden");
    });
    goBtn.textContent = op.charAt(0).toUpperCase() + op.slice(1);
  }

  opSelect.addEventListener("change", function () {
    showFieldsForOp(this.value);
  });

  goBtn.addEventListener("click", function () {
    if (!token) readToken();
    var op = opSelect.value;
    out.className = "";
    out.textContent = "...";
    plotSvg.classList.add("hidden");
    while (plotSvg.firstChild) {
      plotSvg.removeChild(plotSvg.firstChild);
    }

    var body = {
      expression: exprInput.value,
      variable: varInput.value
    };
    if (op === "evaluate") {
      body.value = valueInput.value;
    } else if (op === "plot") {
      if (xMinInput && xMinInput.value) body.x_min = xMinInput.value;
      if (xMaxInput && xMaxInput.value) body.x_max = xMaxInput.value;
      if (pointsInput && pointsInput.value) {
        var parsedPoints = parseInt(pointsInput.value, 10);
        if (!isNaN(parsedPoints)) body.points = parsedPoints;
      }
    }

    fetch("/api/v1/symbolic/" + op, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + (token || "") },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (j) {
        return { ok: r.ok, data: j };
      });
    }).then(function (res) {
      var j = res.data;
      if (j.status === "ok" || j.status === "partial" || j.status === "unresolved") {
        renderResult(j, op);
      } else {
        out.className = "err";
        var errDetail = j.error || "";
        if (!errDetail && j.detail) {
          if (Array.isArray(j.detail)) {
            errDetail = j.detail.map(function (d) {
              return (d.loc ? d.loc.join(".") + ": " : "") + d.msg;
            }).join("; ");
          } else {
            errDetail = j.detail;
          }
        }
        out.textContent = (j.status || "error") + ": " + errDetail;
      }
    }).catch(function () {
      out.className = "err";
      out.textContent = "request failed";
    });
  });

  function renderResult(j, op) {
    var lines = [];
    if (j.normalized_expression) lines.push("Input: " + j.normalized_expression);
    if (j.result_expression) lines.push("Result: " + j.result_expression);
    if (j.exactness) lines.push("Exactness: " + j.exactness);
    if (j.engine) lines.push("Engine: " + j.engine);
    if (j.run_id) lines.push("Run: " + j.run_id);
    if (j.assumptions && j.assumptions.length) lines.push("Assumptions: " + j.assumptions.join("; "));
    if (j.checks && j.checks.length) lines.push("Checks: " + j.checks.join("; "));
    if (j.warnings && j.warnings.length) lines.push("Warnings: " + j.warnings.join("; "));
    if (j.error) lines.push("Error: " + j.error);

    out.textContent = lines.join("\\n");
    if (j.status !== "ok") out.className = "err";

    if (op === "plot" && j.samples && j.samples.length) {
      renderPlot(j.samples);
    }
  }

  function renderPlot(samples) {
    var valid = samples.filter(function(p) { return p[1] !== null; });
    if (!valid.length) return;

    var xs = valid.map(function(p) { return p[0]; });
    var ys = valid.map(function(p) { return p[1]; });
    var minX = Math.min.apply(null, xs);
    var maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys);
    var maxY = Math.max.apply(null, ys);

    var width = plotSvg.clientWidth || 400;
    var height = 240;
    var padding = 40;

    var scaleX = (width - 2 * padding) / (maxX - minX || 1);
    var scaleY = (height - 2 * padding) / (maxY - minY || 1);

    var pathData = valid.map(function(p, i) {
      var x = padding + (p[0] - minX) * scaleX;
      var y = height - padding - (p[1] - minY) * scaleY;
      return (i === 0 ? "M" : "L") + x.toFixed(1) + "," + y.toFixed(1);
    }).join(" ");

    var svgNS = ["http:", "//www.w3.org/2000/svg"].join("");
    while (plotSvg.firstChild) {
      plotSvg.removeChild(plotSvg.firstChild);
    }
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("aria-label", "Function plot");
    svg.setAttribute("role", "img");

    var path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", pathData);
    path.setAttribute("stroke", "#6d7cff");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("fill", "none");
    svg.appendChild(path);

    var xAxis = document.createElementNS(svgNS, "line");
    xAxis.setAttribute("x1", padding.toString());
    xAxis.setAttribute("y1", (height - padding).toString());
    xAxis.setAttribute("x2", (width - padding).toString());
    xAxis.setAttribute("y2", (height - padding).toString());
    xAxis.setAttribute("stroke", "#3a4052");
    svg.appendChild(xAxis);

    var yAxis = document.createElementNS(svgNS, "line");
    yAxis.setAttribute("x1", padding.toString());
    yAxis.setAttribute("y1", padding.toString());
    yAxis.setAttribute("x2", padding.toString());
    yAxis.setAttribute("y2", (height - padding).toString());
    yAxis.setAttribute("stroke", "#3a4052");
    svg.appendChild(yAxis);

    plotSvg.appendChild(svg);
    plotSvg.classList.remove("hidden");
  }

  showFieldsForOp(opSelect.value);
})();
"""


def _hash(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


CSP = (
    "default-src 'self'; "
    f"script-src {_hash(_SCRIPT)}; "
    f"style-src {_hash(_STYLE)}; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HCSEASYMATH</title><style>{_STYLE}</style></head>
<body><main>
<h1>HCSEASYMATH</h1>
<p>Exact symbolic math (SymPy). Powers use <code>**</code>. Made with love by hcsmedia.</p>
<label for="operation">Operation</label>
<select id="operation">
  <option value="differentiate">Differentiate</option>
  <option value="integrate">Integrate</option>
  <option value="evaluate">Evaluate</option>
  <option value="simplify">Simplify</option>
  <option value="solve">Solve</option>
  <option value="plot">Plot</option>
</select>

<div class="field-group" id="expr-group">
  <label for="expr">Expression</label>
  <input id="expr" value="x**3 - 3*x**2 + 2*x" autocomplete="off" spellcheck="false">
</div>
<div class="field-group" id="var-group">
  <label for="var">Variable</label>
  <input id="var" value="x" autocomplete="off" spellcheck="false">
</div>
<div class="field-group hidden" id="value-group">
  <label for="value">Value</label>
  <input id="value" value="2" autocomplete="off" spellcheck="false">
</div>
<div class="field-group hidden" id="x_min-group">
  <label for="x_min">X Min</label>
  <input id="x_min" value="-5" autocomplete="off" spellcheck="false">
</div>
<div class="field-group hidden" id="x_max-group">
  <label for="x_max">X Max</label>
  <input id="x_max" value="5" autocomplete="off" spellcheck="false">
</div>
<div class="field-group hidden" id="points-group">
  <label for="points">Points</label>
  <input id="points" value="200" autocomplete="off" spellcheck="false">
</div>

<button id="go" type="button">Differentiate</button>
<pre id="out" aria-live="polite"></pre>
<div id="plot-svg" class="hidden"></div>
</main><script>{_SCRIPT}</script></body></html>
"""
