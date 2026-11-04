const $ = s => document.querySelector(s);
const esc = v => String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmtDate = s => {if(!s)return"unknown";const d=new Date(s);return isNaN(d)?s:d.toLocaleDateString(undefined,{year:"numeric",month:"long",day:"numeric"});};
const fmtViews = n => Number(n||0).toLocaleString();
const fmtTime = sec => {sec=Math.floor(sec||0);const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;return h?`${h}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`:`${m}:${String(s).padStart(2,"0")}`;};

async function main(){
  const id = new URLSearchParams(location.search).get("id");
  const app = $("#app");
  if(!id){app.innerHTML='<div class="empty">No video id supplied.</div>';return;}
  const idx = await fetch("data/index.json",{cache:"no-store"}).then(r=>r.json()).catch(()=>({videos:[]}));
  const v = (idx.videos||[]).find(x=>x.id===id);
  if(!v){app.innerHTML='<div class="empty">Video not found in the public library. It may be restricted or not yet processed.</div>';return;}
  document.title = `${v.title} · Court Transcript Desk`;
  let tr = null;
  if(v.transcript_url){
    tr = await fetch(v.transcript_url,{cache:"no-store"}).then(r=>r.json()).catch(()=>null);
  }
  const topics = (v.topic_labels||[]).map(t=>`<span class="badge">${esc(t)}</span>`).join(" ");
  const transcript = tr?.segments?.length
    ? `<pre class="transcript">${tr.segments.map(s=>`<span class="ts">[${fmtTime(s.start)}]</span> ${esc(s.text)}\n`).join("")}</pre>`
    : `<div class="note"><strong>No transcript available.</strong> ${esc(v.transcript_status==="blocked_rights"?"This source is marked no-recording.":v.transcript_status==="restricted"?"This source is restricted from public transcript publication.":"YouTube did not expose captions for this video.")}</div>`;
  app.innerHTML = `<article class="panel"><p class="kicker">${esc(v.channel_name)}</p><h1 style="color:var(--ink);font-size:clamp(28px,4vw,46px)">${esc(v.title)}</h1>
    <div class="meta-grid">
      <div><b>Judge</b><br>${esc(v.judge||"Not detected")}</div>
      <div><b>Court</b><br>${esc(v.court||v.channel_name)}</div>
      <div><b>Published</b><br>${esc(fmtDate(v.published))}</div>
      <div><b>Duration</b><br>${esc(v.duration_fmt||"")}</div>
      <div><b>Stage</b><br>${esc(v.stage||"")}</div>
      <div><b>Views</b><br>${fmtViews(v.views)}</div>
    </div>
    <div class="chips">${topics}</div>
    ${v.why?`<div class="note"><strong>Why it matters:</strong> ${esc(v.why)}</div>`:""}
    ${v.outcome?`<p><strong>Outcome signal:</strong> ${esc(v.outcome)}</p>`:""}
    <p><a class="btn" href="${esc(v.url)}" target="_blank" rel="noopener">Watch original on YouTube ↗</a> ${v.transcript_url?`<a class="btn" href="${esc(v.transcript_url)}" target="_blank">Raw JSON</a>`:""}</p>
    <h2>Transcript</h2>${transcript}</article>`;
}
main();
