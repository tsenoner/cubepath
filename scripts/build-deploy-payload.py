#!/usr/bin/env python3
"""Build the Vercel deploy payload from app/ — the ONLY sanctioned way to
assemble a deploy. Verifies completeness so a partial deploy can't happen."""

import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
OUT = os.path.expanduser("~/.claude/jobs/87065dd8/tmp/deploy-files.json")

REQUIRED = [
    "package.json",
    "astro.config.mjs",
    "tsconfig.json",
    "vercel.json",
    "src/pages/index.astro",
    "src/data/algs.ts",
    "public/favicon.svg",
]
SKIP_DIRS = {"node_modules", "dist", ".astro", "test-results", "playwright-report"}
SKIP_TOP = {"e2e", "tests", "scripts"}  # not needed to build on Vercel
TEXT_EXT = {".astro", ".ts", ".mjs", ".json", ".css", ".svg", ".mdx", ".md", ".webmanifest", ".txt"}
BIN_EXT = {".png", ".ico", ".woff2", ".pdf", ".jpg", ".webp"}

files = []
for dirpath, dirnames, filenames in os.walk(APP):
    rel_dir = os.path.relpath(dirpath, APP)
    parts = [] if rel_dir == "." else rel_dir.split(os.sep)
    if parts and (parts[0] in SKIP_TOP or any(p in SKIP_DIRS for p in parts)):
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (not parts and d in SKIP_TOP)]
    for f in filenames:
        if f.startswith(".") or f in {"package-lock.json", "vitest.config.ts", "playwright.config.ts"}:
            continue
        path = os.path.join(dirpath, f)
        rel = os.path.relpath(path, APP).replace(os.sep, "/")
        ext = os.path.splitext(f)[1]
        if ext in BIN_EXT:
            files.append({"file": rel, "data": base64.b64encode(open(path, "rb").read()).decode(), "encoding": "base64"})
        elif ext in TEXT_EXT:
            files.append({"file": rel, "data": open(path, encoding="utf-8").read()})

present = {f["file"] for f in files}
missing = [r for r in REQUIRED if r not in present]
if missing:
    sys.exit(f"REFUSING to write payload — missing required files: {missing}")
lessons = [f for f in present if f.startswith("src/content/lessons/")]
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(files, open(OUT, "w"))
print(f"payload: {len(files)} files ({len(lessons)} lessons), {os.path.getsize(OUT)} bytes -> {OUT}")
