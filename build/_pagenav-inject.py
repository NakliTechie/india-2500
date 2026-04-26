#!/usr/bin/env python3
"""
_pagenav-inject.py — patch a copied india-history.html with the
assets.chiragpatnaik.com page-nav sidebar.

The page-nav widget is asset-host-specific (it fetches /pages.json), so we
don't bake it into the build pipeline's template.html. Instead, deploy.sh
copies the built single-file artifact into the assets repo and then runs
this script to inject the sidebar CSS + HTML+JS in two splice points.

Idempotent: skips injection if the markers are already present.
"""
import sys
from pathlib import Path

CSS_BLOCK = """
  /* page-nav sidebar */
  #pg-toggle{position:fixed;right:0;top:50%;transform:translateY(-50%);background:var(--cream-card);border:1px solid var(--cream-border-soft);border-right:none;border-radius:8px 0 0 8px;padding:12px 7px;cursor:pointer;writing-mode:vertical-rl;font-size:11px;color:var(--cream-muted);letter-spacing:.8px;text-transform:uppercase;z-index:100;font-family:inherit;transition:color .12s;}
  #pg-toggle:hover{color:var(--cream-text);}
  #pg-bd{display:none;position:fixed;inset:0;background:rgba(44,42,36,.15);z-index:150;}
  #pg-bd.open{display:block;}
  #pg-panel{position:fixed;right:-290px;top:0;height:100vh;width:272px;background:var(--cream-card);border-left:1px solid var(--cream-border-soft);z-index:200;display:flex;flex-direction:column;transition:right .2s ease;}
  #pg-panel.open{right:0;}
  #pg-head{display:flex;justify-content:space-between;align-items:center;padding:18px 16px 12px;border-bottom:1px solid var(--cream-border-soft);}
  #pg-head span{font-size:13px;font-weight:500;color:var(--cream-text);}
  #pg-close{background:none;border:none;cursor:pointer;color:var(--cream-muted);font-size:20px;padding:0;line-height:1;font-family:inherit;}
  #pg-close:hover{color:var(--cream-text);}
  #pg-search{margin:10px 14px 6px;padding:7px 10px;font-size:13px;border:1px solid var(--cream-border);border-radius:6px;background:var(--cream);color:var(--cream-text);font-family:inherit;outline:none;}
  #pg-search:focus{border-color:var(--cream-muted);}
  #pg-list{overflow-y:auto;flex:1;padding-bottom:12px;}
  .pg-item{display:block;padding:6px 16px;font-size:13px;color:var(--cream-muted);text-decoration:none;}
  .pg-item:hover{background:rgba(60,45,15,.06);color:var(--cream-text);}
  .pg-item.cur{color:var(--cream-text);font-weight:500;background:rgba(60,45,15,.04);}
  #pg-home{display:block;padding:8px 16px 10px;font-size:12px;color:var(--cream-faint);text-decoration:none;border-bottom:1px solid var(--cream-border-soft);margin-bottom:4px;}
  #pg-home:hover{color:var(--cream-muted);}
  @media(max-width:480px){#pg-panel{width:100%;}}
"""

HTML_BLOCK = """
<button id="pg-toggle" aria-label="Browse all assets">All</button>
<div id="pg-bd"></div>
<aside id="pg-panel" aria-label="All assets">
  <div id="pg-head"><span>All Assets</span><button id="pg-close" aria-label="Close">×</button></div>
  <input id="pg-search" type="search" placeholder="Search…" autocomplete="off" spellcheck="false">
  <a id="pg-home" href="/">← Index</a>
  <div id="pg-list"></div>
</aside>
<script>
(function(){
  var t=document.getElementById('pg-toggle'),p=document.getElementById('pg-panel'),
      b=document.getElementById('pg-bd'),x=document.getElementById('pg-close'),
      s=document.getElementById('pg-search'),l=document.getElementById('pg-list'),
      cur=location.pathname.split('/').pop()||'',all=[];
  function open(){p.classList.add('open');b.classList.add('open');s.focus();}
  function close(){p.classList.remove('open');b.classList.remove('open');}
  t.addEventListener('click',open);b.addEventListener('click',close);x.addEventListener('click',close);
  document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});
  function render(arr){
    l.innerHTML=arr.map(function(a){
      return '<a class="pg-item'+(a.url===cur?' cur':'')+'" href="/'+a.url+'">'+a.title+'</a>';
    }).join('');
  }
  fetch('/pages.json').then(function(r){return r.json();}).then(function(d){
    all=d.sort(function(a,b){return a.title.localeCompare(b.title);});
    render(all);
  });
  s.addEventListener('input',function(){
    var q=s.value.toLowerCase();
    render(q?all.filter(function(a){return a.title.toLowerCase().indexOf(q)>-1;}):all);
  });
})();
</script>
"""

def inject(path: Path) -> bool:
    text = path.read_text()
    if "pg-toggle" in text:
        return False  # already injected; idempotent
    # CSS splice point — last </style> before </head>
    style_close = text.rfind("</style>", 0, text.find("</head>"))
    if style_close == -1:
        raise SystemExit(f"could not find </style> before </head> in {path}")
    # HTML splice point — </body>
    body_close = text.rfind("</body>")
    if body_close == -1:
        raise SystemExit(f"could not find </body> in {path}")
    out = (
        text[:style_close]
        + CSS_BLOCK
        + text[style_close:body_close]
        + HTML_BLOCK
        + text[body_close:]
    )
    path.write_text(out)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: _pagenav-inject.py <path-to-india-history.html>")
    p = Path(sys.argv[1])
    if inject(p):
        print(f"    page-nav sidebar injected into {p.name}")
    else:
        print(f"    page-nav sidebar already present in {p.name}; skipped")
