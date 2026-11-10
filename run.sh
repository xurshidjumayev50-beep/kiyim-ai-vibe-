#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo "👗 KIYIM AI — VIRTUAL TRY-ON & FIT DETECTION ILOVASI"
echo "=========================================================="

# Python muhitini aniqlash
if [ -f "/home/xurshid/venv/bin/python3" ]; then
    PYTHON_CMD="/home/xurshid/venv/bin/python3"
elif [ -f "venv/bin/python3" ]; then
    PYTHON_CMD="venv/bin/python3"
else
    PYTHON_CMD="python3"
fi

echo "🚀 Python ishlatilmoqda: $PYTHON_CMD"

# Mahalliy IP manzilni aniqlash (telefon orqali ulanish uchun)
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

PORT=${PORT:-5050}

echo ""
echo "📱 Ilovani ochish uchun manzillar:"
echo "   💻 Kompyuterda: http://localhost:$PORT"
echo "   📲 Telefonda (Wi-Fi orqali): http://$LOCAL_IP:$PORT"
echo ""
echo "Boshqaruv tugmalari:"
echo "   [Ctrl + C] — Serverni to'xtatish"
echo "=========================================================="

export PORT
exec $PYTHON_CMD app.py
