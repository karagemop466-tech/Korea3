
/* games explorer — no dependencies */
(function(){
  var tbody=document.querySelector('#gtab tbody');
  if(!tbody) return;
  var state={rows:[],page:0,size:50,q:"",season:""};
  var q=document.getElementById('q'), seasonSel=document.getElementById('season'),
      resSel=document.getElementById('res'), countEl=document.getElementById('count');
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  fetch('data/games.json').then(function(r){return r.json();}).then(function(d){
    state.rows=d.rows;
    var seasons=Array.from(new Set(d.rows.map(function(r){return r.season;}))).sort(function(a,b){return b-a;});
    seasons.forEach(function(s){var o=document.createElement('option');o.value=s;o.textContent=s;seasonSel.appendChild(o);});
    render();
  }).catch(function(){ tbody.innerHTML='<tr><td colspan="11" class="small">Could not load data/games.json — use the CSV download above.</td></tr>'; });
  function filtered(){
    var out=state.rows;
    if(state.season) out=out.filter(function(r){return String(r.season)===state.season;});
    if(state.q){
      var s=state.q.toLowerCase();
      out=out.filter(function(r){
        return (r.season+' '+r.week+' '+r.home+' '+r.away+' '+r.date).toLowerCase().indexOf(s)>=0;
      });
    }
    return out;
  }
  function render(){
    var rows=filtered();
    var pages=Math.max(1,Math.ceil(rows.length/state.size));
    if(state.page>=pages) state.page=pages-1;
    if(state.page<0) state.page=0;
    var slice=rows.slice(state.page*state.size,(state.page+1)*state.size);
    var html='';
    slice.forEach(function(r){
      var ats=r.ats===1?'<span class="pos">covered</span>':(r.ats===0?'<span class="neg">no</span>':'<span class="small">push</span>');
      var ou=r.ou===1?'<span class="pos">over</span>':(r.ou===0?'<span class="neg">under</span>':'<span class="small">push</span>');
      var sp=r.spread===null?'<span class="small">—</span>':((r.spread>0?'+':'')+r.spread.toFixed(1));
      var tot=r.total===null?'<span class="small">—</span>':r.total.toFixed(1);
      html+='<tr><td>'+r.season+'</td><td>'+r.week+'</td><td>'+esc(r.date)+'</td><td>'
        +esc(r.away)+' @ '+esc(r.home)+'</td><td class="num">'+esc(r.score)+'</td>'
        +'<td class="num">'+(r.margin>0?'+':'')+r.margin+'</td><td class="num">'+sp+'</td>'
        +'<td class="num">'+tot+'</td><td>'+ats+'</td><td>'+ou+'</td>'
        +'<td><a target="_blank" rel="noopener" href="'+esc(r.src)+'">source</a></td></tr>';
    });
    tbody.innerHTML=html||'<tr><td colspan="11" class="small">No matching games.</td></tr>';
    if(countEl) countEl.textContent=rows.length.toLocaleString()+' games · page '+(state.page+1)+' of '+pages;
  }
  if(q) q.addEventListener('input',function(e){state.q=e.target.value;state.page=0;render();});
  if(seasonSel) seasonSel.addEventListener('change',function(e){state.season=e.target.value;state.page=0;render();});
  if(resSel) resSel.addEventListener('change',function(e){state.size=parseInt(e.target.value,10);state.page=0;render();});
  var p=document.getElementById('prev'),n=document.getElementById('next');
  if(p) p.addEventListener('click',function(){state.page--;render();});
  if(n) n.addEventListener('click',function(){state.page++;render();});
})();
