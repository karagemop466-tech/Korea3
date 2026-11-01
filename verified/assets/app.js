
document.addEventListener('input',e=>{if(!e.target.matches('[data-filter]'))return;const q=e.target.value.toLowerCase();const table=document.querySelector(e.target.dataset.filter);if(!table)return;table.querySelectorAll('tbody tr').forEach(tr=>{tr.hidden=!tr.textContent.toLowerCase().includes(q)})});
