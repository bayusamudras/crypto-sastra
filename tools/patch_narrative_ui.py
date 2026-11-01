p = "site/crypto-sastra.src.html"; s = open(p, encoding="utf-8").read()
assert "hSectors" not in s
def rep(a, b, n=1):
    global s
    assert a in s, a[:60]
    s = s.replace(a, b, n)

# hero & stats
rep("Hunter menyaring ratusan altcoin kecil, menghitung seberapa murah valuasinya terhadap pendapatan dan TVL, lalu mengukur seberapa sepi pembahasannya di Reddit, X, dan CoinGecko Trending. Yang murah dan masih senyap naik ke atas.",
    "Hunter lebih dulu melihat ke mana uang dan developer bergerak (sektor, TVL, volume DEX, commit), baru menyaring koin kecil di sektor itu: seberapa murah valuasinya, seberapa sepi pembahasannya di Reddit dan X, dan apa katalis yang akan memicunya.")
rep("""    <label class="chk"><input type="checkbox" id="hQuiet" checked> Sembunyikan yang sudah viral</label>""",
    """    <label class="chk"><input type="checkbox" id="hQuiet" checked> Sembunyikan yang sudah viral</label>
    <label class="chk"><input type="checkbox" id="hHot"> Hanya narasi utama</label>""")
rep("""  <div id="hList"><div class="scanwait">""", """  <section class="panel" id="hSectors" style="margin-bottom:14px"></section>
  <div id="hList"><div class="scanwait">""")
rep('<option value="quiet">Paling senyap</option>', '<option value="quiet">Paling senyap</option><option value="narr">Narrative Score</option>')

# rumus cara kerja
rep("Hunter: skor = valuasi 30 + suplai 15 + diskon dari ATH 10 + likuiditas 10 + fase harga 10 + senyap 25 ± insight analis 8<br>senyap = 25 × (1 − bobot_buzz / 10) · nol bila sudah trending di CoinGecko",
    "Hunter: dasar = valuasi 30 + suplai 15 + diskon ATH 10 + likuiditas 10 + fase harga 10 + senyap 25 ± insight analis 8<br>Narrative Score = TVL_Velocity 40 + Volume_Anomaly 30 + Dev_Activity 20 + Social_Velocity 10 (komponen tak diketahui dihitung netral 30)<br>skor akhir = 0,7 × dasar + 0,3 × Narrative + katalis (−10 sampai +10) − sektor usang 10 − indikasi proyek mati 15")

# CSS
rep("@media(max-width:1000px){.hgrid", """.sect td,.sect th{white-space:nowrap}
.sect .tag.hot{background:var(--up-soft);color:var(--up);font-family:var(--f-body);font-weight:600}
.sect .tag.old{background:var(--surface2);color:var(--mut);font-family:var(--f-body)}
.sect .num{text-align:right;font-variant-numeric:tabular-nums}
.sect .tablebox{max-height:340px;overflow:auto}
.cat{font-size:13.5px;margin:4px 0}.cat b.pos{color:var(--up)}.cat b.neg{color:var(--dn)}
@media(max-width:1000px){.hgrid""")

# JS: kartu
rep("""<span class="pill ${c.viral?'viral':'quiet'}">${c.viral?'sudah ramai':'senyap'}</span><small>${esc(c.category||'Kategori tidak diketahui')} · lolos""",
    """<span class="pill ${c.viral?'viral':'quiet'}">${c.viral?'sudah ramai':'senyap'}</span>${c.ghost?' <span class="pill viral">indikasi proyek mati</span>':''}${c.legacy?' <span class="pill lemah">sektor usang</span>':''}${c.early?' <span class="pill pantau">early-stage</span>':''}<small>${esc((c.sector&&c.sector.tag)||c.category||'Sektor tidak diketahui')}${c.sector&&c.sector.hot?' (narasi utama)':''} · lolos""")
rep("""<div class="sg">${Math.round(c.score)}<small>dari 100</small></div>""", """<div class="sg">${Math.round(c.score)}<small>narasi ${c.narrative_score}</small></div>""")
rep("""  const m=c.manual?""", """  const nn=c.narrative_notes||{},NL={tvl_velocity:'Kecepatan TVL sektor (40%)',volume_anomaly:'Anomali volume (30%)',dev_activity:'Aktivitas developer (20%)',social_velocity:'Kecepatan sosial (10%)'};
  const ntxt={tvl_velocity:(c.sector&&c.sector.tvl_ch7!=null)?`${c.sector.tag}: TVL 7h ${c.sector.tvl_ch7>0?'+':''}${c.sector.tvl_ch7.toFixed(1)}%`:'TVL sektor tidak tersedia (dihitung netral)',volume_anomaly:nn.volume||'-',dev_activity:nn.dev||'-',social_velocity:nn.social||'-'};
  const nbars=Object.keys(NL).map(k=>{const v=c.narrative?c.narrative[k]:null;return `<div class="pb"><span>${NL[k]}</span><i><u style="width:${v==null?0:v}%"></u></i><b>${v==null?'n/a':v}</b><em>${esc(ntxt[k])}</em></div>`}).join('');
  const dx=c.dex?`DEX ${esc(c.dex.chain)}: volume 24j ${fU(c.dex.vol24)}, likuiditas ${fU(c.dex.liq)}, ${c.dex.buys} beli / ${c.dex.sells} jual (${c.dex.pairs} pool)`:(c.enriched?'Tidak ada pool DEX terdeteksi untuk koin ini.':'Belum diperkaya (di luar 20 kandidat teratas).');
  const cats=(c.catalysts||[]).length?(c.catalysts||[]).map(k=>`<div class="cat"><b class="${k.polarity>0?'pos':'neg'}">${k.polarity>0?'＋':'－'}</b> ${esc(k.date)} · ${esc(k.type)}: ${esc(k.note)}${k.source?` <a href="${esc(k.source)}" target="_blank" rel="noopener">sumber</a>`:''}</div>`).join(''):'<p class="mut" style="margin:0;font-size:14px">Tidak ada katalis tercatat. Tambahkan ke <span class="mono">catalysts.json</span> setelah memverifikasi roadmap.</p>';
  const si=(typeof scanIdx!=='undefined'&&scanIdx||[]).find(e=>e.symbol===c.symbol);
  const scanBox=si?`<p style="margin:10px 0 0;font-size:14px">Scan SMC: <b>${si.score.toFixed(1)}/10</b> · ${esc(lblTxt[si.label]||si.label)} <button class="btnl" data-scan="${esc(c.symbol)}" type="button">Buka Scan SMC</button></p>`:(c.scan_ref?'<p class="mut" style="margin:10px 0 0;font-size:13.5px">Belum dipindai SMC. Kandidat bersih tanpa label viral dioper otomatis; pemindaian butuh ≥ 40 minggu candle dari pool DEX.</p>':'<p class="mut" style="margin:10px 0 0;font-size:13.5px">Tanpa pool DEX terdeteksi: Scan SMC tidak bisa dijalankan otomatis.</p>');
  const m=c.manual?""")
rep("""    <div><h4>Mengapa menarik</h4>""", """    <div><h4>Narrative Score ${c.narrative_score}/100 · keyakinan data ${Math.round((c.narrative_conf||0)*100)}%</h4>${nbars}<p style="margin:8px 0 0;font-size:13.5px;color:var(--mut)">Skor dasar ${c.hunter_score}${c.bonus?` (insight analis ${c.bonus>0?'+':''}${c.bonus})`:''}${c.penalty?`, penalti −${c.penalty}`:''}.</p></div>
    <div><h4>Aliran dana, katalis, dan eksekusi</h4><p style="margin:0 0 8px;font-size:14px">${dx}</p>${cats}${scanBox}</div>
    <div><h4>Mengapa menarik</h4>""")
# render: filter, sort, stats, sektor
rep("(!H.tier||c.tier===H.tier)&&(!H.quiet||!c.viral));", "(!H.tier||c.tier===H.tier)&&(!H.quiet||!c.viral)&&(!H.hot||(c.sector&&c.sector.hot)));")
rep("quiet:c=>(c.buzz&&c.buzz.weight||0)+(c.viral?100:0)}[H.sort]", "quiet:c=>(c.buzz&&c.buzz.weight||0)+(c.viral?100:0),narr:c=>-c.narrative_score}[H.sort]")
rep("const H={data:null,tier:'',sort:'score',quiet:true};", "const H={data:null,tier:'',sort:'score',quiet:true,hot:false};")
rep("[d.universe||0,'koin dipindai'],[social+'/2','sumber sosial aktif']]", "[d.universe||0,'koin dipindai'],[(d.top_narratives||[]).length,'narasi utama minggu ini']]")
rep("""  const mn=d.manual||[];""", """  const sc=d.sectors||[],f1=v=>v==null?'-':(v>0?'+':'')+v.toFixed(1)+'%';
  $('#hSectors').innerHTML=`<h2>Narasi minggu ini (top-down)</h2><p class="sub">Sektor diurutkan menurut kecepatan TVL 7 hari. Divergensi = TVL naik lebih cepat daripada harga koin sektor: uang masuk, harga belum menyusul.${(d.top_narratives||[]).length?' Narasi utama: <b>'+d.top_narratives.map(esc).join(', ')+'</b>.':''}</p>`+(sc.length?`<div class="tablebox sect"><table><thead><tr><th>Sektor</th><th class="num">TVL</th><th class="num">TVL 7h</th><th class="num">TVL 30h</th><th class="num">Harga koin 7h</th><th class="num">Divergensi</th><th class="num">Kecepatan</th><th></th></tr></thead><tbody>${sc.map(x=>`<tr><td><b>${esc(x.tag)}</b></td><td class="num">${x.tvl!=null?fU(x.tvl):'-'}</td><td class="num">${f1(x.tvl_ch7)}</td><td class="num">${f1(x.tvl_ch30)}</td><td class="num">${f1(x.price_ch7)}</td><td class="num">${x.divergence!=null?(x.divergence>0?'+':'')+x.divergence.toFixed(0)+' poin':'-'}</td><td class="num">${x.velocity!=null?x.velocity:'-'}</td><td>${x.legacy?'<span class="tag old">usang</span>':(d.top_narratives||[]).includes(x.tag)?'<span class="tag hot">narasi utama</span>':x.divergence>=15?'<span class="tag hot">uang masuk, harga belum</span>':''}</td></tr>`).join('')}</tbody></table></div>`:'<p class="mut" style="margin:0">Belum ada data sektor (DefiLlama belum terjangkau).</p>');
  const mn=d.manual||[];""")
rep("""<li>CoinGecko Trending: ${sr.trending!=null?sr.trending+' koin ditandai viral':'-'}</li></ul>""", """<li>CoinGecko Trending: ${sr.trending!=null?sr.trending+' koin ditandai viral':'-'}</li>
   <li>DexScreener dan detail CoinGecko: ${d.enriched!=null?d.enriched+' kandidat diperkaya':'-'}${sr.dexscreener?' (DEX aktif)':''}</li></ul>
   ${(d.data_gaps||[]).length?`<p class="sub" style="margin:12px 0 4px"><b>Keterbatasan data</b></p><ul style="margin:0;padding-left:18px;font-size:13px;color:var(--mut)">${d.data_gaps.map(g=>`<li>${esc(g)}</li>`).join('')}</ul>`:''}""")
rep("""$('#hQuiet').onchange=e=>{H.quiet=e.target.checked;renderHunt()};""", """$('#hQuiet').onchange=e=>{H.quiet=e.target.checked;renderHunt()};
$('#hHot').onchange=e=>{H.hot=e.target.checked;renderHunt()};
$('#hList').addEventListener('click',e=>{const b=e.target.closest('[data-scan]');if(b){e.preventDefault();openScan(b.dataset.scan)}});""")
open(p, "w", encoding="utf-8").write(s); print("OK")
