#!/bin/bash

# A-ki 테스트 실행 스크립트

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
    if [ -d "venv" ]; then
        log_info "가상환경 활성화 중... (venv)"
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        log_info "가상환경 활성화 중... (.venv)"
        source .venv/bin/activate
    else
        log_warning "가상환경을 찾을 수 없습니다."
        return 1
    fi
}

# 의존성 설치
install_dependencies() {
    log_info "개발 의존성 설치 중..."
    pip install -r requirements-dev.txt
    if [ $? -eq 0 ]; then
        log_success "의존성 설치 완료"
    else
        log_error "의존성 설치 실패"
        exit 1
    fi
}

# 테스트 실행
run_tests() {
    local test_type="$1"
    local coverage="$2"
    
    case "$test_type" in
        "unit")
            log_info "📋 단위 테스트 실행..."
            python -m pytest tests/unit/ -v --cov=src --cov-report=html --cov-report=term
            ;;
        "integration")
            log_info "🔗 통합 테스트 실행..."
            python -m pytest tests/integration/ -v
            ;;
        "e2e")
            log_info "🌐 E2E 테스트 실행..."
            python -m pytest tests/e2e/ -v
            ;;
        "all")
            log_info "🧪 전체 테스트 실행..."
            python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term
            ;;
        "coverage")
            log_info "📊 테스트 커버리지 리포트 생성..."
            python -m pytest --cov=src --cov-report=html --cov-report=term --cov-fail-under=80
            ;;
        *)
            log_error "알 수 없는 테스트 타입: $test_type"
            show_usage
            exit 1
            ;;
    esac
}

# 사용법 표시
show_usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  unit        단위 테스트만 실행"
    echo "  integration 통합 테스트만 실행"
    echo "  e2e         E2E 테스트만 실행"
    echo "  all         전체 테스트 실행 (기본값)"
    echo "  coverage    커버리지 리포트만 생성"
    echo "  install     개발 의존성 설치"
    echo "  help        이 도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 unit        # 단위 테스트만 실행"
    echo "  $0 all         # 전체 테스트 실행"
    echo "  $0 coverage    # 커버리지 리포트 생성"
}

# 메인 함수
main() {
    local command="${1:-all}"
    
    case "$command" in
        unit|integration|e2e|all|coverage)
            # 가상환경 활성화
            activate_venv
            
            # 테스트 실행
            run_tests "$command"
            ;;
        install)
            # 가상환경 활성화
            activate_venv
            
            # 의존성 설치
            install_dependencies
            ;;
        help)
            show_usage
            exit 0
            ;;
        *)
            log_error "알 수 없는 명령어: $command"
            show_usage
            exit 1
            ;;
    esac
    
    log_success "테스트 완료!"
}

# 스크립트 실행
if [ $# -eq 0 ]; then
    main "all"
else
    main "$1"
fi 