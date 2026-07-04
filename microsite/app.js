document.addEventListener('DOMContentLoaded',function(){
// Animated counters
const counters=document.querySelectorAll('.stat-value[data-target]');
counters.forEach(function(counter){
  const target=parseFloat(counter.getAttribute('data-target'));
  const duration=1500;
  const start=performance.now();
  function update(now){
    const elapsed=now-start;
    const progress=Math.min(elapsed/duration,1);
    const eased=1-Math.pow(1-progress,3);
    const current=eased*target;
    if(target>=100) counter.textContent=Math.round(current).toLocaleString();
    else if(target>=10) counter.textContent=current.toFixed(1);
    else counter.textContent=current.toFixed(2);
    if(progress<1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
});

// Table search filter
const searchInput=document.getElementById('corpSearch');
if(searchInput){
  searchInput.addEventListener('input',function(){
    const term=this.value.toLowerCase();
    const rows=document.querySelectorAll('#corpTableBody tr');
    rows.forEach(function(row){
      const text=row.textContent.toLowerCase();
      row.style.display=text.includes(term)?'':'none';
    });
  });
}
});

// Table sort
function sortTable(n){
  const table=document.getElementById('corporateTable');
  if(!table) return;
  const tbody=table.tBodies[0];
  const rows=Array.from(tbody.rows);
  const asc=!table.getAttribute('data-sort-'+n);
  rows.sort(function(a,b){
    let A=a.cells[n].textContent.trim().replace(/[$,%TBMK]/g,'');
    let B=b.cells[n].textContent.trim().replace(/[$,%TBMK]/g,'');
    const aNum=parseFloat(A),bNum=parseFloat(B);
    if(!isNaN(aNum)&&!isNaN(bNum)) return asc?aNum-bNum:bNum-aNum;
    return asc?A.localeCompare(B):B.localeCompare(A);
  });
  rows.forEach(function(r){tbody.appendChild(r)});
  table.setAttribute('data-sort-'+n,asc?'1':'');
}

// Sector pie chart
function drawSectorChart(){
  const canvas=document.getElementById('sectorChart');
  if(!canvas) return;
  const ctx=canvas.getContext('2d');
  const data=[
    {label:'Healthcare',value:8,color:'#4a90d9'},
    {label:'Technology',value:3,color:'#d4af37'},
    {label:'Consumer',value:4,color:'#e8c84a'},
    {label:'Comm Services',value:2,color:'#9b59b6'},
    {label:'Financial',value:1,color:'#2ecc71'},
    {label:'Energy',value:2,color:'#e74c3c'}
  ];
  const total=data.reduce(function(s,d){return s+d.value},0);
  let angle=-Math.PI/2;
  const cx=canvas.width/2,cy=canvas.height/2,radius=100;
  data.forEach(function(slice){
    const sliceAngle=(slice.value/total)*Math.PI*2;
    ctx.beginPath();
    ctx.moveTo(cx,cy);
    ctx.arc(cx,cy,radius,angle,angle+sliceAngle);
    ctx.fillStyle=slice.color;
    ctx.fill();
    ctx.strokeStyle='#0a1628';
    ctx.lineWidth=2;
    ctx.stroke();
    const midAngle=angle+sliceAngle/2;
    const tx=cx+Math.cos(midAngle)*(radius+20);
    const ty=cy+Math.sin(midAngle)*(radius+20);
    ctx.fillStyle='#e0e6f0';
    ctx.font='12px sans-serif';
    ctx.textAlign='center';
    ctx.fillText(slice.label+' ('+slice.value+')',tx,ty);
    angle+=sliceAngle;
  });
  ctx.fillStyle='#0a1628';
  ctx.beginPath();
  ctx.arc(cx,cy,40,0,Math.PI*2);
  ctx.fill();
  ctx.fillStyle='#d4af37';
  ctx.font='bold 16px sans-serif';
  ctx.textAlign='center';
  ctx.fillText('20',cx,cy+5);
  ctx.fillStyle='#8892a8';
  ctx.font='10px sans-serif';
  ctx.fillText('Total',cx,cy+18);
}
