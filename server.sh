#!/bin/bash

# A-ki 웹 대시보드 서버 관리 스크립트
# 사용법: ./server.sh [start|stop|restart|status]

PORT=8000
APP_PATH="src.web.web_dashboard:app"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 서버 상태 확인
check_status() {
    if lsof -i :$PORT > /dev/null 2>&1; then
        log_info "서버가 실행 중입니다 (포트: $PORT)"
        lsof -i :$PORT
        return 0
    else
        log_warn "서버가 실행되지 않았습니다 (포트: $PORT)"
        return 1
    fi
}

# 서버 시작
start_server() {
    log_info "서버를 시작합니다..."
    
    if check_status > /dev/null 2>&1; then
        log_warn "서버가 이미 실행 중입니다. 'restart' 명령어를 사용하세요."
        return 1
    fi
    
    export PYTHONPATH=$(pwd)
    nohup uvicorn $APP_PATH --host 0.0.0.0 --port $PORT --reload > logs/server.log 2>&1 &
    
    sleep 2
    if check_status > /dev/null 2>&1; then
        log_info "✅ 서버가 성공적으로 시작되었습니다!"
        log_info "🌐 접속 URL: http://localhost:$PORT"
    else
        log_error "❌ 서버 시작에 실패했습니다. logs/server.log를 확인하세요."
        return 1
    fi
}

# 서버 중지
stop_server() {
    log_info "서버를 중지합니다..."
    
    if ! check_status > /dev/null 2>&1; then
        log_warn "서버가 실행되지 않았습니다."
        return 0
    fi
    
    # uvicorn 프로세스 종료
    pkill -f "uvicorn.*web_dashboard" 2>/dev/null
    
    # 포트를 사용하는 프로세스 강제 종료
    PIDS=$(lsof -ti :$PORT 2>/dev/null)
    if [ ! -z "$PIDS" ]; then
        log_warn "포트 $PORT를 사용하는 프로세스를 강제 종료합니다: $PIDS"
        kill -9 $PIDS 2>/dev/null
    fi
    
    sleep 1
    if ! check_status > /dev/null 2>&1; then
        log_info "✅ 서버가 성공적으로 중지되었습니다!"
    else
        log_error "❌ 서버 중지에 실패했습니다."
        return 1
    fi
}

# 서버 재시작
restart_server() {
    log_info "서버를 재시작합니다..."
    stop_server
    sleep 2
    start_server
}

# 메인 로직
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        check_status
        ;;
    *)
        echo "사용법: $0 {start|stop|restart|status}"
        echo ""
        echo "명령어:"
        echo "  start   - 서버 시작"
        echo "  stop    - 서버 중지"
        echo "  restart - 서버 재시작"
        echo "  status  - 서버 상태 확인"
        echo ""
        echo "예시:"
        echo "  $0 start    # 서버 시작"
        echo "  $0 restart  # 서버 재시작"
        echo "  $0 stop     # 서버 중지"
        exit 1
        ;;
esac 