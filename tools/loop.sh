#!/usr/bin/env bash
# Pengumpul berkelanjutan untuk GitHub Actions.
# Satu job menjalankan banyak siklus (default tiap 3 menit selama 5 jam 40 menit), lalu workflow memanggil dirinya lagi.
# Data (JSON) didorong ke branch `data` tanpa memicu build Pages; branch `gh-pages` hanya didorong bila index.html berubah
# atau tiap PAGES_EVERY detik (salinan cadangan), supaya tidak melewati batas build GitHub Pages (sekitar 10 per jam).
set -u
ROOT="$(pwd)"
REPO_URL="${REPO_URL:-https://x-access-token:${GH_TOKEN:-}@github.com/${GITHUB_REPOSITORY:-}.git}"
PY="${PY_CMD:-python3 server.py --once}"
LOOP_SECONDS="${LOOP_SECONDS:-20400}"; INTERVAL="${LOOP_INTERVAL:-180}"; PAGES_EVERY="${PAGES_EVERY:-1800}"; CYCLE_TIMEOUT="${CYCLE_TIMEOUT:-420}"
END=$(( $(date +%s) + LOOP_SECONDS ))

rm -rf out-data out-pages
if ! git clone -q --depth 1 --branch gh-pages "$REPO_URL" out-pages 2>/dev/null; then
  mkdir -p out-pages; git -C out-pages init -q -b gh-pages; git -C out-pages remote add origin "$REPO_URL"
fi
if ! git clone -q --depth 1 --branch data "$REPO_URL" out-data 2>/dev/null; then
  mkdir -p out-data; git -C out-data init -q -b data; git -C out-data remote add origin "$REPO_URL"
  [ -d out-pages/data ] && cp -r out-pages/data out-data/data && echo "migrasi: data awal disalin dari gh-pages"
fi
mkdir -p out-data/data
for d in out-data out-pages; do
  git -C "$d" config user.name "crypto-sastra-bot"; git -C "$d" config user.email "bot@users.noreply.github.com"; git -C "$d" config commit.gpgsign false
done
export DATA_DIR="$ROOT/out-data/data"

push() {   # push <dir> <branch> <pesan>: satu commit yang terus ditimpa (riwayat tidak membengkak)
  git -C "$1" add -A
  if git -C "$1" rev-parse -q --verify HEAD >/dev/null 2>&1; then git -C "$1" commit -q --amend -m "$3" >/dev/null 2>&1 || true
  else git -C "$1" commit -q -m "$3" >/dev/null 2>&1 || true; fi
  git -C "$1" push -q --force origin "$2" 2>&1 || echo "push $2 gagal"
}

publish_pages() {
  local changed=0 now last
  now=$(date +%s); last=$(cat out-pages/.pushed_at 2>/dev/null || echo 0)
  cmp -s static/index.html out-pages/index.html 2>/dev/null || { cp static/index.html out-pages/index.html; changed=1; }
  touch out-pages/.nojekyll
  if [ "$changed" = 1 ] || [ $(( now - last )) -ge "$PAGES_EVERY" ]; then
    rm -rf out-pages/data; cp -r out-data/data out-pages/data
    echo "$now" > out-pages/.pushed_at
    push out-pages gh-pages "pages $(date -u +%FT%TZ)"
  fi
}

# Berkas konfigurasi manual (diedit dari menu Pengaturan di web) disegarkan dari branch main tiap siklus, tanpa menunggu job dimulai ulang.
CFG_FILES="unlocks.json thesis_events.json smartmoney.json catalysts.json buyback.json macro.json founders.json"
sync_cfg() {
  git fetch -q --depth 1 origin main 2>/dev/null || return 0
  for f in $CFG_FILES; do
    git show "FETCH_HEAD:$f" > .cfg.tmp 2>/dev/null && python3 -c "import json,sys;json.load(open('.cfg.tmp'))" 2>/dev/null && cp .cfg.tmp "$f"
  done
  rm -f .cfg.tmp
}

n=0
while :; do
  s=$(date +%s); n=$(( n + 1 ))
  echo "=== siklus $n $(date -u +%FT%TZ)"
  sync_cfg
  timeout "$CYCLE_TIMEOUT" $PY || echo "siklus $n gagal atau melewati batas waktu (lanjut)"
  push out-data data "data $(date -u +%FT%TZ)"
  publish_pages
  e=$(date +%s)
  w=$(( INTERVAL - (e - s) )); [ "$w" -gt 5 ] || w=5
  [ $(( e + w )) -ge "$END" ] && break
  sleep "$w"
done
echo "loop selesai setelah $n siklus"
