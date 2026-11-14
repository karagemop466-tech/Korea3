// Row filter for long tables. No network, no dependencies, no analytics.
(function () {
  "use strict";
  function ready(fn) {
    if (document.readyState !== "loading") { fn(); } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }
  ready(function () {
    var inputs = document.querySelectorAll("input[data-filter]");
    Array.prototype.forEach.call(inputs, function (input) {
      var sel = input.getAttribute("data-filter");
      var table = document.querySelector(sel);
      if (!table) { return; }
      var counter = document.querySelector('[data-count-for="' + input.id + '"]');
      var rows = table.querySelectorAll("tbody tr");
      function apply() {
        var q = input.value.trim().toLowerCase();
        var shown = 0;
        Array.prototype.forEach.call(rows, function (tr) {
          var hit = q === "" || tr.textContent.toLowerCase().indexOf(q) !== -1;
          tr.style.display = hit ? "" : "none";
          if (hit) { shown += 1; }
        });
        if (counter) {
          counter.textContent = shown + " of " + rows.length + " rows";
        }
      }
      input.addEventListener("input", apply);
      if (counter) { apply(); }
    });
  });
})();
