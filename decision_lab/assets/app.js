/* decision_lab — progressive enhancement only.
 * Every table is fully readable with JavaScript disabled; this adds client-side
 * filtering and a visible row count. No external library, no network request. */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") { fn(); }
    else { document.addEventListener("DOMContentLoaded", fn); }
  }

  /* One filter bar may control one or more tables named in data-tables. */
  function wire(bar) {
    var ids = (bar.getAttribute("data-tables") || "").split(/[,\s]+/).filter(Boolean);
    var tables = ids.map(function (id) { return document.getElementById(id); })
                    .filter(Boolean);
    if (!tables.length) { return; }

    var text = bar.querySelector("input[data-filter='text']");
    var selects = Array.prototype.slice.call(bar.querySelectorAll("select[data-filter]"));
    var out = bar.querySelector(".count");

    function apply() {
      var q = (text && text.value || "").trim().toLowerCase();
      var shown = 0, total = 0;

      tables.forEach(function (tbl) {
        var bodies = tbl.querySelectorAll("tbody");
        Array.prototype.forEach.call(bodies, function (tb) {
          Array.prototype.forEach.call(tb.querySelectorAll("tr"), function (tr) {
            total++;
            var hay = (tr.getAttribute("data-search") || tr.textContent || "").toLowerCase();
            var ok = !q || hay.indexOf(q) !== -1;

            if (ok) {
              ok = selects.every(function (sel) {
                var key = sel.getAttribute("data-filter");
                var want = sel.value;
                if (!want || want === "__all") { return true; }
                var have = tr.getAttribute("data-" + key) || "";
                return want === "__blank" ? have === "" : have === want;
              });
            }
            tr.style.display = ok ? "" : "none";
            if (ok) { shown++; }
          });
        });
      });

      if (out) {
        out.textContent = shown === total
          ? shown + " rows"
          : shown + " of " + total + " rows";
      }
    }

    if (text) { text.addEventListener("input", apply); }
    selects.forEach(function (s) { s.addEventListener("change", apply); });
    var reset = bar.querySelector("button[data-reset]");
    if (reset) {
      reset.addEventListener("click", function () {
        if (text) { text.value = ""; }
        selects.forEach(function (s) { s.selectedIndex = 0; });
        apply();
      });
    }
    apply();
  }

  ready(function () {
    Array.prototype.forEach.call(document.querySelectorAll(".filters[data-tables]"), wire);

    /* Populate a select from the distinct data-<key> values already present in the
     * table, so the filter options can never drift from the published rows. */
    Array.prototype.forEach.call(document.querySelectorAll("select[data-autofill]"), function (sel) {
      var key = sel.getAttribute("data-filter");
      var tbl = document.getElementById(sel.getAttribute("data-autofill"));
      if (!tbl) { return; }
      var seen = {}, blank = false;
      Array.prototype.forEach.call(tbl.querySelectorAll("tbody tr"), function (tr) {
        var v = tr.getAttribute("data-" + key);
        if (v === null || v === "") { blank = true; } else { seen[v] = true; }
      });
      Object.keys(seen).sort().forEach(function (v) {
        var o = document.createElement("option");
        o.value = v; o.textContent = v;
        sel.appendChild(o);
      });
      if (blank) {
        var b = document.createElement("option");
        b.value = "__blank"; b.textContent = "(blank / unverified)";
        sel.appendChild(b);
      }
    });
  });
})();
