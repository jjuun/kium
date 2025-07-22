#!/bin/bash

# A-ki 통합 서버 컨트롤 스크립트
# 웹 서버와 트레이딩 서버를 모두 관리합니다.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTROL_SCRIPT="$SCRIPT_DIR/aki_server_control.py"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 가상환경 활성화
activate_venv() {
    if [ -d "$SCRIPT_DIR/venv" ]; then
        log_info "가상환경 활성화 중... (venv)"
        source "$SCRIPT_DIR/venv/bin/activate"
    elif [ -d "$SCRIPT_DIR/.venv" ]; then
        log_info "가상환경 활성화 중... (.venv)"
        source "$SCRIPT_DIR/.venv/bin/activate"
    else
        log_warning "가상환경을 찾을 수 없습니다. 시스템 Python을 사용합니다."
    fi
}

# Python 스크립트 실행
run_control() {
    local command="$1"
    local force="$2"
    
    log_info "A-ki 서버 컨트롤 실행: $command"
    
    if [ "$force" = "true" ]; then
        python3 "$CONTROL_SCRIPT" "$command" --force
    else
        python3 "$CONTROL_SCRIPT" "$command"
    fi
}

# 사용법 출력
show_usage() {
    echo "A-ki 통합 서버 컨트롤 스크립트"
    echo "================================"
    echo ""
    echo "사용법:"
    echo "  $0 start              # 모든 서버 시작"
    echo "  $0 stop               # 모든 서버 중지"
    echo "  $0 stop --force       # 모든 서버 강제 중지"
    echo "  $0 restart            # 모든 서버 재시작"
    echo "  $0 status             # 서버 상태 확인"
    echo "  $0 help               # 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 start              # 웹 서버와 트레이딩 서버 모두 시작"
    echo "  $0 stop               # 모든 서버 안전하게 중지"
    echo "  $0 restart            # 모든 서버 재시작"
    echo ""
}

# 메인 함수
main() {
    local command="$1"
    local force="false"
    
    # 강제 옵션 확인
    if [ "$2" = "--force" ] || [ "$2" = "-f" ]; then
        force="true"
    fi
    
    # 명령어 검증
    case "$command" in
        start|stop|restart|status|help)
            ;;
        *)
            log_error "알 수 없는 명령어: $command"
            show_usage
            exit 1
            ;;
    esac
    
    # 도움말 표시
    if [ "$command" = "help" ]; then
        show_usage
        exit 0
    fi
    
    # 스크립트 존재 확인
    if [ ! -f "$CONTROL_SCRIPT" ]; then
        log_error "컨트롤 스크립트를 찾을 수 없습니다: $CONTROL_SCRIPT"
        exit 1
    fi
    
    # 실행 권한 확인
    if [ ! -x "$CONTROL_SCRIPT" ]; then
        log_warning "컨트롤 스크립트에 실행 권한이 없습니다. 권한을 추가합니다."
        chmod +x "$CONTROL_SCRIPT"
    fi
    
    # 가상환경 활성화
    activate_venv
    
    # 명령어 실행
    case "$command" in
        start)
            log_info "🚀 A-ki 서버 시작"
            run_control "start" "$force"
            ;;
        stop)
            log_info "🛑 A-ki 서버 중지"
            run_control "stop" "$force"
            ;;
        restart)
            log_info "🔄 A-ki 서버 재시작"
            run_control "restart" "$force"
            ;;
        status)
            log_info "📊 A-ki 서버 상태 확인"
            run_control "status" "$force"
            ;;
    esac
}

# 스크립트 실행
if [ $# -eq 0 ]; then
    log_error "명령어가 필요합니다."
    show_usage
    exit 1
fi

main "$@" 