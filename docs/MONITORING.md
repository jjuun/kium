# A-ki 서버 모니터링 시스템

## 개요

A-ki 서버의 상태를 실시간으로 모니터링하고, 문제 발생 시 자동으로 재시작하는 시스템입니다.

## 구성 요소

### 1. 모니터링 스크립트 (`monitor_server.py`)
- 서버 상태 실시간 모니터링
- HTTP 응답 확인
- 프로세스 상태 확인
- 자동 재시작 기능
- 로그 기록

### 2. 로그 뷰어 (`view_logs.py`)
- 실시간 로그 확인
- 로그 검색 기능
- 특정 로그 파일 추적

### 3. Systemd 서비스 (`aki-monitor.service`)
- 시스템 부팅 시 자동 시작
- 서비스 관리 (시작/중지/재시작)

## 사용법

### 기본 모니터링 시작

```bash
# 기본 설정으로 모니터링 시작 (30초 간격, 3회 재시도)
python3 monitor_server.py

# 커스텀 설정으로 모니터링 시작
python3 monitor_server.py --interval 60 --retries 5 --delay 15
```

### 로그 확인

```bash
# 모든 로그 파일 확인 (마지막 30줄)
python3 view_logs.py

# 특정 로그 파일 확인
python3 view_logs.py --file server --lines 100

# 실시간 로그 추적
python3 view_logs.py --file server --follow

# 로그에서 키워드 검색
python3 view_logs.py --search "error"
python3 view_logs.py --search "timeout" --case-sensitive
```

### Systemd 서비스 등록 (Linux/macOS)

```bash
# 서비스 파일 복사
sudo cp aki-monitor.service /etc/systemd/system/

# 서비스 활성화
sudo systemctl enable aki-monitor.service

# 서비스 시작
sudo systemctl start aki-monitor.service

# 서비스 상태 확인
sudo systemctl status aki-monitor.service

# 서비스 중지
sudo systemctl stop aki-monitor.service
```

## 모니터링 기능

### 1. 상태 확인
- **HTTP 응답 확인**: `/api/test` 엔드포인트 호출
- **프로세스 확인**: `aki_control.sh status` 명령 실행
- **응답 시간 측정**: HTTP 요청 응답 시간 기록

### 2. 자동 재시작 조건
- 연속 3회 (기본값) 실패 시 자동 재시작
- 재시작 후 10초 (기본값) 대기
- 재시작 실패 시 다음 체크에서 재시도

### 3. 로그 기록
- **모니터링 로그**: `logs/monitor.log`
- **서버 로그**: `logs/server.log`
- **트레이딩 로그**: `logs/trading.log`

## 설정 옵션

### 모니터링 스크립트 옵션
- `--interval`: 체크 간격 (초, 기본값: 30)
- `--retries`: 최대 재시작 시도 횟수 (기본값: 3)
- `--delay`: 재시작 후 대기 시간 (초, 기본값: 10)

### 로그 뷰어 옵션
- `--file`: 특정 로그 파일 선택 (server/trading/monitor)
- `--lines`: 출력할 줄 수 (기본값: 50)
- `--follow`: 실시간 추적
- `--search`: 키워드 검색
- `--case-sensitive`: 대소문자 구분 검색

## 모니터링 상태

### 정상 상태
```
✅ 서버 정상 - 응답시간: 0.15초
```

### 비정상 상태
```
⚠️ 서버 비정상 - 상태: timeout, 프로세스: 정상, 연속 실패: 1회
오류: Request timeout
```

### 재시작 필요
```
🚨 서버 재시작 필요 (연속 실패: 3회)
📋 최근 서버 로그:
🔄 서버 재시작 시작...
✅ 서버 재시작 완료
```

## 문제 해결

### 1. 모니터링이 시작되지 않는 경우
```bash
# 의존성 확인
pip install requests

# 권한 확인
chmod +x monitor_server.py

# 로그 확인
python3 view_logs.py --file monitor
```

### 2. 서버 재시작이 실패하는 경우
```bash
# 수동으로 서버 상태 확인
./aki_control.sh status

# 수동으로 서버 재시작
./aki_control.sh restart

# 로그 확인
python3 view_logs.py --search "재시작"
```

### 3. 로그 파일이 없는 경우
```bash
# 로그 디렉토리 생성
mkdir -p logs

# 서버 시작하여 로그 생성
./aki_control.sh start
```

## 고급 설정

### 백그라운드 실행
```bash
# nohup으로 백그라운드 실행
nohup python3 monitor_server.py > monitor.out 2>&1 &

# 프로세스 확인
ps aux | grep monitor_server.py

# 로그 확인
tail -f monitor.out
```

### cron 작업 등록
```bash
# crontab 편집
crontab -e

# 매 5분마다 모니터링 스크립트 실행
*/5 * * * * cd /path/to/A-ki && python3 monitor_server.py --interval 300
```

## 보안 고려사항

1. **파일 권한**: 로그 파일의 적절한 권한 설정
2. **네트워크 보안**: 모니터링 포트 접근 제한
3. **로그 보안**: 민감한 정보가 로그에 기록되지 않도록 주의
4. **서비스 계정**: 전용 사용자 계정으로 서비스 실행 권장

## 성능 고려사항

1. **체크 간격**: 너무 짧은 간격은 시스템 부하 증가
2. **로그 크기**: 로그 파일 크기 모니터링 및 로테이션
3. **메모리 사용량**: 장기 실행 시 메모리 누수 확인
4. **CPU 사용량**: 모니터링 프로세스의 CPU 사용량 확인 