#!/usr/bin/env bash
# 2 fps contact sheets for review.  usage: scripts/sheets.sh FINAL.mp4 [REF.mp4] [OUTDIR]
#   OUTDIR/sheet.jpg    — ours, 2 fps, 16 columns, timestamped
#   OUTDIR/compare.jpg  — ours (left) | reference (right), first 60 s, 2 fps, 10 columns each
set -euo pipefail
OURS=$1; REF=${2:-}; OUT=${3:-renders}
mkdir -p "$OUT"
ffmpeg -v error -y -i "$OURS" -vf "fps=2,scale=135:240,drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=16x9" -frames:v 1 "$OUT/sheet.jpg"
if [ -n "$REF" ]; then
  ffmpeg -v error -y -t 60 -i "$OURS" -vf "fps=2,scale=108:192,tile=10x12" -frames:v 1 "$OUT/_ours.png"
  ffmpeg -v error -y -t 60 -i "$REF"  -vf "fps=2,scale=108:192,tile=10x12" -frames:v 1 "$OUT/_ref.png"
  ffmpeg -v error -y -i "$OUT/_ours.png" -i "$OUT/_ref.png" -filter_complex "[0][1]hstack=2" "$OUT/compare.jpg"
  rm -f "$OUT/_ours.png" "$OUT/_ref.png"
fi
echo "sheets in $OUT"
