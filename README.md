# Crypto Sastra

Radar berita crypto realtime: mengumpulkan berita dari banyak sumber, memberi skor 0-100, menjelaskan dampak dan alasan,
menyarankan langkah, memperkirakan jendela exit, menebak proyek lain yang ikut terdampak, menampilkan Top 5 proyek paling
berdampak, lalu **mengukur akurasi sinyalnya terhadap harga (vs BTC)** dan mengkalibrasi skor sendiri.

## Struktur
```
scan.py                    mesin Scan Institusional (6 modul + SMC/ICT)
unlocks.json, macro.json   input manual untuk modul 3 dan 5
tests/                     uji mesin scan (python3 tests/test_scan.py)
server.py                  backend: pengumpul berita, analisis, harga, kalibrasi, alert Telegram, API + SSE; --once = satu siklus untuk Actions
.github/workflows/collect.yml  GitHub Actions: loop siklus ~3 menit (tools/loop.sh) yang memanggil dirinya lagi; data ke branch `data`, situs ke gh-pages
static/index.html          website (hasil build, dilayani server)
site/crypto-sastra.src.html sumber website (edit di sini, lalu jalankan: python3 build.py)
Dockerfile, docker-compose.yml, render.yaml, Procfile, .env.example   berkas deploy
```

## Hunter (konsep utama)
`hunter.py` memburu altcoin kecil yang undervalue dan masih sepi dibahas.
1. **Universe**: CoinGecko, market cap $15 jt sampai $400 jt, volume minimal $300 rb (atur lewat `HUNT_MC_MIN`, `HUNT_MC_MAX`, `HUNT_VOL_MIN`).
2. **Fundamental**: DefiLlama (TVL, pendapatan 30 hari) menghitung MC/pendapatan tahunan dan MC/TVL; FDV/MC; diskon dari ATH; likuiditas; fase harga.
3. **Radar sosial**: Reddit (top mingguan 8 subreddit, post "DD/analysis" berbobot lebih), X bila `X_BEARER_TOKEN` dipasang (isi `X_ANALYSTS=akun1,akun2` dengan analis yang Anda percaya; tweet mereka berbobot 2x), dan CoinGecko Trending sebagai penanda sudah viral.
4. **Skor** 0-100 = valuasi 30 + suplai 15 + diskon ATH 10 + likuiditas 10 + fase 10 + senyap 25, plus/minus insight analis (maks 8). Checklist tesis Kalimasada menandai tiap kriteria lolos, gagal, atau tidak diketahui.
5. `hunt_seed.json` memuat riset manual dan catatan analis bertanggal. Tambahkan sendiri. Isi `unlocks.json` agar cek unlock 90 hari terisi.

### Narrative Engine (`narrative.py`)
Hunter bekerja top-down lalu bottom-up:
1. **Sektor**: protokol DefiLlama dijumlahkan per sektor; kecepatan TVL 7 hari dan 30 hari dibandingkan dengan harga koin sektor (divergensi = uang masuk, harga belum). Sektor tanpa TVL (AI, DePIN, ZK) hanya terbaca dari kategori CoinGecko. Sektor usang (yield/farm/algo-stable) dikenai penalti 10.
2. **Narrative Score** per koin = TVL_Velocity 40 + Volume_Anomaly 30 + Dev_Activity 20 + Social_Velocity 10. Komponen yang tidak diketahui dihitung netral 30 dan menurunkan "keyakinan data".
3. **Anomali volume**: DexScreener (volume, likuiditas, beli/jual 24 jam). Vol/MC ≥ 20% dengan harga datar = pola akumulasi. Dompet segar tidak tersedia gratis; rasio beli/jual dipakai sebagai proksi.
4. **Developer**: commit 4 minggu dari CoinGecko. Tanpa commit, tanpa pendapatan, umur > 1 tahun = indikasi proyek mati (penalti 15, tier "lemah").
5. **Early-stage** (< 1 tahun, belum ada pendapatan): valuasi memakai FDV vs median rekan sektor dan aktivitas developer.
6. **Katalis**: `catalysts.json` (manual) dan berita radar 72 jam. Katalis positif ≤ 14 hari +10, ≤ 30 hari +8; katalis negatif (mis. cliff unlock) ≤ 45 hari −10.
7. **Serah-terima**: kandidat bersih teratas dipindai di Scan SMC memakai candle pool DEX (GeckoTerminal) bila tersedia ≥ 40 minggu data (`HUNT_SCAN`, default 2 per siklus).
### Fundamental & Pendapatan (tesis "token = saham")
Komponen ke-3 dengan bobot lebih besar daripada narasi: **P/E** (market cap / pendapatan tahunan, atau P/F dari fee bila pendapatan tak ada) 40 + **pertumbuhan penggunaan** 30 + **buyback / bagi hasil ke holder** 30. Pertumbuhan memakai tren fee 7 hari vs 30 hari sebagai proksi (DAU tidak tersedia gratis). Bagi hasil dihitung otomatis dari pendapatan-holder DefiLlama dan digabung dengan `buyback.json` (model resmi yang Anda verifikasi). Komponen tak diketahui diabaikan dan sisanya dinormalkan; tanpa data sama sekali dihitung netral 30.

**Skor akhir = 0,5 × dasar + 0,3 × Fundamental + 0,2 × Narrative + katalis − penalti.** Catatan: dasar sudah memuat nilai valuasi P/E 30 poin, jadi P/E efektif berbobot sekitar 27% dari skor akhir (sengaja, mengikuti tesis).

Reddit sering menolak IP datacenter (termasuk GitHub Actions). Bila gagal, Hunter menandai sumber sosial tidak terjangkau dan menilai "senyap" netral, bukan menebak. Hasil di GitHub: `data/hunt.json`, diperbarui tiap sekitar 55 menit.

## Scan SMC: komponen yang dideteksi
Struktur swing (BOS/CHoCH), Fair Value Gap, Order Block bullish (candle turun terakhir sebelum displacement; status belum tersentuh/sebagian/terpakai), Liquidity Sweep (wick menembus swing high/low lalu close kembali), equal highs/lows, dan OTE Fib 0,62-0,79. Order Block yang bertumpuk dengan OTE membentuk setup A+ (konfluensi). Semua dihitung di backend dari candle OHLCV (Binance/OKX, atau pool DEX untuk koin kecil).

## Status error di website
Pemuatan data punya batas waktu 12 detik. Bila gagal, muncul bilah pemberitahuan dengan alasannya (timeout, 404, 429) dan tombol "Coba lagi". Data berita lebih dari 30 menit ditandai basi, hasil Hunter lebih dari 3 jam ditandai basi, dan alasan kegagalan sumber (mis. batas API X habis) tampil di panel Status sumber. Website menyegarkan diri saat tab dibuka kembali.

## Jalankan lokal
```bash
python3 server.py            # Python 3.9+, tanpa dependensi
# buka http://localhost:8000
```
Tanpa akses internet ke sumber, server memuat data contoh (diberi label "Contoh"). Uji harga offline: `SIM_PRICES=1 python3 server.py`.

## Scan Institusional (doktrin Kalimasada + SMC/ICT)
Untuk tiap koin (16 koin di `scan.py`) tersedia scan enam modul dan skor akhir /10, sesuai alur institusional:

| Modul | Isi | Sumber gratis |
|---|---|---|
| 1 Narasi dan lifecycle | Fase 1-4 (akumulasi, validasi, euforia, kelelahan) dari drawdown, momentum, SMA-200, volume, dan berita radar; filter Top of Mind (30 besar) | Binance/OKX, CoinGecko |
| 2 On-chain dan fundamental | NVT, MVRV, MC/TVL, pendapatan, aktivitas | CoinMetrics (BTC/ETH), DefiLlama, proxy bila tidak tersedia |
| 3 Tokenomics | FDV vs beredar, unlock 7-90 hari, mekanisme deflasi | CoinGecko, `unlocks.json`, data kurasi |
| 4 Smart money | Backer Tier-1, aturan minimal 3 entitas, playbook a16z/Pantera/Animoca | Data kurasi (verifikasi manual) |
| 5 Makro dan regulasi | Fear and Greed, dominasi BTC, berita regulasi/ETF di radar, sikap The Fed | alternative.me, CoinGecko, `macro.json` |
| 6 SMC/ICT | Struktur weekly/daily, swing, FVG, likuiditas (EQH/EQL), OTE 0,62-0,79, entry, stop struktural, target, Moonbag +100% | Binance/OKX |

Skor akhir = narasi 20% + fundamental 20% + tokenomics 15% + smart money 15% + makro 10% + SMC 20%.
Fase 3 selalu berujung **Distribute** dan fase 4 **Avoid**. Ukuran posisi = min(batas skor 5-10%, alokasi yang membuat stop = 1% portofolio); altcoin total 10-30%, tanpa leverage; Moonbag: jual 50% saat +100%.

**Kejujuran data (penting):** NVT on-chain, MVRV sejati, dan alamat aktif tidak tersedia gratis untuk kebanyakan koin. Bila begitu,
scan memakai *proxy* yang diberi label jelas (mis. kapitalisasi/volume bursa, harga/VWAP 365 hari) dan menuliskannya di "Keterbatasan data".
Daftar backer dan mekanisme burn adalah pengetahuan umum per Jun 2026: verifikasi di ChainBroker/Crunchbase. Isi `unlocks.json` (TokenUnlocks/Tokenomist)
dan `macro.json` (sikap The Fed) agar modul 3 dan 5 lengkap. Mode server memindai semua koin bergiliran (tiap ~30 menit);
mode GitHub memindai `SCAN_PER_RUN` (default 3) koin tertua tiap siklus. Uji mesin scan: `python3 tests/test_scan.py`.

## Hosting gratis dari GitHub (tanpa server, tanpa domain berbayar)
Website di **GitHub Pages**, pengumpul berita di **GitHub Actions** (`.github/workflows/collect.yml`, siklus tiap ~3 menit lewat rantai job yang saling memanggil).
Alamatnya `https://<username>.github.io/crypto-sastra/`.

1. **Jadikan repo Public** (Settings → General → Danger Zone → Change visibility). Pages di akun gratis hanya untuk repo publik,
   dan repo publik mendapat menit Actions tanpa batas. Aman karena tidak ada kunci di kode; kunci disimpan di Secrets.
2. **Isi Secrets** (Settings → Secrets and variables → Actions → New repository secret), semua opsional:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`, `X_BEARER_TOKEN`, `CRYPTOPANIC_KEY`.
3. **Jalankan pertama kali**: tab Actions → "Kumpulkan berita" → Run workflow. Ini membuat branch `gh-pages`.
4. **Aktifkan Pages**: Settings → Pages → Source: *Deploy from a branch* → Branch `gh-pages` / `/ (root)` → Save.

Cara kerjanya: satu job menjalankan siklus tiap 3 menit selama 5 jam 40 menit (`tools/loop.sh`), lalu memanggil workflow ini lagi lewat
`workflow_dispatch` sehingga rantainya tidak putus. Cron tiap 15 menit hanya penjaga yang menghidupkan kembali rantai bila terputus. Alasannya:
jadwal cron GitHub bisa tertunda berjam-jam. Data JSON didorong ke branch **`data`** (satu commit yang ditimpa); website di github.io membacanya
lewat `raw.githubusercontent.com` (repo harus **publik**), sehingga tidak memicu build Pages (batas sekitar 10 build per jam). Branch `gh-pages`
hanya didorong bila `index.html` berubah atau tiap 30 menit sebagai salinan cadangan. Run pertama tidak mengirim alert agar backlog tidak membanjiri Telegram.
Atur `LOOP_INTERVAL` (detik) di workflow bila ingin lebih jarang. Bila rantai terputus, jalankan manual: tab Actions → "Kumpulkan berita" → Run workflow.

Batasan mode ini: bukan realtime. Siklus tiap 3 menit ditambah lama satu siklus, jadi waktu deteksi
lebih lambat daripada server sendiri. Workflow terjadwal bisa dinonaktifkan GitHub bila repo tidak ada aktivitas lama (cek tab Actions
dan aktifkan kembali). Untuk deteksi detik demi detik, jalankan `server.py` di VPS.

Uji satu siklus di komputer sendiri: `DATA_DIR=out/data python3 server.py --once`

## Deploy dengan server sendiri (realtime)
Server ini harus berjalan terus (ia menarik berita dan mengukur harga setiap beberapa detik), jadi pilih hosting yang mendukung proses long-running, bukan hosting statis.

**Opsi A, Render / Railway / Fly.io (paling mudah)**
1. Unggah folder ini ke repo GitHub privat.
2. Render: New → Blueprint → pilih repo (membaca `render.yaml`). Isi variabel rahasia di dashboard. Railway/Fly: deploy dari `Dockerfile`.
3. Pasang domain sendiri di pengaturan layanan (mis. `cryptosastra.com`), HTTPS otomatis.
4. Aktifkan disk persisten dan set `STATS_FILE=/data/stats.json` agar kalibrasi tidak hilang saat restart.

**Opsi B, VPS (Singapura/Tokyo untuk latensi rendah)**
```bash
cp .env.example .env && nano .env
docker compose up -d --build
```
Lalu pasang Caddy atau Nginx sebagai reverse proxy ke port 8000 agar dapat HTTPS. Untuk SSE (`/events`) matikan buffering proxy, di Nginx: `proxy_buffering off;`.

## Konfigurasi (environment variable, semua opsional)
| Variabel | Fungsi |
|---|---|
| `POLL_SECONDS` | Interval tarik data, default 20 dtk |
| `ANTHROPIC_API_KEY` | Analisis tambahan oleh Claude untuk berita skor 55+ |
| `X_BEARER_TOKEN`, `X_ACCOUNTS` | Sumber X/Twitter (API v2) dan akun yang dipantau |
| `CRYPTOPANIC_KEY` | Agregator CryptoPanic |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Alert Telegram (chat id boleh beberapa, pisah koma) |
| `ALERT_MIN_SCORE`, `ALERT_MAX_PER_HOUR` | Skor minimum alert (70) dan batas per jam (20) |
| `STATS_FILE` | Lokasi file statistik kalibrasi |
| `PORT` | Port server, default 8000 |

Kunci dan token bersifat rahasia: simpan di environment/secret hosting, jangan di-commit.

## Endpoint
`/` website · `/api/scan?symbol=SOL` · `/api/scan/index` · `/api/news` · `/api/top5` · `/api/predictions` · `/api/prices` · `/api/stats` · `/api/hunt` · `/api/scan/index` · `/events` (SSE) · `/health`

## Cara skor dihitung
`skor = bobot_event × kredibilitas × skala_proyek × urgensi × kesegaran`. Harga dicatat saat berita muncul dan diukur 1/6/24 jam
kemudian. Sinyal dianggap benar bila **alpha** (return koin dikurangi return BTC) searah prediksi. Setelah 8 sampel per jenis event,
bobotnya otomatis disesuaikan (×0,7 sampai ×1,3).

## Agar lebih cepat dari yang lain
X API (stream), Telegram/Discord resmi proyek, Binance announcement API, data on-chain (mempool, event kontrak, GitHub release),
`POLL_SECONDS` 5-10, dan server di dekat sumber. Kecepatan tidak bisa dijamin selalu pertama; kartu berita menampilkan waktu deteksi nyata.

## Batasan
Klasifikasi berbasis kata kunci bisa keliru pada rumor atau berita palsu. Estimasi exit dan prediksi adalah pola umum, bukan jaminan.
Bukan nasihat keuangan. Harga hanya dilacak untuk koin di `CG_IDS` (server.py). Hasil akurasi baru bermakna setelah berjalan beberapa hari.

## Dewan Agen, alat on-chain, dan pembelajaran diri

| Komponen | Isi | Catatan jujur |
|---|---|---|
| `agents.py` | 4 sub-agen (On-Chain & Likuiditas, Keamanan & Tokenomics, Narasi & Sosial, Developer & Kode) + Master Agent | Bukan LangGraph/CrewAI: orkestrasi ditulis sendiri tanpa dependensi |
| Alat (tool) | DexScreener (pool, umur, rasio beli/jual), GoPlus (honeypot, mint, pajak, holder, kunci LP, EVM saja), DefiLlama Yields (real yield vs emisi), GitHub API (aktivitas, fork vs orisinal, kompleksitas PR), pengambil teks whitepaper | Birdeye/Arkham/Solscan berbayar atau butuh kunci: pelacakan paus tidak aktif, agen menandai data kosong |
| Master Agent | Keyakinan 0-100 dari bobot agen x keyakinan data. Bila `ANTHROPIC_API_KEY` ada, LLM menalar dan boleh memanggil alat (maks 4 putaran), menyetel +-15 | VETO keamanan (honeypot, pajak >10%, pemilik tersembunyi) mutlak, tidak bisa dibatalkan LLM. Jalur LLM belum diuji ke API sungguhan |
| `memory.py` | Memori vektor (bag-of-words ber-hash + cosine), riwayat tren narasi, catatan pilihan, evaluasi 7/14/30 hari vs BTC, pelajaran dari kegagalan, aturan penalti terpelajar (maks 12) | Setara ChromaDB/Pinecone untuk skala kecil; belum ada embedding semantik |
| `founders.json` | Rekam jejak founder, diisi manual | Tidak ada API gratis; proyek gagal/rug mengurangi keyakinan 10 poin |

Hanya `AGENT_N` (default 8) kandidat teratas diperiksa agen per siklus; `MASTER_LLM_N` (5) dari itu juga dinalar LLM. Kartu kandidat menampilkan panel agen, dan bagian "Pembelajaran diri" menampilkan aturan yang dipelajari. Aturan baru baru muncul setelah >=10 pilihan terevaluasi.

## Modul filter kuantitatif (`quant.py`)

P/F (FDV / fee tahunan) dibanding median sektor (minimal 3 rekan berdata); efisiensi modal (volume DEX harian / TVL, aktif >= 0,8); divergensi harga-penggunaan (volume dan fee naik >30% sementara harga 30 hari <5%); MC/FDV < 0,25 dieliminasi kecuali dipastikan tanpa unlock 12 bulan di `unlocks.json` (jadwal tak tercatat dianggap berisiko); net real yield = pendapatan - nilai emisi (emisi dihitung dari pertumbuhan suplai beredar yang dicatat sejak siklus pertama, jadi baru muncul setelah >= 3 hari); kedalaman likuiditas DEX / market cap. Penyesuaian skor dibatasi +10 / -18.

Smart money (100 dompet profit teratas) tidak punya API gratis. Aktif hanya jika `DUNE_API_KEY` + `DUNE_QUERY_ID` (query Anda sendiri dengan kolom `symbol, net_flow_usd_7d, net_flow_usd_14d, wallets_buying, wallets_selling`) dipasang sebagai secrets; jalur ini belum diuji ke Dune sungguhan. Tanpa itu komponen ditampilkan n/a.

## Mesin Tesis (`thesis.py`)

Menyusun tesis tema (stablecoin institusional, RWA, perp DEX, staking/restaking, kredit on-chain, arus ETF) dari: berita radar 7 hari, momentum TVL sektor, total pasokan stablecoin (DefiLlama), dan catatan manual di `thesis_events.json`. Setiap tema memuat mekanisme, bukti, apa yang mengonfirmasi, apa yang membatalkan, dan peringkat proyek terbaik beserta alasannya (stablecoin: skala, pertumbuhan 30 hari, sebaran chain, jenis jaminan, peg; protokol: TVL, fee, pertumbuhan, sebaran chain, MC/fee). Keyakinan "kuat" butuh tiga jenis bukti berbeda dan tanpa bukti yang melawan. Atribut yang tidak ada API-nya (kepatuhan regulasi, kemitraan bank) hanya masuk lewat `stablecoin_meta` yang Anda isi dan verifikasi sendiri. Bila `ANTHROPIC_API_KEY` ada, 3 tema teratas diberi sintesis LLM yang dilarang menambah fakta.

## Papan eksekusi (`playbook.py`)

Panel paling atas. Status EKSEKUSI hanya bila semua gerbang lolos: skor >= 65, bukan viral/hantu/usang, tanpa eliminasi MC/FDV, keyakinan agen >= 65 dengan cakupan data >= 60% dan tanpa veto, kontrak terverifikasi (GoPlus), likuiditas DEX cukup untuk keluar, tanpa unlock <= 30 hari, serta DUA konfirmasi wajib: smart money net akumulasi dan TVL sektor naik (narasi on-chain). Tanpa data smart money tidak ada koin yang berstatus EKSEKUSI; yang lain tampil sebagai "menunggu". Rencana keluar: stop 20%, TP1 +40% (jual 1/3), TP2 +100% (jual 1/3), trailing 25%, batas waktu 21/30 hari, keluar 7 hari sebelum unlock, pemicu keluar dini (smart money berbalik, TVL sektor -5%, keyakinan <50, viral, divergensi tertutup), ukuran posisi dari risiko 1% modal. Angka-angka ini default yang bisa diubah di `playbook.py`, bukan hasil optimasi atau backtest.

## Menu Pengaturan (di web)

Bagian "Pengaturan" di halaman: (1) hubungkan token GitHub fine-grained (izin Secrets, Actions, Contents: read and write, hanya repo ini); (2) tempel API key, dienkripsi di browser dengan libsodium sealed box (tweetnacl + blakejs, hasilnya diuji didekripsi PyNaCl) lalu disimpan ke GitHub Secrets, tombol "Terapkan" menghentikan pengumpul lama dan memulai yang baru supaya secret dipakai; (3) editor file konfigurasi yang melakukan commit ke `main` dan disegarkan pengumpul tiap siklus (`sync_cfg` di `tools/loop.sh`). Token GitHub hanya di memori halaman kecuali opsi "ingat" dicentang. Kunci baru yang didukung: `CG_API_KEY` (CoinGecko demo, header `x-cg-demo-api-key`).

Menu Pengaturan sekarang halaman sendiri: `pengaturan.html` (dibangun `build.py` dari `site/pengaturan.*`, dipublikasikan ke gh-pages bersama `index.html`), dengan tab Koneksi, API key, dan Konfigurasi serta indikator status koneksi.

## Penyedia LLM (`llm.py`)

Satu antarmuka untuk Gemini, Groq, OpenRouter, DeepSeek, Mistral, OpenAI, dan Anthropic (tool use diterjemahkan ke format kompatibel-OpenAI, diuji dengan mock). Dipakai Master Agent, sintesis tesis, ringkasan whitepaper, dan analisis berita. Urutan bawaan: yang gratis dulu (Gemini, Groq, OpenRouter), lalu berbayar; bila satu gagal atau kena batas laju, otomatis mencoba berikutnya. Atur urutan dengan `LLM_PROVIDER` dan model dengan `LLM_MODELS` (nama model bawaan bisa usang; ganti bila ditolak). Belum diuji ke API sungguhan. Di halaman Pengaturan, kunci yang sudah tersimpan ditandai "✓ terisi" dan dipertahankan; opsi "Terapkan otomatis" memulai ulang pengumpul tiap kali menyimpan.

## Notifikasi cepat & tiket beli (`notify.py`)

Berjalan tiap siklus pengumpul (sekitar 3 menit), terpisah dari Hunter (kini tiap 30 menit bila `CG_API_KEY` ada, 55 menit bila tidak; atur `HUNT_EVERY_MIN`). Siklus sinyal: ENTRY (koin baru berstatus EKSEKUSI, berisi tiket order dan tautan beli), TP1/TP2, STOP, TRAIL, UNLOCK, REVIEW/TIME, EXIT (VETO, smart money berbalik, keyakinan turun, narasi pudar, atau hilang dari EKSEKUSI dalam 2 hasil Hunter berturut-turut). Harga dicek tiap siklus untuk stop/target; jeda 7 hari setelah sinyal ditutup. Kanal: Telegram, ntfy.sh (push gratis ke HP; secret `NTFY_TOPIC`), webhook Discord/Slack (`ALERT_WEBHOOK_URL`), dan notifikasi browser/suara di halaman (hanya saat halaman terbuka; web push murni tidak mungkin dari situs statis). Tombol beli hanya membuka Uniswap/PancakeSwap/Jupiter, DexScreener, CoinGecko, Binance (bila terdaftar) dengan alamat kontrak terisi; Anda yang memeriksa dan mengonfirmasi di dompet atau bursa Anda. Sistem ini sengaja tidak mengeksekusi order otomatis.

## Kesegaran data

- **Kolektor:** siklus penuh (berita + Hunter) tiap 3 menit; di antaranya jalur cepat tiap 1 menit (`server.py --fast`: harga + notifikasi sinyal + detak `live.json`). Interval diatur `LOOP_INTERVAL` dan `FULL_EVERY`. GitHub Actions tidak bisa lebih cepat dari ini dengan andal.
- **Halaman:** berita dan notifikasi disegarkan tiap 30 detik, Hunter tiap 60 detik (hanya bila hasilnya baru, supaya kartu yang terbuka tidak tertutup), semuanya berhenti saat tab tidak terlihat. Harga koin di Papan eksekusi diambil langsung dari DexScreener oleh browser tiap 10 detik, lengkap dengan posisi terhadap stop/TP. Bilah kesegaran menampilkan umur tiap sumber per detik dan tombol "Segarkan sekarang"; bila detak kolektor lebih tua dari 2,5 menit statusnya berubah merah.
- Per-detik sungguhan hanya berlaku untuk jam di bilah dan tampilan harga DEX; data analisis tetap menit-an.

Catatan: auto-apply di Pengaturan kini menunggu 45 detik setelah simpan terakhir (tiap penyimpanan yang langsung memulai ulang membuat siklus pengumpul terpotong berulang). Gemini/Groq otomatis memilih model yang tersedia bila model bawaan ditolak (404). Papan eksekusi menjelaskan mengapa smart money tidak aktif (kunci/ID Dune belum lengkap, query kosong, kolom salah, atau tak ada simbol yang cocok).
