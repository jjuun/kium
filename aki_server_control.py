#!/usr/bin/env python3
"""
A-ki 통합 서버 컨트롤 시스템
웹 서버와 트레이딩 서버를 모두 관리합니다.
"""

import os
import sys
import time
import signal
import subprocess
import psutil
from pathlib import Path
from typing import List, Dict, Optional

class AkiServerController:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.web_pid_file = self.project_root / "web_server.pid"
        self.trading_pid_file = self.project_root / "trading_server.pid"
        self.web_port = 8000
        self.trading_port = 8001  # 트레이딩 서버용 포트 (필요시)
        
        # 프로세스 이름 패턴
        self.web_patterns = [
            "uvicorn.*web_dashboard",
            "web_dashboard",
            "web_server"
        ]
        self.trading_patterns = [
            "main.py",
            "auto_trader",
            "trading_server"
        ]
        
    def find_processes(self) -> Dict[str, List[psutil.Process]]:
        """현재 실행 중인 관련 프로세스들을 찾습니다."""
        web_processes = []
        trading_processes = []
        
        # PID 파일에서 프로세스 확인
        if self.web_pid_file.exists():
            try:
                with open(self.web_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            web_processes.append(proc)
                    except psutil.NoSuchProcess:
                        pass
            except (ValueError, IOError):
                pass
                
        if self.trading_pid_file.exists():
            try:
                with open(self.trading_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            trading_processes.append(proc)
                    except psutil.NoSuchProcess:
                        pass
            except (ValueError, IOError):
                pass
        
        # Python 프로세스 중 A-ki 관련 프로세스 찾기
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmdline_str = ' '.join(str(arg) for arg in cmdline)
                    
                    # 웹 서버 프로세스 확인
                    if any(pattern in cmdline_str for pattern in self.web_patterns):
                        if proc not in web_processes:
                            web_processes.append(proc)
                            
                    # 트레이딩 서버 프로세스 확인
                    if any(pattern in cmdline_str for pattern in self.trading_patterns):
                        if proc not in trading_processes:
                            trading_processes.append(proc)
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # 포트 사용 프로세스 확인
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == self.web_port and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        if proc not in web_processes:
                            web_processes.append(proc)
                    except psutil.NoSuchProcess:
                        continue
        except psutil.AccessDenied:
            pass
            
        return {
            'web': web_processes,
            'trading': trading_processes
        }
    
    def kill_processes(self, processes: List[psutil.Process], force: bool = False) -> Dict[str, List[int]]:
        """지정된 프로세스들을 종료합니다."""
        killed = []
        failed = []
        
        for proc in processes:
            try:
                print(f"프로세스 종료 중: PID {proc.pid} - {proc.name()}")
                
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                    
                killed.append(proc.pid)
                
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                print(f"프로세스 종료 권한 없음: PID {proc.pid}")
                failed.append(proc.pid)
                
        # 강제 종료가 필요한 경우
        if not force:
            time.sleep(3)
            for proc in processes:
                try:
                    if proc.is_running():
                        print(f"강제 종료: PID {proc.pid}")
                        proc.kill()
                        if proc.pid not in killed:
                            killed.append(proc.pid)
                except psutil.NoSuchProcess:
                    continue
                    
        return {'killed': killed, 'failed': failed}
    
    def wait_for_port(self, port: int, timeout: int = 10) -> bool:
        """포트가 사용 가능할 때까지 대기합니다."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                for conn in psutil.net_connections():
                    if conn.laddr.port == port and conn.status == 'LISTEN':
                        return False
                return True
            except psutil.AccessDenied:
                return True
            time.sleep(0.5)
        return False
    
    def start_web_server(self) -> Optional[subprocess.Popen]:
        """웹 서버를 시작합니다."""
        print("🌐 웹 서버 시작 중...")
        
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "src.web.web_dashboard:app",
            "--host", "0.0.0.0",
            "--port", str(self.web_port),
            "--reload"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # PID 파일에 저장
            with open(self.web_pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"✅ 웹 서버 시작됨 (PID: {process.pid})")
            print(f"🌍 웹 서버 주소: http://localhost:{self.web_port}")
            
            return process
            
        except Exception as e:
            print(f"❌ 웹 서버 시작 실패: {e}")
            return None
    
    def start_trading_server(self) -> Optional[subprocess.Popen]:
        """트레이딩 서버를 시작합니다."""
        print("📈 트레이딩 서버 시작 중...")
        
        cmd = [sys.executable, "main.py"]
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # PID 파일에 저장
            with open(self.trading_pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"✅ 트레이딩 서버 시작됨 (PID: {process.pid})")
            
            return process
            
        except Exception as e:
            print(f"❌ 트레이딩 서버 시작 실패: {e}")
            return None
    
    def cleanup(self):
        """정리 작업을 수행합니다."""
        # PID 파일 삭제
        for pid_file in [self.web_pid_file, self.trading_pid_file]:
            if pid_file.exists():
                try:
                    pid_file.unlink()
                except:
                    pass
    
    def stop_all(self, force: bool = False) -> bool:
        """모든 서버를 중지합니다."""
        print("🛑 A-ki 서버 중지")
        print("=" * 50)
        
        # 1. 기존 프로세스 확인
        print("🔍 실행 중인 프로세스 확인 중...")
        processes = self.find_processes()
        
        total_processes = len(processes['web']) + len(processes['trading'])
        if total_processes == 0:
            print("✅ 실행 중인 프로세스가 없습니다.")
            self.cleanup()
            return True
        
        print(f"📋 발견된 프로세스: {total_processes}개")
        
        if processes['web']:
            print("  🌐 웹 서버 프로세스:")
            for proc in processes['web']:
                try:
                    print(f"    - PID {proc.pid}: {proc.name()}")
                except psutil.NoSuchProcess:
                    continue
                    
        if processes['trading']:
            print("  📈 트레이딩 서버 프로세스:")
            for proc in processes['trading']:
                try:
                    print(f"    - PID {proc.pid}: {proc.name()}")
                except psutil.NoSuchProcess:
                    continue
        
        # 2. 프로세스 종료
        print("🛑 프로세스 종료 중...")
        
        all_processes = processes['web'] + processes['trading']
        result = self.kill_processes(all_processes, force)
        
        print(f"✅ 종료된 프로세스: {len(result['killed'])}개")
        if result['failed']:
            print(f"❌ 종료 실패한 프로세스: {len(result['failed'])}개")
        
        # 3. 포트 해제 대기
        if self.wait_for_port(self.web_port):
            print("✅ 웹 서버 포트 해제 완료")
        else:
            print("⚠️  웹 서버 포트가 아직 사용 중입니다.")
        
        # 4. 정리 작업
        self.cleanup()
        
        print("🎉 모든 서버 중지 완료!")
        return True
    
    def start_all(self) -> bool:
        """모든 서버를 시작합니다."""
        print("🚀 A-ki 서버 시작")
        print("=" * 50)
        
        # 1. 기존 프로세스 정리
        print("🔍 기존 프로세스 확인 중...")
        processes = self.find_processes()
        
        total_processes = len(processes['web']) + len(processes['trading'])
        if total_processes > 0:
            print(f"📋 발견된 프로세스: {total_processes}개")
            print("🛑 기존 프로세스 종료 중...")
            
            all_processes = processes['web'] + processes['trading']
            result = self.kill_processes(all_processes)
            print(f"✅ 종료된 프로세스: {len(result['killed'])}개")
            
            # 포트 해제 대기
            if self.wait_for_port(self.web_port):
                print("✅ 웹 서버 포트 해제 완료")
            else:
                print("⚠️  웹 서버 포트가 아직 사용 중입니다.")
        else:
            print("✅ 실행 중인 프로세스가 없습니다.")
        
        # 2. 서버 시작
        web_process = self.start_web_server()
        trading_process = self.start_trading_server()
        
        if web_process and trading_process:
            print("\n🎉 모든 서버가 성공적으로 시작되었습니다!")
            print("📝 종료하려면 Ctrl+C를 누르세요.")
            
            try:
                # 서버 출력 모니터링
                while True:
                    # 웹 서버 출력
                    if web_process.poll() is None:
                        line = web_process.stdout.readline()
                        if line:
                            print(f"[웹] {line.rstrip()}")
                    
                    # 트레이딩 서버 출력
                    if trading_process.poll() is None:
                        line = trading_process.stdout.readline()
                        if line:
                            print(f"[트레이딩] {line.rstrip()}")
                    
                    # 프로세스가 종료되었는지 확인
                    if web_process.poll() is not None and trading_process.poll() is not None:
                        break
                        
            except KeyboardInterrupt:
                print("\n🛑 서버 종료 중...")
                web_process.terminate()
                trading_process.terminate()
                web_process.wait()
                trading_process.wait()
                self.cleanup()
                print("✅ 서버가 종료되었습니다.")
                return True
        else:
            print("❌ 일부 서버 시작에 실패했습니다.")
            return False
    
    def restart_all(self) -> bool:
        """모든 서버를 재시작합니다."""
        print("🔄 A-ki 서버 재시작")
        print("=" * 50)
        
        # 1. 모든 서버 중지
        if not self.stop_all():
            return False
        
        # 2. 잠시 대기
        print("⏳ 3초 대기 중...")
        time.sleep(3)
        
        # 3. 모든 서버 시작
        return self.start_all()
    
    def status(self):
        """서버 상태를 확인합니다."""
        print("📊 A-ki 서버 상태")
        print("=" * 50)
        
        processes = self.find_processes()
        
        # 웹 서버 상태
        if processes['web']:
            print("🌐 웹 서버: 실행 중")
            for proc in processes['web']:
                try:
                    print(f"  - PID {proc.pid}: {proc.name()}")
                except psutil.NoSuchProcess:
                    continue
        else:
            print("🌐 웹 서버: 중지됨")
        
        # 트레이딩 서버 상태
        if processes['trading']:
            print("📈 트레이딩 서버: 실행 중")
            for proc in processes['trading']:
                try:
                    print(f"  - PID {proc.pid}: {proc.name()}")
                except psutil.NoSuchProcess:
                    continue
        else:
            print("📈 트레이딩 서버: 중지됨")
        
        # 포트 상태
        if self.wait_for_port(self.web_port, timeout=1):
            print(f"🔌 포트 {self.web_port}: 사용 가능")
        else:
            print(f"🔌 포트 {self.web_port}: 사용 중")

def signal_handler(signum, frame):
    """시그널 핸들러"""
    print("\n🛑 서버 종료 신호를 받았습니다.")
    sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 aki_server_control.py start    # 모든 서버 시작")
        print("  python3 aki_server_control.py stop     # 모든 서버 중지")
        print("  python3 aki_server_control.py restart  # 모든 서버 재시작")
        print("  python3 aki_server_control.py status   # 서버 상태 확인")
        sys.exit(1)
    
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 컨트롤러 실행
    controller = AkiServerController()
    command = sys.argv[1].lower()
    force = '--force' in sys.argv or '-f' in sys.argv
    
    if command == 'start':
        controller.start_all()
    elif command == 'stop':
        controller.stop_all(force)
    elif command == 'restart':
        controller.restart_all()
    elif command == 'status':
        controller.status()
    else:
        print(f"알 수 없는 명령어: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 