# Crypto Sastra

Radar berita crypto realtime: mengumpulkan berita dari banyak sumber, memberi skor 0-100, menjelaskan dampak dan alasan,
menyarankan langkah, memperkirakan jendela exit, menebak proyek lain yang ikut terdampak, menampilkan Top 5 proyek paling
berdampak, lalu **mengukur akurasi sinyalnya terhadap harga (vs BTC)** dan mengkalibrasi skor sendiri.

## Struktur
```
server.py                  backend: pengumpul berita, analisis, harga, kalibrasi, alert Telegram, API + SSE; --once = satu siklus untuk Actions
.github/workflows/collect.yml  jadwal GitHub Actions (cron 5 menit) yang menerbitkan ke gh-pages
static/index.html          website (hasil build, dilayani server)
site/crypto-sastra.src.html sumber website (edit di sini, lalu jalankan: python3 build.py)
Dockerfile, docker-compose.yml, render.yaml, Procfile, .env.example   berkas deploy
```

## Jalankan lokal
```bash
python3 server.py            # Python 3.9+, tanpa dependensi
# buka http://localhost:8000
```
Tanpa akses internet ke sumber, server memuat data contoh (diberi label "Contoh"). Uji harga offline: `SIM_PRICES=1 python3 server.py`.

## Hosting gratis dari GitHub (tanpa server, tanpa domain berbayar)
Website di **GitHub Pages**, pengumpul berita di **GitHub Actions** (`.github/workflows/collect.yml`, jalan tiap ~5 menit).
Alamatnya `https://<username>.github.io/crypto-sastra/`.

1. **Jadikan repo Public** (Settings → General → Danger Zone → Change visibility). Pages di akun gratis hanya untuk repo publik,
   dan repo publik mendapat menit Actions tanpa batas. Aman karena tidak ada kunci di kode; kunci disimpan di Secrets.
2. **Isi Secrets** (Settings → Secrets and variables → Actions → New repository secret), semua opsional:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`, `X_BEARER_TOKEN`, `CRYPTOPANIC_KEY`.
3. **Jalankan pertama kali**: tab Actions → "Kumpulkan berita" → Run workflow. Ini membuat branch `gh-pages`.
4. **Aktifkan Pages**: Settings → Pages → Source: *Deploy from a branch* → Branch `gh-pages` / `/ (root)` → Save.

Cara kerjanya: tiap siklus memuat data sebelumnya dari `gh-pages`, mengumpulkan berita, mengukur hasil harga, mengirim alert, lalu
menimpa `gh-pages` dengan satu commit (riwayat tidak membengkak). Run pertama tidak mengirim alert agar backlog tidak membanjiri Telegram.

Batasan mode ini: bukan realtime. Jadwal cron GitHub minimal 5 menit dan sering tertunda beberapa menit saat ramai, jadi waktu deteksi
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
`/` website · `/api/news` · `/api/top5` · `/api/predictions` · `/api/prices` · `/api/stats` · `/events` (SSE) · `/health`

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
