// Progressive enhancement only: every table is fully rendered without JS.
(function () {
  function attach(input) {
    var table = document.querySelector(input.dataset.for);
    if (!table) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    input.addEventListener('input', function () {
      var q = input.value.toLowerCase().trim();
      rows.forEach(function (tr) {
        tr.style.display = !q || tr.textContent.toLowerCase().indexOf(q) !== -1 ? '' : 'none';
      });
    });
  }
  document.querySelectorAll('input.filter[data-for]').forEach(attach);

  // click-to-sort on numeric/text columns
  document.querySelectorAll('table.sortable thead th').forEach(function (th, idx) {
    th.style.cursor = 'pointer';
    th.title = 'Click to sort';
    th.addEventListener('click', function () {
      var table = th.closest('table');
      var body = table.querySelector('tbody');
      var rows = Array.prototype.slice.call(body.querySelectorAll('tr'));
      var dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
      th.dataset.dir = dir;
      rows.sort(function (a, b) {
        var x = a.children[idx] ? a.children[idx].textContent.trim() : '';
        var y = b.children[idx] ? b.children[idx].textContent.trim() : '';
        var nx = parseFloat(x.replace(/[^0-9.\-]/g, ''));
        var ny = parseFloat(y.replace(/[^0-9.\-]/g, ''));
        var numeric = !isNaN(nx) && !isNaN(ny) && x.indexOf('http') !== 0;
        var c = numeric ? nx - ny : x.localeCompare(y);
        return dir === 'asc' ? c : -c;
      });
      rows.forEach(function (r) { body.appendChild(r); });
    });
  });
})();
