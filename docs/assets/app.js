/* Table sort + filter, nav highlighting, nothing else. No external requests. */
(function () {
  function textOf(cell) {
    var t = (cell.innerText || cell.textContent || "").trim();
    return t;
  }
  function numOf(cell) {
    var t = textOf(cell).replace(/[%,$\s]/g, "").replace(/[^\d.\-+eE]/g, "");
    if (t === "" || t === "-" || t === "--") return null;
    var v = Number(t);
    return isNaN(v) ? null : v;
  }
  function sortTable(table, idx, dir) {
    var body = table.tBodies[0];
    if (!body) return;
    var rows = Array.prototype.slice.call(body.rows);
    var cells0 = table.tHead ? table.tHead.rows[0].cells.length : 0;
    var numeric = true, any = false;
    rows.forEach(function (r) {
      if (!r.cells[idx]) return;
      var v = numOf(r.cells[idx]);
      if (v !== null) { any = true; } else if (textOf(r.cells[idx]) !== "") { numeric = false; }
    });
    numeric = numeric && any;
    rows.sort(function (a, b) {
      var x = a.cells[idx] ? a.cells[idx] : null, y = b.cells[idx] ? b.cells[idx] : null;
      if (!x || !y) return 0;
      if (numeric) {
        var nx = numOf(x), ny = numOf(y);
        if (nx === null && ny === null) return 0;
        if (nx === null) return 1;
        if (ny === null) return -1;
        return dir * (nx - ny);
      }
      return dir * textOf(x).localeCompare(textOf(y), undefined, { numeric: true });
    });
    rows.forEach(function (r) { body.appendChild(r); });
    void cells0;
  }
  function enhance(table) {
    if (table.dataset.enhanced) return;
    table.dataset.enhanced = "1";
    var ths = table.tHead ? table.tHead.rows[0].cells : [];
    Array.prototype.forEach.call(ths, function (th, i) {
      th.addEventListener("click", function () {
        var dir = th.dataset.dir === "asc" ? -1 : 1;
        Array.prototype.forEach.call(ths, function (o) { delete o.dataset.dir; });
        th.dataset.dir = dir === 1 ? "asc" : "desc";
        sortTable(table, i, dir);
      });
    });
    var wrap = table.closest(".tablewrap");
    if (!wrap) return;
    var bar = document.createElement("div");
    bar.className = "tblbar";
    var seen = {};
    var sel = document.createElement("select");
    sel.style.cssText = "padding:8px 10px;border:1px solid var(--line);border-radius:10px;font-size:13px;background:#fff";
    var all = document.createElement("option");
    all.value = ""; all.textContent = "All rows";
    sel.appendChild(all);
    var filterCol = table.dataset.filterCol ? parseInt(table.dataset.filterCol, 10) : -1;
    if (filterCol >= 0 && table.tBodies[0]) {
      Array.prototype.forEach.call(table.tBodies[0].rows, function (r) {
        if (!r.cells[filterCol]) return;
        var v = textOf(r.cells[filterCol]);
        if (v && !seen[v]) { seen[v] = 1; var o = document.createElement("option"); o.value = v; o.textContent = v; sel.appendChild(o); }
      });
    }
    var input = document.createElement("input");
    input.type = "search";
    input.placeholder = table.dataset.searchPlaceholder || "Filter rows…";
    var count = document.createElement("span");
    count.className = "count";
    function apply() {
      var q = input.value.toLowerCase().trim();
      var fv = sel.value;
      var shown = 0;
      Array.prototype.forEach.call(table.tBodies[0].rows, function (r) {
        var hay = textOf(r).toLowerCase();
        var ok = q === "" || hay.indexOf(q) !== -1;
        if (ok && fv && r.cells[filterCol]) ok = textOf(r.cells[filterCol]) === fv;
        r.style.display = ok ? "" : "none";
        if (ok) shown++;
      });
      count.textContent = shown + " row" + (shown === 1 ? "" : "s");
    }
    input.addEventListener("input", apply);
    sel.addEventListener("change", apply);
    if (filterCol < 0) sel.style.display = "none";
    bar.appendChild(sel); bar.appendChild(input); bar.appendChild(count);
    wrap.parentNode.insertBefore(bar, wrap);
    apply();
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("table[data-sortable]").forEach(enhance);
    var path = location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll("nav.main a").forEach(function (a) {
      if (a.getAttribute("href") === path) a.classList.add("active");
    });
  });
})();
