/* Two affordances, both deliberately small: a text filter for the long tables and a
   count of what is blank on the page, so a reader can see how much of a table the
   publishers left empty instead of assuming the zeros are data. */
(function () {
  function countBlanks() {
    var n = document.querySelectorAll('.blank').length;
    if (!n) return;
    var d = document.createElement('div');
    d.className = 'note';
    d.style.marginTop = '8px';
    d.textContent = 'This page contains ' + n + ' blank marker(s). A blank means no official source '
      + 'published that value; it was left empty rather than filled in.';
    document.querySelector('main').appendChild(d);
  }
  function filterRows() {
    var tables = document.querySelectorAll('table.grid');
    if (tables.length < 2) return;
    var box = document.createElement('input');
    box.type = 'search';
    box.placeholder = 'filter the tables on this page - club, player, keyword';
    box.style.cssText = 'padding:8px 11px;font-size:13.5px;border:1px solid #dfe3e8;border-radius:7px;width:340px;max-width:100%';
    box.setAttribute('aria-label', 'Filter table rows');
    var main = document.querySelector('main');
    main.insertBefore(box, main.querySelector('h2'));
    box.addEventListener('input', function () {
      var q = box.value.trim().toLowerCase();
      tables.forEach(function (t) {
        var shown = 0;
        t.querySelectorAll('tbody tr').forEach(function (tr) {
          var hit = !q || tr.textContent.toLowerCase().indexOf(q) > -1;
          tr.style.display = hit ? '' : 'none';
          if (hit) shown++;
        });
        t.dataset.shown = shown;
      });
    });
  }
  if (document.readyState !== 'loading') { countBlanks(); filterRows(); }
  else document.addEventListener('DOMContentLoaded', function () { countBlanks(); filterRows(); });
})();
