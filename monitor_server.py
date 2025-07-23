#!/usr/bin/env python3
"""
A-ki 웹서버 모니터링 및 자동 재시작 시스템
"""

import os
import sys
import time
import signal
import subprocess
import requests
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.logger import logger

class ServerMonitor:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.web_port = 8000
        self.check_interval = 30  # 30초마다 체크
        self.max_retries = 3
        self.retry_delay = 10  # 재시작 후 10초 대기
        self.control_script = self.project_root / "aki_control.sh"
        self.log_file = self.project_root / "logs" / "monitor.log"
        
        # 로그 설정
        self.setup_logging()
        
        # 모니터링 상태
        self.is_running = True
        self.consecutive_failures = 0
        self.last_check_time = None
        self.server_start_time = None
        
    def setup_logging(self):
        """모니터링 전용 로그 설정"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 파일 핸들러
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 로거 설정
        self.monitor_logger = logging.getLogger('server_monitor')
        self.monitor_logger.setLevel(logging.INFO)
        self.monitor_logger.addHandler(file_handler)
        self.monitor_logger.addHandler(console_handler)
        
    def check_server_health(self) -> Dict[str, Any]:
        """서버 상태 확인"""
        try:
            # HTTP 응답 확인
            response = requests.get(
                f"http://localhost:{self.web_port}/api/test",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'status_code': response.status_code
                }
            else:
                return {
                    'status': 'unhealthy',
                    'status_code': response.status_code,
                    'error': f"HTTP {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'timeout',
                'error': 'Request timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'connection_error',
                'error': 'Connection refused'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def check_server_process(self) -> bool:
        """서버 프로세스 확인"""
        try:
            result = subprocess.run(
                [str(self.control_script), 'status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 상태 출력에서 "실행 중" 확인
            return "실행 중" in result.stdout and "정상 동작" in result.stdout
            
        except Exception as e:
            self.monitor_logger.error(f"프로세스 확인 실패: {e}")
            return False
    
    def restart_server(self) -> bool:
        """서버 재시작"""
        try:
            self.monitor_logger.info("🔄 서버 재시작 시작...")
            
            # 서버 중지
            subprocess.run(
                [str(self.control_script), 'stop'],
                capture_output=True,
                timeout=30
            )
            
            time.sleep(3)  # 중지 대기
            
            # 서버 시작
            result = subprocess.run(
                [str(self.control_script), 'start'],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.monitor_logger.info("✅ 서버 재시작 완료")
                self.server_start_time = datetime.now()
                return True
            else:
                self.monitor_logger.error(f"❌ 서버 재시작 실패: {result.stderr}")
                return False
                
        except Exception as e:
            self.monitor_logger.error(f"❌ 서버 재시작 중 오류: {e}")
            return False
    
    def get_server_logs(self, lines: int = 50) -> str:
        """최근 서버 로그 조회"""
        try:
            log_files = [
                self.project_root / "logs" / "server.log",
                self.project_root / "logs" / "trading.log"
            ]
            
            logs = []
            for log_file in log_files:
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines_content = f.readlines()
                        recent_lines = lines_content[-lines:] if len(lines_content) > lines else lines_content
                        logs.append(f"=== {log_file.name} ===")
                        logs.extend(recent_lines)
            
            return ''.join(logs) if logs else "로그 파일이 없습니다."
            
        except Exception as e:
            return f"로그 조회 실패: {e}"
    
    def monitor_loop(self):
        """메인 모니터링 루프"""
        self.monitor_logger.info("🚀 A-ki 서버 모니터링 시작")
        self.monitor_logger.info(f"📊 체크 간격: {self.check_interval}초")
        self.monitor_logger.info(f"🔄 최대 재시작 시도: {self.max_retries}회")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                self.last_check_time = current_time
                
                # 서버 상태 확인
                health = self.check_server_health()
                process_ok = self.check_server_process()
                
                # 상태 로깅
                if health['status'] == 'healthy' and process_ok:
                    if self.consecutive_failures > 0:
                        self.monitor_logger.info("✅ 서버 정상 복구됨")
                        self.consecutive_failures = 0
                    
                    self.monitor_logger.info(
                        f"✅ 서버 정상 - 응답시간: {health.get('response_time', 0):.2f}초"
                    )
                else:
                    self.consecutive_failures += 1
                    self.monitor_logger.warning(
                        f"⚠️ 서버 비정상 - 상태: {health['status']}, "
                        f"프로세스: {'정상' if process_ok else '비정상'}, "
                        f"연속 실패: {self.consecutive_failures}회"
                    )
                    
                    # 오류 상세 정보
                    if 'error' in health:
                        self.monitor_logger.error(f"오류: {health['error']}")
                
                # 재시작 조건 확인
                if self.consecutive_failures >= self.max_retries:
                    self.monitor_logger.error(f"🚨 서버 재시작 필요 (연속 실패: {self.consecutive_failures}회)")
                    
                    # 최근 로그 출력
                    logs = self.get_server_logs(20)
                    self.monitor_logger.info("📋 최근 서버 로그:")
                    for line in logs.split('\n')[-20:]:
                        if line.strip():
                            self.monitor_logger.info(f"  {line}")
                    
                    # 서버 재시작
                    if self.restart_server():
                        self.consecutive_failures = 0
                        time.sleep(self.retry_delay)  # 재시작 후 대기
                    else:
                        self.monitor_logger.error("❌ 재시작 실패, 다음 체크에서 재시도")
                
                # 대기
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.monitor_logger.info("🛑 모니터링 중단 신호 수신")
                break
            except Exception as e:
                self.monitor_logger.error(f"❌ 모니터링 루프 오류: {e}")
                time.sleep(self.check_interval)
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        self.monitor_logger.info(f"🛑 시그널 {signum} 수신, 모니터링 종료")
        self.is_running = False
    
    def run(self):
        """모니터링 실행"""
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            self.monitor_loop()
        finally:
            self.monitor_logger.info("🏁 모니터링 종료")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='A-ki 서버 모니터링')
    parser.add_argument('--interval', type=int, default=30, help='체크 간격 (초)')
    parser.add_argument('--retries', type=int, default=3, help='최대 재시작 시도 횟수')
    parser.add_argument('--delay', type=int, default=10, help='재시작 후 대기 시간 (초)')
    
    args = parser.parse_args()
    
    monitor = ServerMonitor()
    monitor.check_interval = args.interval
    monitor.max_retries = args.retries
    monitor.retry_delay = args.delay
    
    monitor.run()

if __name__ == "__main__":
    main() 