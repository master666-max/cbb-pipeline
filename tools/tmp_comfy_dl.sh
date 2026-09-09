#!/bin/bash
# ComfyUI standalone env 多线程分片下载器 (12路并发+断点续传+自动重试)
URL="https://desktop-assets.comfy.org/standalone-environments/win-nvidia/v0.34.0-env1/comfyui-standalone-win-nvidia-v0.34.0-env1.7z"
TOTAL=2365760769
OUT="/tmp/comfy_dl/final.7z"
DEST="C:/Users/26672/AppData/Local/Comfy-Desktop/ComfyUI-Cache/download-cache/v0.34.0-env1_win-nvidia/comfyui-standalone-win-nvidia-v0.34.0-env1.7z"
PARTS=12
DIR=/tmp/comfy_dl
mkdir -p "$DIR"
CHUNK=$(( (TOTAL + PARTS - 1) / PARTS ))

download_part() {
  local i=$1 start=$(( i * CHUNK )) end=$(( (i+1) * CHUNK - 1 ))
  [ $end -ge $TOTAL ] && end=$(( TOTAL - 1 ))
  local want=$(( end - start + 1 )) part="$DIR/part_$i"
  while true; do
    local have=0
    [ -f "$part" ] && have=$(stat -c %s "$part")
    [ "$have" -ge "$want" ] && return 0
    local from=$(( start + have ))
    curl -sS -r "$from-$end" --max-time 600 --speed-limit 10240 --speed-time 30 \
         -o "$part.new" "$URL" 2>>"$DIR/err.log" && cat "$part.new" >> "$part"
    rm -f "$part.new"
    sleep 1
  done
}

echo "[$(date +%T)] 启动 $PARTS 路并发下载, 总大小 $TOTAL bytes"
for i in $(seq 0 $((PARTS-1))); do download_part "$i" & done
wait
echo "[$(date +%T)] 全部分片完成, 合并中..."
cat $(for i in $(seq 0 $((PARTS-1))); do echo "$DIR/part_$i"; done) > "$OUT"
got=$(stat -c %s "$OUT")
echo "[$(date +%T)] 合并完成: $got bytes (期望 $TOTAL)"
if [ "$got" -eq "$TOTAL" ]; then
  cp "$OUT" "$DEST"
  echo "[$(date +%T)] 已放置到应用缓存: $DEST"
  echo "DONE_OK"
else
  echo "SIZE_MISMATCH"
fi
