"""Interactive HTML report renderer — single self-contained file with D3.js."""

from __future__ import annotations

import html
import json
from pathlib import Path

from lens.models import ProjectAnalysis


def render_html(analysis: ProjectAnalysis, output_path: Path | None = None) -> Path:
    """Generate a self-contained interactive HTML report.

    All CSS, JS, and data are inlined. Works completely offline.
    """
    if output_path is None:
        output_path = Path("lens-report.html")

    project_name = html.escape(analysis.root_path.rstrip("/").split("/")[-1])
    data = _build_data_payload(analysis)
    data_json = json.dumps(data, default=str)

    html_content = _HTML_TEMPLATE.replace("{{PROJECT_NAME}}", project_name)
    html_content = html_content.replace("{{DATA_JSON}}", data_json)

    output_path.write_text(html_content, encoding="utf-8")
    return output_path


def _build_data_payload(analysis: ProjectAnalysis) -> dict:
    """Build the JSON data payload for the HTML report."""
    return {
        "project": {
            "name": analysis.root_path.rstrip("/").split("/")[-1],
            "language": analysis.detection.primary_language.value,
            "frameworks": [f.value for f in analysis.detection.frameworks],
            "architecture": analysis.architecture.value,
            "packageManager": analysis.detection.package_manager,
            "hasTests": analysis.detection.has_tests,
            "hasCi": analysis.detection.has_ci,
            "hasDocker": analysis.detection.has_docker,
        },
        "stats": {
            "totalFiles": analysis.stats.total_files,
            "codeLines": analysis.stats.code_lines,
            "blankLines": analysis.stats.blank_lines,
            "commentLines": analysis.stats.comment_lines,
            "totalLines": analysis.stats.total_lines,
            "languageBreakdown": analysis.stats.language_breakdown,
            "languagePercentages": analysis.stats.language_percentages,
            "fileCountByLanguage": analysis.stats.file_count_by_language,
            "largestFiles": [
                {"path": p, "size": s} for p, s in analysis.stats.largest_files
            ],
        },
        "files": [
            {
                "path": f.relative_path,
                "language": f.language.value,
                "lines": f.code_lines,
                "size": f.size_bytes,
            }
            for f in analysis.files
        ],
        "dependencies": [
            {"source": d.source, "target": d.target, "names": d.import_names}
            for d in analysis.dependencies
        ],
        "externalDeps": analysis.external_deps,
        "circularDeps": analysis.circular_deps,
        "hotspots": [
            {
                "path": h.file_path,
                "score": h.score,
                "churn": h.change_frequency,
                "complexity": h.complexity,
                "danger": h.is_danger_zone,
            }
            for h in analysis.hotspots
        ],
        "entryPoints": analysis.entry_points,
        "explanation": analysis.explanation,
        "gitHistory": [
            {
                "path": g.file_path,
                "commits": g.commit_count,
                "contributors": g.contributors,
                "lastModified": g.last_modified,
            }
            for g in analysis.git_history
        ],
    }


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lens — {{PROJECT_NAME}}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--text:#e6edf3;--text-dim:#8b949e;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;--purple:#bc8cff;--cyan:#39d2c0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;overflow-x:hidden}
.layout{display:grid;grid-template-columns:280px 1fr;grid-template-rows:auto 1fr;height:100vh}
header{grid-column:1/-1;background:var(--surface);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;gap:16px}
header h1{font-size:18px;font-weight:600}
header .badge{background:var(--border);padding:2px 8px;border-radius:12px;font-size:12px;color:var(--text-dim)}
.sidebar{background:var(--surface);border-right:1px solid var(--border);overflow-y:auto;padding:12px 0}
.sidebar-section{padding:8px 16px}
.sidebar-section h3{font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-dim);margin-bottom:8px}
.file-tree{list-style:none;font-size:13px}
.file-tree li{padding:3px 8px;cursor:pointer;border-radius:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.file-tree li:hover{background:rgba(88,166,255,0.1)}
.file-tree li.dir{color:var(--accent);font-weight:500}
.file-tree li.entry{color:var(--green)}
.file-tree li.danger{color:var(--red)}
.main{overflow-y:auto;padding:24px}
.dashboard{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:24px}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px}
.stat-card .label{font-size:12px;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.5px}
.stat-card .value{font-size:28px;font-weight:700;margin-top:4px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:20px;margin-bottom:16px}
.card h2{font-size:16px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.lang-bar{height:12px;border-radius:6px;overflow:hidden;display:flex;margin:8px 0}
.lang-bar span{display:inline-block;height:100%}
.lang-legend{display:flex;flex-wrap:wrap;gap:12px;font-size:13px;color:var(--text-dim)}
.lang-legend .dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}
.dep-graph{width:100%;height:500px;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:var(--bg)}
.dep-graph svg{width:100%;height:100%}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;border-bottom:2px solid var(--border);color:var(--text-dim);font-size:11px;text-transform:uppercase;letter-spacing:0.5px}
td{padding:8px 12px;border-bottom:1px solid var(--border)}
tr:hover td{background:rgba(88,166,255,0.04)}
.score{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600}
.score-high{background:rgba(248,81,73,0.15);color:var(--red)}
.score-mid{background:rgba(210,153,34,0.15);color:var(--yellow)}
.score-low{background:rgba(63,185,80,0.15);color:var(--green)}
.search-box{width:100%;padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:13px;margin-bottom:12px}
.search-box:focus{outline:none;border-color:var(--accent)}
.tag{display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;margin:1px;background:var(--border);color:var(--text-dim)}
.explanation{font-size:15px;line-height:1.7;color:var(--text);padding:4px 0}
.treemap{width:100%;height:400px}
.heatmap{display:grid;grid-template-columns:repeat(52,1fr);gap:2px}
.heatmap-cell{width:100%;aspect-ratio:1;border-radius:2px;background:var(--border)}
#tooltip{position:fixed;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-size:12px;pointer-events:none;z-index:1000;display:none;max-width:300px;box-shadow:0 4px 12px rgba(0,0,0,0.4)}
</style>
</head>
<body>
<div class="layout">
<header>
<h1>LENS</h1>
<span class="badge" id="projName"></span>
<span class="badge" id="projLang"></span>
<span class="badge" id="projArch"></span>
</header>
<aside class="sidebar">
<div class="sidebar-section">
<input type="text" class="search-box" id="searchBox" placeholder="Search files...">
</div>
<div class="sidebar-section">
<h3>Files</h3>
<ul class="file-tree" id="fileTree"></ul>
</div>
</aside>
<main class="main" id="mainContent">
<div class="dashboard" id="dashboard"></div>
<div id="explanationCard"></div>
<div class="card"><h2>Language Breakdown</h2><div class="lang-bar" id="langBar"></div><div class="lang-legend" id="langLegend"></div></div>
<div class="card"><h2>Dependency Graph</h2><div class="dep-graph" id="depGraph"></div></div>
<div class="card"><h2>Hotspots</h2><table id="hotspotsTable"><thead><tr><th>File</th><th>Score</th><th>Churn</th><th>Complexity</th><th>Status</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h2>Largest Files</h2><table id="largestTable"><thead><tr><th>File</th><th>Size</th></tr></thead><tbody></tbody></table></div>
<div class="card"><h2>External Dependencies</h2><div id="extDeps"></div></div>
</main>
</div>
<div id="tooltip"></div>
<script>
const DATA = {{DATA_JSON}};

const LANG_COLORS = {Python:'#3572A5',JavaScript:'#f1e05a',TypeScript:'#3178c6',Go:'#00ADD8',Rust:'#dea584',Java:'#b07219',Ruby:'#701516',PHP:'#4F5D95',C:'#555555','C++':'#f34b7d','C#':'#178600',Swift:'#F05138',Kotlin:'#A97BFF',Shell:'#89e051',HTML:'#e34c26',CSS:'#563d7c',SQL:'#e38c00',Markdown:'#083fa1',YAML:'#cb171e',JSON:'#292929',TOML:'#9c4221',Dockerfile:'#384d54',Other:'#666'};

function init(){
  document.getElementById('projName').textContent=DATA.project.name;
  document.getElementById('projLang').textContent=DATA.project.language;
  document.getElementById('projArch').textContent=DATA.project.architecture;
  renderDashboard();
  renderExplanation();
  renderLangBar();
  renderFileTree(DATA.files);
  renderHotspots();
  renderLargestFiles();
  renderExtDeps();
  renderDepGraph();
  setupSearch();
}

function renderDashboard(){
  const d=document.getElementById('dashboard');
  const cards=[
    {label:'Files',value:DATA.stats.totalFiles.toLocaleString()},
    {label:'Lines of Code',value:DATA.stats.codeLines.toLocaleString()},
    {label:'Languages',value:Object.keys(DATA.stats.languageBreakdown).length},
    {label:'Dependencies',value:DATA.externalDeps.length},
    {label:'Entry Points',value:DATA.entryPoints.length},
    {label:'Hotspots',value:DATA.hotspots.filter(h=>h.danger).length+' danger'},
  ];
  d.innerHTML=cards.map(c=>`<div class="stat-card"><div class="label">${c.label}</div><div class="value">${c.value}</div></div>`).join('');
}

function renderExplanation(){
  if(!DATA.explanation)return;
  document.getElementById('explanationCard').innerHTML=`<div class="card"><h2>Project Overview</h2><p class="explanation">${escapeHtml(DATA.explanation)}</p></div>`;
}

function renderLangBar(){
  const bar=document.getElementById('langBar');
  const legend=document.getElementById('langLegend');
  const pcts=DATA.stats.languagePercentages;
  let barHtml='',legendHtml='';
  for(const[lang,pct]of Object.entries(pcts)){
    if(pct<0.5)continue;
    const c=LANG_COLORS[lang]||'#666';
    barHtml+=`<span style="width:${pct}%;background:${c}" title="${lang}: ${pct}%"></span>`;
    legendHtml+=`<span><span class="dot" style="background:${c}"></span>${lang} ${pct}%</span>`;
  }
  bar.innerHTML=barHtml;
  legend.innerHTML=legendHtml;
}

function renderFileTree(files){
  const tree=document.getElementById('fileTree');
  const entrySet=new Set(DATA.entryPoints);
  const dangerSet=new Set(DATA.hotspots.filter(h=>h.danger).map(h=>h.path));
  const dirs={};
  const sorted=[...files].sort((a,b)=>a.path.localeCompare(b.path));

  let html='';
  for(const f of sorted.slice(0,500)){
    const cls=entrySet.has(f.path)?'entry':dangerSet.has(f.path)?'danger':'';
    html+=`<li class="${cls}" title="${escapeHtml(f.path)} (${f.lines} loc)">${escapeHtml(f.path)}</li>`;
  }
  tree.innerHTML=html;
}

function renderHotspots(){
  const tbody=document.querySelector('#hotspotsTable tbody');
  tbody.innerHTML=DATA.hotspots.slice(0,15).map(h=>{
    const cls=h.score>70?'score-high':h.score>40?'score-mid':'score-low';
    const status=h.danger?'<span class="score score-high">DANGER</span>':'<span class="score score-low">OK</span>';
    return`<tr><td>${escapeHtml(h.path)}</td><td><span class="score ${cls}">${h.score}</span></td><td>${h.churn}</td><td>${h.complexity}</td><td>${status}</td></tr>`;
  }).join('');
}

function renderLargestFiles(){
  const tbody=document.querySelector('#largestTable tbody');
  tbody.innerHTML=DATA.stats.largestFiles.map(f=>`<tr><td>${escapeHtml(f.path)}</td><td>${formatBytes(f.size)}</td></tr>`).join('');
}

function renderExtDeps(){
  const el=document.getElementById('extDeps');
  el.innerHTML=DATA.externalDeps.map(d=>`<span class="tag">${escapeHtml(d)}</span>`).join(' ');
}

function renderDepGraph(){
  const container=document.getElementById('depGraph');
  const w=container.clientWidth||800;
  const h=500;

  if(DATA.dependencies.length===0){
    container.innerHTML='<p style="padding:20px;color:var(--text-dim)">No internal dependencies detected</p>';
    return;
  }

  // Build nodes and links
  const nodeSet=new Set();
  DATA.dependencies.forEach(d=>{nodeSet.add(d.source);nodeSet.add(d.target)});
  const nodes=[...nodeSet].map(id=>({id,label:id.split('/').pop()}));
  const links=DATA.dependencies.map(d=>({source:d.source,target:d.target}));
  const entrySet=new Set(DATA.entryPoints);
  const dangerSet=new Set(DATA.hotspots.filter(h=>h.danger).map(h=>h.path));

  // Simple force-directed layout (no D3 dependency)
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox',`0 0 ${w} ${h}`);

  // Assign initial positions
  const nodeMap={};
  nodes.forEach((n,i)=>{
    const angle=(2*Math.PI*i)/nodes.length;
    n.x=w/2+Math.cos(angle)*(w*0.35);
    n.y=h/2+Math.sin(angle)*(h*0.35);
    n.vx=0;n.vy=0;
    nodeMap[n.id]=n;
  });

  // Simple force simulation
  for(let iter=0;iter<150;iter++){
    // Repulsion
    for(let i=0;i<nodes.length;i++){
      for(let j=i+1;j<nodes.length;j++){
        let dx=nodes[j].x-nodes[i].x;
        let dy=nodes[j].y-nodes[i].y;
        let dist=Math.sqrt(dx*dx+dy*dy)||1;
        let force=500/dist;
        nodes[i].vx-=dx/dist*force;
        nodes[i].vy-=dy/dist*force;
        nodes[j].vx+=dx/dist*force;
        nodes[j].vy+=dy/dist*force;
      }
    }
    // Attraction
    links.forEach(l=>{
      const s=nodeMap[l.source],t=nodeMap[l.target];
      if(!s||!t)return;
      let dx=t.x-s.x,dy=t.y-s.y;
      let dist=Math.sqrt(dx*dx+dy*dy)||1;
      let force=dist*0.01;
      s.vx+=dx/dist*force;s.vy+=dy/dist*force;
      t.vx-=dx/dist*force;t.vy-=dy/dist*force;
    });
    // Center gravity
    nodes.forEach(n=>{
      n.vx+=(w/2-n.x)*0.01;
      n.vy+=(h/2-n.y)*0.01;
      n.x+=n.vx*0.3;n.y+=n.vy*0.3;
      n.vx*=0.7;n.vy*=0.7;
      n.x=Math.max(40,Math.min(w-40,n.x));
      n.y=Math.max(40,Math.min(h-40,n.y));
    });
  }

  // Draw links
  links.forEach(l=>{
    const s=nodeMap[l.source],t=nodeMap[l.target];
    if(!s||!t)return;
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('x1',s.x);line.setAttribute('y1',s.y);
    line.setAttribute('x2',t.x);line.setAttribute('y2',t.y);
    line.setAttribute('stroke','#30363d');line.setAttribute('stroke-width','1');
    svg.appendChild(line);
  });

  // Draw nodes
  const tooltip=document.getElementById('tooltip');
  nodes.forEach(n=>{
    const g=document.createElementNS('http://www.w3.org/2000/svg','g');
    const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');
    circle.setAttribute('cx',n.x);circle.setAttribute('cy',n.y);
    circle.setAttribute('r',6);
    let color='#58a6ff';
    if(entrySet.has(n.id))color='#3fb950';
    if(dangerSet.has(n.id))color='#f85149';
    circle.setAttribute('fill',color);
    circle.style.cursor='pointer';
    g.appendChild(circle);

    const text=document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x',n.x);text.setAttribute('y',n.y-10);
    text.setAttribute('text-anchor','middle');
    text.setAttribute('fill','#8b949e');text.setAttribute('font-size','10');
    text.textContent=n.label;
    g.appendChild(text);

    g.addEventListener('mouseover',e=>{
      tooltip.style.display='block';
      tooltip.style.left=e.clientX+10+'px';
      tooltip.style.top=e.clientY+10+'px';
      tooltip.textContent=n.id;
    });
    g.addEventListener('mouseout',()=>{tooltip.style.display='none'});

    svg.appendChild(g);
  });

  container.appendChild(svg);
}

function setupSearch(){
  const input=document.getElementById('searchBox');
  input.addEventListener('input',()=>{
    const q=input.value.toLowerCase();
    const filtered=q?DATA.files.filter(f=>f.path.toLowerCase().includes(q)):DATA.files;
    renderFileTree(filtered);
  });
}

function escapeHtml(s){
  const d=document.createElement('div');
  d.textContent=s;
  return d.innerHTML;
}

function formatBytes(b){
  if(b<1024)return b+' B';
  if(b<1024*1024)return(b/1024).toFixed(1)+' KB';
  return(b/(1024*1024)).toFixed(1)+' MB';
}

document.addEventListener('DOMContentLoaded',init);
</script>
</body>
</html>"""
