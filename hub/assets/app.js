/* Table filter for the consolidated dashboard. No network calls, no dependencies. */
(function () {
  "use strict";
  document.querySelectorAll("[data-filter]").forEach(function (input) {
    var target = document.querySelector(input.getAttribute("data-filter"));
    if (!target) return;
    var rows = Array.prototype.slice.call(target.querySelectorAll("tbody tr"));
    var counter = document.querySelector("[data-count-for='" + input.id + "']");
    function apply() {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (row) {
        var match = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = match ? "" : "none";
        if (match) shown += 1;
      });
      if (counter) counter.textContent = shown + " of " + rows.length + " rows";
    }
    input.addEventListener("input", apply);
    apply();
  });
})();
