import re
p = "site/crypto-sastra.src.html"; s = open(p, encoding="utf-8").read()
assert "id=\"hunter\"" not in s, "sudah dipatch"

# --- meta, nav, brand
s = s.replace('content="Crypto Sastra: radar berita crypto realtime dengan skor, dampak, aksi, estimasi exit, dan pengukuran akurasi sinyal."',
              'content="Crypto Sastra: pemburu altcoin kecil yang undervalue dan masih sepi dibahas, plus radar berita crypto, scan institusional, dan pengukuran akurasi sinyal."')
s = s.replace('<a class="brand" href="#radar"', '<a class="brand" href="#hunter"')
s = s.replace('<a href="#radar">Radar</a><a href="#top5">Top 5</a>', '<a href="#hunter">Hunter</a><a href="#radar-top">Radar</a><a href="#top5">Top 5</a>')

# --- hero lama -> kepala bagian Radar; hero baru + bagian Hunter
old_hero = re.search(r'<section class="wrap hero">.*?</section>\n', s, re.S).group(0)
radar_head = old_hero.replace('<section class="wrap hero">', '<section class="wrap hero radarhead" id="radar-top">').replace("<h1>", "<h2>").replace("</h1>", "</h2>")
HUNTER = '''<section class="wrap hero" aria-label="Hunter">
  <div>
    <h1>Temukan altcoin <em>undervalue</em> sebelum ramai dibahas.</h1>
    <p>Hunter menyaring ratusan altcoin kecil, menghitung seberapa murah valuasinya terhadap pendapatan dan TVL, lalu mengukur seberapa sepi pembahasannya di Reddit, X, dan CoinGecko Trending. Yang murah dan masih senyap naik ke atas.</p>
  </div>
  <div class="stats" id="hstats" aria-live="polite"></div>
</section>

<section class="wrap hunter" id="hunter" aria-label="Hasil Hunter">
  <div class="bar">
    <div class="seg" role="group" aria-label="Tingkat">
      <button data-tier="" aria-pressed="true">Semua</button>
      <button data-tier="prioritas" aria-pressed="false">Prioritas riset</button>
      <button data-tier="pantau" aria-pressed="false">Pantau</button>
    </div>
    <label class="sr" for="hSort">Urutan</label>
    <select class="field" id="hSort"><option value="score">Skor tertinggi</option><option value="mc">Market cap terkecil</option><option value="ps">Termurah vs pendapatan</option><option value="quiet">Paling senyap</option></select>
    <label class="chk"><input type="checkbox" id="hQuiet" checked> Sembunyikan yang sudah viral</label>
    <span class="count" id="hMeta"></span>
  </div>
  <div id="hList"><div class="scanwait">Memuat hasil Hunter…</div></div>
  <div class="hgrid">
    <section class="panel" id="hManual"></section>
    <section class="panel" id="hAnalyst"></section>
    <section class="panel" id="hSrc"></section>
  </div>
</section>

'''
s = s.replace(old_hero, HUNTER + radar_head, 1)

# --- cara kerja: tambahkan rumus Hunter
s = s.replace('<div class="formula">skor = bobot_event', '<div class="formula">Hunter: skor = valuasi 30 + suplai 15 + diskon dari ATH 10 + likuiditas 10 + fase harga 10 + senyap 25 ± insight analis 8<br>senyap = 25 × (1 − bobot_buzz / 10) · nol bila sudah trending di CoinGecko</div>\n    <div class="formula">skor = bobot_event', 1)

# --- CSS
CSS = '''
/* Hunter */
.hero h2{font-family:var(--f-display);font-weight:500;font-size:clamp(24px,3.2vw,34px);line-height:1.1;letter-spacing:-.02em;margin:0 0 10px;text-wrap:balance}
.radarhead{border-top:1px solid var(--line);margin-top:34px;padding-top:34px}
.hunter{padding-block:6px 28px}
.hc{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow);margin-bottom:10px;min-width:0}
.hc>summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:34px minmax(0,1.5fr) repeat(3,minmax(0,.8fr)) 96px 22px;gap:14px;align-items:center;padding:14px 16px}
.hc>summary::-webkit-details-marker{display:none}
.hc>summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px;border-radius:var(--r)}
.hc .rk{font:italic 500 24px var(--f-display);color:var(--mut)}
.hc .nm b{font-size:16px}.hc .nm small{display:block;color:var(--mut);font-size:12.5px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hc .mt span{display:block;font-size:11px;color:var(--mut);letter-spacing:.04em;text-transform:uppercase}
.hc .mt b{font:600 14px var(--f-mono);font-variant-numeric:tabular-nums}
.hc .sg{font:600 26px/1 var(--f-mono);text-align:right;letter-spacing:-.03em}.hc .sg small{display:block;font:500 11px var(--f-body);color:var(--mut);letter-spacing:0;margin-top:3px}
.hc .chev{width:18px;height:18px;stroke:var(--mut);fill:none;stroke-width:2;transition:transform .15s}
.hc[open] .chev{transform:rotate(180deg)}
.dots{display:flex;gap:3px;margin-top:6px}.dots i{width:9px;height:9px;border-radius:3px;background:var(--surface2);border:1px solid var(--line)}
.dots i.pass{background:var(--up);border-color:var(--up)}.dots i.fail{background:var(--dn);border-color:var(--dn)}
.pill.prioritas{background:var(--up-soft);color:var(--up)}.pill.pantau{background:var(--warn-soft);color:var(--warn)}.pill.lemah{background:var(--surface2);color:var(--mut)}
.pill.viral{background:var(--dn-soft);color:var(--dn)}.pill.quiet{background:var(--accent-soft);color:var(--accent)}
.hbody{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;padding:4px 16px 16px;border-top:1px solid var(--line);padding-top:14px}
.hbody h4{margin:0 0 8px;font:600 11.5px var(--f-body);letter-spacing:.07em;text-transform:uppercase;color:var(--mut)}
.hbody ul{margin:4px 0;padding-left:18px;font-size:14px}.hbody li{margin:3px 0}
.pb{display:grid;grid-template-columns:120px minmax(0,1fr) 54px;gap:8px;align-items:center;font-size:13px;margin:5px 0}
.pb i{display:block;height:6px;border-radius:4px;background:var(--surface2);overflow:hidden}.pb i u{display:block;height:100%;background:var(--accent)}
.pb b{font:600 12.5px var(--f-mono);text-align:right}
.pb em{grid-column:2/-1;font-style:normal;color:var(--mut);font-size:12px;margin-top:-3px}
.ck{display:grid;grid-template-columns:18px minmax(0,1fr);gap:8px;font-size:13.5px;margin:5px 0}
.ck b{font:700 13px var(--f-mono)}.ck.pass b{color:var(--up)}.ck.fail b{color:var(--dn)}.ck.unknown b{color:var(--mut)}
.ck small{display:block;color:var(--mut);font-size:12px}
.hbody .full{grid-column:1/-1}
.src a{word-break:break-word}
.hgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:20px}
.hgrid .panel{margin:0}
.mnote{border-top:1px solid var(--line);padding:10px 0;font-size:14px}.mnote:first-of-type{border-top:0}
.mnote p{margin:3px 0;color:var(--mut)}
.btnl{border:1px solid var(--line);background:var(--surface);color:var(--fg);border-radius:8px;padding:6px 12px;font:600 13px var(--f-body);cursor:pointer;text-decoration:none;display:inline-block}
.btnl:hover{border-color:var(--accent);color:var(--accent)}
@media(max-width:1000px){.hgrid{grid-template-columns:1fr}}
@media(max-width:760px){.hc>summary{grid-template-columns:28px minmax(0,1fr) 78px 20px}.hc>summary .mt{display:none}.hbody{grid-template-columns:1fr}.pb{grid-template-columns:96px minmax(0,1fr) 48px}}
'''
s = s.replace("/* Cara kerja */", CSS + "/* Cara kerja */", 1)

# --- JS
JS = r'''
/* ---------- Hunter ---------- */
/*DEMO_HUNT_START*/const DEMO_HUNT=null;/*DEMO_HUNT_END*/
const H={data:null,tier:'',sort:'score',quiet:true};
const openH=new Set();
const fU=v=>v==null?'-':v>=1e9?'$'+(v/1e9).toFixed(2)+' M':v>=1e6?'$'+(v/1e6).toFixed(v>=1e8?0:1)+' jt':'$'+Math.round(v).toLocaleString('en-US');
const PLB={valuasi:'Valuasi',suplai:'Suplai',drawdown:'Diskon dari ATH',likuiditas:'Likuiditas',fase:'Fase harga',senyap:'Senyap (belum ramai)'};
const TIERLB={prioritas:'Prioritas riset',pantau:'Pantau',lemah:'Lemah'};
const stIc={pass:'✓',fail:'✕',unknown:'?'};
function hVal(c){return c.ps!=null?['MC / pendapatan',c.ps.toFixed(1)+'x']:c.mc_tvl!=null?['MC / TVL',c.mc_tvl.toFixed(2)+'x']:['Valuasi','tidak ada data']}
function hCard(c,i){
  const v=hVal(c),b=c.buzz||{},dd=c.checklist.map(x=>`<i class="${x.status}" title="${esc(x.label)}: ${esc(x.detail)}"></i>`).join('');
  const posts=(b.top||[]).map(t=>`<li><a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(t.title)}</a> <span class="mut">(${esc(t.src)}, ${t.score})</span></li>`).join('');
  const bars=Object.keys(PLB).map(k=>{const p=c.parts[k];return p?`<div class="pb"><span>${PLB[k]}</span><i><u style="width:${p.pts/p.max*100}%"></u></i><b>${p.pts}/${p.max}</b><em>${esc(p.note)}</em></div>`:''}).join('')+(c.bonus?`<div class="pb"><span>Insight analis</span><i></i><b>${c.bonus>0?'+':''}${c.bonus}</b><em>sentimen dari analis/pengguna X yang disebut</em></div>`:'');
  const ck=c.checklist.map(x=>`<div class="ck ${x.status}"><b>${stIc[x.status]}</b><div>${esc(x.label)}<small>${esc(x.detail)}</small></div></div>`).join('');
  const m=c.manual?`<div class="full"><h4>Riset manual (${esc(c.manual.as_of)})</h4><p style="margin:0;font-size:14px">${esc(c.manual.thesis)}</p></div>`:'';
  const L=c.links||{};
  return `<details class="hc" data-id="${esc(c.id)}"${openH.has(c.id)?' open':''}><summary>
    <div class="rk">${i+1}</div>
    <div class="nm"><b>$${esc(c.symbol)}</b> <span class="mut">${esc(c.name)}</span> <span class="pill ${c.tier}">${TIERLB[c.tier]}</span> <span class="pill ${c.viral?'viral':'quiet'}">${c.viral?'sudah ramai':'senyap'}</span><small>${esc(c.category||'Kategori tidak diketahui')} · lolos ${c.pass} dari ${c.known} cek terverifikasi</small><div class="dots" aria-label="Checklist tesis">${dd}</div></div>
    <div class="mt"><span>Market cap</span><b>${fU(c.mc)}</b></div>
    <div class="mt"><span>${v[0]}</span><b>${v[1]}</b></div>
    <div class="mt"><span>FDV / MC</span><b>${c.fdv_mc!=null?c.fdv_mc.toFixed(2):'-'}</b></div>
    <div class="sg">${Math.round(c.score)}<small>dari 100</small></div>
    <svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
  </summary><div class="hbody">
    <div><h4>Rincian skor</h4>${bars}</div>
    <div><h4>Checklist tesis Kalimasada</h4>${ck}</div>
    <div><h4>Mengapa menarik</h4>${c.notes.length?`<ul>${c.notes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="mut" style="margin:0;font-size:14px">Tidak ada keunggulan menonjol yang terukur.</p>'}
      <h4 style="margin-top:14px">Risiko</h4>${c.risks.length?`<ul>${c.risks.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class="mut" style="margin:0;font-size:14px">Tidak ada bendera merah otomatis. Tetap cek unlock dan backer.</p>'}</div>
    <div class="src"><h4>Pembicaraan sosial</h4><p style="margin:0 0 6px;font-size:14px">Reddit ${b.reddit||0} · X ${b.x||0} · analis ${b.analyst||0}${b.sent!=null?' · sentimen '+(b.sent>0?'+':'')+b.sent:''}</p>${posts?`<ul>${posts}</ul>`:'<p class="mut" style="margin:0;font-size:14px">Tidak ada pembahasan terdeteksi minggu ini. Itu yang dicari Hunter.</p>'}
      <p style="margin:12px 0 0;display:flex;gap:8px;flex-wrap:wrap">${L.coingecko?`<a class="btnl" href="${esc(L.coingecko)}" target="_blank" rel="noopener">CoinGecko</a>`:''}${L.defillama?`<a class="btnl" href="${esc(L.defillama)}" target="_blank" rel="noopener">DefiLlama</a>`:''}</p></div>
    ${m}
  </div></details>`}
function renderHunt(){
  const d=H.data;if(!d)return;
  let a=(d.candidates||[]).filter(c=>(!H.tier||c.tier===H.tier)&&(!H.quiet||!c.viral));
  const key={score:c=>-c.score,mc:c=>c.mc,ps:c=>c.ps==null?1e9:c.ps,quiet:c=>(c.buzz&&c.buzz.weight||0)+(c.viral?100:0)}[H.sort];
  a=a.slice().sort((x,y)=>key(x)-key(y));
  const pr=(d.candidates||[]).filter(c=>c.tier==='prioritas').length,sr=d.sources||{};
  const social=(sr.reddit&&sr.reddit.ok?1:0)+(sr.x&&sr.x.ok?1:0);
  $('#hstats').innerHTML=[[(d.candidates||[]).length,'kandidat lolos saringan'],[pr,'prioritas riset'],[d.universe||0,'koin dipindai'],[social+'/2','sumber sosial aktif']].map(c=>`<div class="stat"><b>${c[0]}</b><span>${c[1]}</span></div>`).join('');
  $('#hMeta').textContent=(d.demo?'data contoh · ':'')+(d.generated_at?'diperbarui '+ago(d.generated_at)+' · ':'')+a.length+' ditampilkan';
  $('#hList').innerHTML=a.length?a.map(hCard).join(''):`<div class="scanwait">${(d.candidates||[]).length?'Tidak ada kandidat dengan filter ini. Matikan "sembunyikan yang sudah viral" atau ganti tingkat.':'Hunter belum punya hasil live. Di GitHub, hasil pertama muncul setelah workflow berjalan; sementara itu lihat riset manual di bawah.'}</div>`;
  const mn=d.manual||[];
  $('#hManual').innerHTML=`<h2>Riset manual</h2><p class="sub">Dikumpulkan dari artikel dan data publik, tiap catatan menyebut tanggal datanya.</p>`+(mn.length?mn.map(m=>`<div class="mnote"><b>$${esc(m.symbol)}</b> ${esc(m.name)} <span class="tag">${esc(m.as_of)}</span> <span class="tag">MC ≈ ${fU(m.mc)}</span><p>${esc(m.thesis)}</p><ul style="margin:4px 0;padding-left:18px;font-size:13.5px">${(m.facts||[]).map(f=>`<li>${esc(f)}</li>`).join('')}</ul>${(m.unverified||[]).length?`<p style="font-size:13px">Belum terverifikasi: ${esc(m.unverified.join(', '))}</p>`:''}<a href="${esc(m.source)}" target="_blank" rel="noopener" style="font-size:13px">Sumber</a></div>`).join(''):'<p class="mut">Belum ada.</p>');
  const an=d.analyst_notes||[];
  $('#hAnalyst').innerHTML=`<h2>Catatan analis</h2><p class="sub">Yang disebut analis bukan rekomendasi kami. Dicatat apa adanya beserta tanggal dan sumbernya.</p>`+(an.length?an.map(n=>`<div class="mnote"><b>${esc(n.analyst)}</b> <span class="tag">${esc(n.date)}</span> <span class="mut" style="font-size:12.5px">${esc(n.platform)}</span><p>${esc(n.thesis)}</p><ul style="margin:4px 0;padding-left:18px;font-size:13.5px">${(n.coins||[]).map(c=>`<li><b>$${esc(c.symbol)}</b> <span class="tag">${esc(c.stance)}</span> ${esc(c.note)}</li>`).join('')}</ul><a href="${esc(n.source)}" target="_blank" rel="noopener" style="font-size:13px">Sumber</a></div>`).join(''):'<p class="mut">Belum ada.</p>');
  const rs=sr.reddit||{},xs=sr.x||{};
  $('#hSrc').innerHTML=`<h2>Status sumber</h2><p class="sub">Hunter hanya menilai "senyap" bila sumber sosial terjangkau; bila tidak, nilainya netral.</p><ul style="margin:0;padding-left:18px;font-size:14px;line-height:1.7">
   <li>CoinGecko: ${sr.coingecko?'aktif':'tidak terjangkau'}${d.universe?` (${d.universe} koin)`:''}</li><li>DefiLlama: ${sr.defillama?'aktif':'tidak terjangkau'}</li>
   <li>Reddit: ${rs.ok!=null?rs.ok+' subreddit terbaca, '+rs.fail+' gagal':'-'}${sr.posts!=null?` (${sr.posts} post)`:''}</li>
   <li>X: ${xs.off?'mati (pasang X_BEARER_TOKEN dan X_ANALYSTS)':xs.ok!=null?xs.ok+' kueri berhasil, '+xs.fail+' gagal':'-'}</li>
   <li>CoinGecko Trending: ${sr.trending!=null?sr.trending+' koin ditandai viral':'-'}</li></ul>
   <p class="sub" style="margin:12px 0 0">Skor menyaring bahan riset, bukan sinyal beli. Verifikasi backer, unlock, dan kontrak sendiri sebelum bertindak.</p>`;
}
async function initHunt(){
  try{H.data=(S.demo&&DEMO_HUNT)?DEMO_HUNT:await getJSON('/api/hunt')}catch(e){H.data={candidates:[],manual:[],analyst_notes:[],sources:{}}}
  if(!(H.data.manual||[]).length&&!(H.data.candidates||[]).length&&DEMO_HUNT)H.data=DEMO_HUNT;
  renderHunt();
}
$$('#hunter [data-tier]').forEach(b=>b.onclick=()=>{H.tier=b.dataset.tier;$$('#hunter [data-tier]').forEach(x=>x.setAttribute('aria-pressed',x===b));renderHunt()});
$('#hSort').onchange=e=>{H.sort=e.target.value;renderHunt()};
$('#hQuiet').onchange=e=>{H.quiet=e.target.checked;renderHunt()};
$('#hList').addEventListener('toggle',e=>{const d=e.target;if(d.tagName==='DETAILS'&&d.dataset.id){d.open?openH.add(d.dataset.id):openH.delete(d.dataset.id)}},true);
setInterval(()=>{if(S.static||true)initHuntQuiet()},300000);
async function initHuntQuiet(){try{const r=await getJSON('/api/hunt');if((r.candidates||[]).length){H.data=r;renderHunt()}}catch(e){}}
'''
s = s.replace("/* ---------- interaksi ---------- */", JS + "\n/* ---------- interaksi ---------- */", 1)
s = s.replace("'/api/scan/index':'data/scan/index.json'};", "'/api/scan/index':'data/scan/index.json','/api/hunt':'data/hunt.json'};", 1)
s = s.replace("initScan();return}", "initScan();initHunt();return}", 1)
s = s.replace("renderAll();await loadSide();initScan();", "renderAll();await loadSide();initScan();initHunt();", 1)
open(p, "w", encoding="utf-8").write(s)
print("OK")
