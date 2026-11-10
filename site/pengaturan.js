(function(){
const $=id=>document.getElementById(id);
const FIELDS=[['GEMINI_API_KEY','Google Gemini API key','LLM gratis (aistudio.google.com/apikey). Dipakai Master Agent, sintesis tesis, dan analisis berita.',1],
 ['GROQ_API_KEY','Groq API key','LLM cepat dengan tingkat gratis (console.groq.com).',1],['OPENROUTER_API_KEY','OpenRouter API key','Satu kunci untuk banyak model, ada model gratis (openrouter.ai/keys).',1],
 ['DEEPSEEK_API_KEY','DeepSeek API key','LLM murah (platform.deepseek.com).',1],['MISTRAL_API_KEY','Mistral API key','console.mistral.ai.',1],['OPENAI_API_KEY','OpenAI API key','platform.openai.com.',1],
 ['NTFY_TOPIC','Topik ntfy.sh (push ke HP, gratis)','Pasang aplikasi ntfy (Android/iOS), langganan topik ini. Pilih nama panjang dan acak, siapa pun yang tahu nama topik bisa membaca notifikasinya.',0],
 ['ALERT_WEBHOOK_URL','Webhook Discord/Slack','URL webhook untuk kirim notifikasi ke kanal Anda.',1],
 ['LLM_PROVIDER','Urutan penyedia LLM (opsional)','Pisahkan koma, contoh: groq,gemini,openrouter. Bila satu gagal atau kena batas laju, otomatis mencoba berikutnya. Kosong = gratis dulu.',0],
 ['LLM_MODELS','Model per penyedia (opsional)','Contoh: groq=llama-3.3-70b-versatile,gemini=gemini-2.5-flash. Isi bila model bawaan ditolak penyedia.',0],['ANTHROPIC_API_KEY','Anthropic API key','Penalaran LLM Master Agent dan sintesis tesis (opsional, berbayar per pemakaian).',1],
 ['CG_API_KEY','CoinGecko Demo API key','Gratis di coingecko.com/en/api. Mengatasi pengayaan detail yang hanya 2 dari 20 kandidat karena batas laju.',1],
 ['DUNE_API_KEY','Dune API key','Untuk smart money (kunci gratis tersedia di dune.com).',1],['DUNE_QUERY_ID','Dune Query ID','Angka ID query Anda (kolom: symbol, net_flow_usd_7d, net_flow_usd_14d, wallets_buying, wallets_selling).',0],
 ['X_BEARER_TOKEN','X (Twitter) Bearer token','Sinyal sosial dari X; API X berbayar.',1],['X_ANALYSTS','Akun analis X','Pisahkan dengan koma, tanpa @. Contoh: LarkDavis,AltcoinGordon',0],
 ['CRYPTOPANIC_KEY','CryptoPanic key','Sumber berita tambahan (opsional).',1],
 ['TELEGRAM_BOT_TOKEN','Telegram bot token','Alert ke Telegram. Gunakan token baru; yang lama sudah bocor di chat.',1],['TELEGRAM_CHAT_ID','Telegram chat ID','ID chat tujuan alert.',0]];
const FILES=['thesis_events.json','smartmoney.json','unlocks.json','catalysts.json','buyback.json','macro.json','founders.json'];
const TPL={'thesis_events.json':o=>{(o.events=o.events||[]).push({theme:'stablecoin',date:new Date().toISOString().slice(0,10),note:'isi catatan Anda',source:'https://',horizon:'Q1 2027'})},
 'smartmoney.json':o=>{(o.coins=o.coins||{}).SIMBOL={net_flow_usd_7d:0,net_flow_usd_14d:0,wallets_buying:0,wallets_selling:0,as_of:new Date().toISOString().slice(0,10)}},
 'unlocks.json':o=>{o.SIMBOL=[{date:'2027-01-01',pct_circ:5,note:'isi'}]},'catalysts.json':o=>{(o.events=o.events||[]).push({symbol:'SIMBOL',date:'2027-01-01',type:'listing',polarity:1,note:'isi',source:'https://'})}};
const st={sha:null};
const SETK='cs_set';let SET=new Set();try{SET=new Set(JSON.parse(localStorage.getItem(SETK)||'[]'))}catch(e){}
function persistSet(){try{localStorage.setItem(SETK,JSON.stringify([...SET]))}catch(e){}}
function markSet(){FIELDS.forEach(f=>{const i=$('f_'+f[0]),b=document.querySelector('.stgset[data-n="'+f[0]+'"]');if(!i)return;const on=SET.has(f[0]);
 i.classList.toggle('filled',on);i.placeholder=on?'terisi ••••••••  (ketik untuk mengganti)':f[1];if(b){b.textContent=on?'✓ terisi':'· belum';b.className='stgset '+(on?'ok':'')}})}
try{$('sAuto').checked=localStorage.getItem('cs_auto')!=='0';$('sAuto').onchange=()=>{try{localStorage.setItem('cs_auto',$('sAuto').checked?'1':'0')}catch(e){}}}catch(e){}
markSet();
function tab(id){document.querySelectorAll('.stgpnl').forEach(p=>p.hidden=p.id!==id);document.querySelectorAll('.stgtab').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.t===id)))}
document.querySelectorAll('.stgtab').forEach(b=>b.onclick=()=>tab(b.dataset.t));
function chip(on,t){const c=$('gChip');c.dataset.on=on?'1':'0';$('gChipTxt').textContent=t}
try{const th=JSON.parse(localStorage.getItem('cs.theme')||'"system"');if(th==='light'||th==='dark')document.documentElement.setAttribute('data-theme',th);
 $('bTheme').onclick=()=>{const n=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);try{localStorage.setItem('cs.theme',JSON.stringify(n))}catch(e){}}}catch(e){}
const sf=$('sFields');sf.innerHTML=FIELDS.map(f=>`<div class="stgf"><label for="f_${f[0]}">${f[0]} <span class="stgset" data-n="${f[0]}"></span></label><input class="field" id="f_${f[0]}" type="${f[3]?'password':'text'}" autocomplete="off" spellcheck="false" placeholder="${f[1]}"><small>${f[2]}</small></div>`).join('');
$('cFile').innerHTML=FILES.map(f=>`<option>${f}</option>`).join('');markSet();
try{const m=location.hostname.match(/^([^.]+)\.github\.io$/),r=location.pathname.split('/')[1];
 $('gOwner').value=localStorage.getItem('cs_owner')||(m?m[1]:'');$('gRepo').value=localStorage.getItem('cs_repo')||(r&&!/\.html?$/.test(r)?r:'crypto-sastra');
 const t=localStorage.getItem('cs_tok');if(t){$('gTok').value=t;$('gRemember').checked=true}}catch(e){$('gRepo').value='crypto-sastra'}
const say=(id,t,k)=>{const e=$(id);e.textContent=t;e.className='mut stgmsg'+(k?' '+k:'')};
const B64={enc:s=>{const b=new TextEncoder().encode(s);let x='';b.forEach(c=>x+=String.fromCharCode(c));return btoa(x)},dec:s=>new TextDecoder().decode(Uint8Array.from(atob(s.replace(/\s/g,'')),c=>c.charCodeAt(0)))};
function cfg(){const o=$('gOwner').value.trim(),r=$('gRepo').value.trim(),t=$('gTok').value.trim();if(!o||!r||!t)throw new Error('Isi pemilik, nama repo, dan token GitHub di langkah 1.');
 try{localStorage.setItem('cs_owner',o);localStorage.setItem('cs_repo',r);if($('gRemember').checked)localStorage.setItem('cs_tok',t);else localStorage.removeItem('cs_tok')}catch(e){}
 return {o,r,t}}
async function gh(method,path,body){const c=cfg();
 const r=await fetch('https://api.github.com/repos/'+c.o+'/'+c.r+path,{method,headers:{'Authorization':'Bearer '+c.t,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 if(r.status===204)return {};let j={};try{j=await r.json()}catch(e){}
 if(!r.ok){const m=j.message||('HTTP '+r.status);throw new Error(r.status===401?'Token ditolak (salah atau kedaluwarsa).':r.status===403||r.status===404?m+' — periksa izin token (Secrets, Actions, Contents: read and write) dan bahwa repo dipilih.':m)}
 return j}
async function listSecrets(){try{const j=await gh('GET','/actions/secrets?per_page=100');const have=new Set((j.secrets||[]).map(s=>s.name));
 SET=new Set([...have].filter(n=>FIELDS.some(f=>f[0]===n)));persistSet();markSet();return have}catch(e){return null}}
$('gTest').onclick=async()=>{say('gMsg','Menguji…');try{const r=await gh('GET','');const h=await listSecrets();say('gMsg','Terhubung ke '+r.full_name+(h?' · '+h.size+' secret terpasang.':'. Izin Secrets belum cukup.'),'good');chip(true,r.full_name||($('gOwner').value+'/'+$('gRepo').value));if(h)setTimeout(()=>tab('p2'),700)}catch(e){say('gMsg',e.message,'err');chip(false,'belum terhubung')}};
$('nTest').onclick=async()=>{const t=($('f_NTFY_TOPIC').value||'').trim();if(!t){say('sMsg','Isi topik ntfy dulu untuk mengirim tes.','err');return}
 try{const r=await fetch('https://ntfy.sh/'+encodeURIComponent(t),{method:'POST',body:'Tes dari Crypto Sastra: notifikasi aktif.',headers:{Title:'Tes Crypto Sastra'}});say('sMsg',r.ok?'Tes terkirim ke ntfy. Cek HP Anda.':'ntfy menolak (HTTP '+r.status+').',r.ok?'good':'err')}catch(e){say('sMsg','Gagal menghubungi ntfy.sh.','err')}};
$('sSave').onclick=async()=>{
 const vals=FIELDS.map(f=>[f[0],$('f_'+f[0]).value.trim()]).filter(x=>x[1]);if(!vals.length){say('sMsg','Tidak ada kolom yang diisi.','err');return}
 say('sMsg','Mengambil kunci enkripsi repo…');
 try{const pk=await gh('GET','/actions/secrets/public-key');const done=[];
  for(const [n,v] of vals){await gh('PUT','/actions/secrets/'+n,{encrypted_value:SB.seal(v,pk.key),key_id:pk.key_id});done.push(n);SET.add(n);$('f_'+n).value=''}persistSet();markSet();
  say('sMsg','Tersimpan: '+done.join(', ')+'.'+($('sAuto').checked?' Menerapkan ke pengumpul…':' Tekan "Terapkan" agar pengumpul memakainya.'),'good');if($('sAuto').checked)await applyNow()}catch(e){say('sMsg',e.message,'err')}};
async function applyNow(){say('sMsg','Menghentikan pengumpul lama…');
 try{let n=0;for(const s of ['in_progress','queued']){const j=await gh('GET','/actions/workflows/collect.yml/runs?status='+s+'&per_page=20');for(const r of j.workflow_runs||[]){try{await gh('POST','/actions/runs/'+r.id+'/cancel');n++}catch(e){}}}
  await new Promise(r=>setTimeout(r,6000));await gh('POST','/actions/workflows/collect.yml/dispatches',{ref:'main'});
  say('sMsg','Pengumpul baru dimulai ('+n+' proses lama dihentikan). Data baru muncul dalam beberapa menit.','good');setTimeout(showRuns,8000)}catch(e){say('sMsg',e.message,'err')}}
$('sRestart').onclick=applyNow;
async function showRuns(){try{const j=await gh('GET','/actions/workflows/collect.yml/runs?per_page=3');$('sStatus').innerHTML='<p class="mut" style="font-size:13px;margin:6px 0">Proses terakhir: '+(j.workflow_runs||[]).map(r=>r.status+(r.conclusion?'/'+r.conclusion:'')+' ('+new Date(r.created_at).toLocaleTimeString('id-ID')+')').join(' · ')+'</p>'}catch(e){}}
$('cLoad').onclick=async()=>{const f=$('cFile').value;say('cMsg','Memuat…');try{const j=await gh('GET','/contents/'+f+'?ref=main');st.sha=j.sha;$('cText').value=B64.dec(j.content);say('cMsg',f+' dimuat.')}catch(e){say('cMsg',e.message,'err')}};
$('cTpl').onclick=()=>{const f=$('cFile').value;try{const o=JSON.parse($('cText').value||'{}');(TPL[f]||(()=>{throw new Error('Tidak ada contoh untuk file ini.')}))(o);$('cText').value=JSON.stringify(o,null,1);say('cMsg','Baris contoh ditambahkan: ganti isinya lalu simpan.')}catch(e){say('cMsg',e.message,'err')}};
$('cSave').onclick=async()=>{const f=$('cFile').value;let o;try{o=JSON.parse($('cText').value)}catch(e){say('cMsg','JSON tidak valid: '+e.message,'err');return}
 if(!st.sha){say('cMsg','Muat file dulu sebelum menyimpan.','err');return}
 say('cMsg','Menyimpan…');try{const j=await gh('PUT','/contents/'+f,{message:'config via web: '+f,content:B64.enc(JSON.stringify(o,null,1)+'\n'),sha:st.sha,branch:'main'});st.sha=j.content.sha;say('cMsg',f+' tersimpan. Dibaca pengumpul pada siklus berikutnya.','good')}catch(e){say('cMsg',e.message,'err')}};
$('cFile').onchange=()=>{st.sha=null;$('cText').value=''};
})();
