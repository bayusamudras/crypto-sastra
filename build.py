#!/usr/bin/env python3
"""Bangun static/index.html (halaman lengkap) dari site/crypto-sastra.src.html."""
import os
import json
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "site", "crypto-sastra.src.html"), encoding="utf-8").read()
try: seed = open(os.path.join(here, "hunt_seed.json"), encoding="utf-8").read()
except Exception: seed = "null"
src = src.replace("/*SEED_HUNT*/null", json.dumps(json.loads(seed), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
page = ('<!doctype html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        '<meta name="theme-color" content="#0D1020">\n</head>\n<body>\n' + src + '\n</body>\n</html>\n')
open(os.path.join(here, "static", "index.html"), "w", encoding="utf-8").write(page)
print("OK -> static/index.html", len(page), "bytes")

# ---- halaman Pengaturan (terpisah): kepala + gaya dari halaman utama, isi dari site/pengaturan.*
import re
head = src[:src.index("</style>")]
head = head.replace("<title>Crypto Sastra</title>", "<title>Pengaturan · Crypto Sastra</title>")
head = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="Pengaturan API key dan konfigurasi Crypto Sastra.">', head)
rd = lambda n: open(os.path.join(here, "site", n), encoding="utf-8").read()
sb = rd("sealedbox.min.js").replace("</", "<\\/")
page2 = ('<!doctype html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n<meta name="theme-color" content="#0D1020">\n<meta name="robots" content="noindex">\n'
         + head + rd("pengaturan.css") + "</style>\n</head>\n<body>\n" + rd("pengaturan.body.html") + "<script>" + sb + "</script>\n<script>\n" + rd("pengaturan.js").replace("</", "<\\/") + "\n</script>\n</body>\n</html>\n")
open(os.path.join(here, "static", "pengaturan.html"), "w", encoding="utf-8").write(page2)
print("OK -> static/pengaturan.html", len(page2), "bytes")
