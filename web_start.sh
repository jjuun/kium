#!/bin/bash

# A-ki 자동매매 시스템 서버 시작 스크립트

echo "🚀 A-ki 자동매매 시스템 서버 시작"
echo "=================================================="

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "🔧 가상환경 활성화 중..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🔧 가상환경 활성화 중..."
    source .venv/bin/activate
else
    echo "⚠️  가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다."
fi

# Python 스크립트 실행
echo "🐍 Python 웹 서버 시작 스크립트 실행 중..."
python3 web_server_control.py

echo "✅ 서버 시작 완료" 