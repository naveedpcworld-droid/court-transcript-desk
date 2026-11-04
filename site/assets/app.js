const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
let DATA = [], activeTopic = "all";

function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function fmtDate(s){if(!s)return""; const d=new Date(s); return isNaN(d)?"":d.toLocaleDateString(undefined,{year:"numeric",month:"short",day:"numeric"});}
function fmtViews(n){return Number(n||0).toLocaleString();}

async function load(){
  const [idx, stats] = await Promise.all([
    fetch("data/index.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({videos:[]})),
    fetch("data/stats.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({})),
  ]);
  DATA = idx.videos || [];
  const total = stats.videos ?? DATA.length;
  const transcripts = stats.transcripts ?? DATA.filter(v=>v.transcript_status==="ok").length;
  $("#s-videos").textContent = total.toLocaleString();
  $("#s-transcripts").textContent = transcripts.toLocaleString();
  $("#s-channels").textContent = (stats.channels ?? 0).toLocaleString();
  $("#s-latest").textContent = stats.latest_date ? fmtDate(stats.latest_date) : "—";
  const topics = stats.topics || {};
  const chips = $("#chips");
  const all = document.createElement("button");
  all.className = "chip active"; all.textContent = "All"; all.dataset.topic = "all";
  chips.appendChild(all);
  Object.entries(topics).sort((a,b)=>b[1]-a[1]).slice(0,12).forEach(([k,n])=>{
    const b=document.createElement("button"); b.className="chip"; b.dataset.topic=k; b.textContent=`${k} (${n})`; chips.appendChild(b);
  });
  render();
}

function filtered(){
  const q = ($("#search").value || "").toLowerCase().trim();
  const sort = $("#sort").value;
  let rows = DATA.filter(v=>{
    const hay = `${v.title} ${v.channel_name} ${v.judge} ${v.court} ${(v.topic_labels||[]).join(" ")} ${v.stage} ${v.outcome}`.toLowerCase();
    const okQ = !q || hay.includes(q);
    const okT = activeTopic==="all" || (v.topics||[]).includes(activeTopic);
    return okQ && okT;
  });
  if(sort==="oldest") rows.sort((a,b)=>(a.published||"").localeCompare(b.published||""));
  else if(sort==="views") rows.sort((a,b)=>(b.views||0)-(a.views||0));
  else rows.sort((a,b)=>(b.published||"").localeCompare(a.published||""));
  return rows;
}

function render(){
  const rows = filtered();
  $("#count").textContent = `${rows.length.toLocaleString()} of ${DATA.length.toLocaleString()} videos`;
  $("#grid").innerHTML = rows.slice(0,300).map(v=>{
    const st = v.transcript_status==="ok" ? `<span class="badge">Transcript</span>` : `<span class="badge warn">${esc(v.transcript_status.replaceAll("_"," "))}</span>`;
    return `<article class="card"><h3><a href="video.html?id=${encodeURIComponent(v.id)}">${esc(v.title)}</a></h3>
      <div class="meta">${esc(v.channel_name)} · ${fmtDate(v.published)} · ${esc(v.duration_fmt||"")}</div>
      <div class="meta">${esc(v.judge||"Judge not detected")} · ${esc(v.court||"")}</div>
      <div class="chips">${(v.topic_labels||[]).slice(0,3).map(t=>`<span class="chip">${esc(t)}</span>`).join("")}</div>
      <div class="foot">${st}<span>${fmtViews(v.views)} views</span></div></article>`;
  }).join("") || `<div class="empty">No published transcripts yet. The scheduled GitHub Action will add them.</div>`;
}

document.addEventListener("DOMContentLoaded", ()=>{
  $("#search")?.addEventListener("input", render);
  $("#sort")?.addEventListener("change", render);
  $("#chips")?.addEventListener("click", (e)=>{
    const b=e.target.closest(".chip"); if(!b)return;
    activeTopic=b.dataset.topic; $$(".chip").forEach(x=>x.classList.toggle("active",x===b)); render();
  });
  load();
});
