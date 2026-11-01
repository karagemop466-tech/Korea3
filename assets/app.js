/* Tiny enhancements: table filtering and a "count" badge refresh. No dependencies. */
(function () {
  "use strict";

  function addFilters() {
    document.querySelectorAll("section").forEach(function (section) {
      var scroll = section.querySelector(".scroll > table");
      if (!scroll) return;
      var rows = scroll.querySelectorAll("tbody tr");
      if (rows.length < 12) return;
      var box = document.createElement("div");
      box.className = "filter";
      box.innerHTML = '<label for="f"></label><input id="f" type="search" placeholder="Filter this table (e.g. a team, a season, PASS)…" aria-label="Filter table">';
      scroll.parentNode.parentNode.insertBefore(box, scroll.parentNode);
      var input = box.querySelector("input");
      input.addEventListener("input", function () {
        var q = input.value.trim().toLowerCase();
        var shown = 0;
        rows.forEach(function (tr) {
          var hit = !q || tr.textContent.toLowerCase().indexOf(q) !== -1;
          tr.style.display = hit ? "" : "none";
          if (hit) shown += 1;
        });
        box.querySelector("label").textContent = shown + " of " + rows.length + " rows";
      });
      box.querySelector("label").textContent = rows.length + " rows";
    });
  }

  function markExternal() {
    document.querySelectorAll('a[target="_blank"]').forEach(function (a) {
      a.setAttribute("title", "Opens in a new tab");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    addFilters();
    markExternal();
  });
})();
