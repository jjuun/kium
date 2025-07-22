#!/usr/bin/env python3
"""
A-ki 자동매매 시스템 통합 서버 시작 스크립트
기존 프로세스를 정리하고 새로운 서버를 시작합니다.
"""

import os
import sys
import time
import signal
import subprocess
import psutil
from pathlib import Path

class ProcessManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.pid_file = self.project_root / "server.pid"
        self.port = 8000
        
    def find_processes(self):
        """현재 실행 중인 관련 프로세스들을 찾습니다."""
        processes = []
        
        # Python 프로세스 중 A-ki 관련 프로세스 찾기
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    cmdline = proc.info['cmdline']
                    if cmdline and any('A-ki' in str(arg) or 'main.py' in str(arg) or 'web_dashboard' in str(arg) for arg in cmdline):
                        processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        # 포트 8000을 사용하는 프로세스 찾기
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == self.port and conn.status == 'LISTEN':
                    try:
                        proc = psutil.Process(conn.pid)
                        if proc not in processes:
                            processes.append(proc)
                    except psutil.NoSuchProcess:
                        continue
        except psutil.AccessDenied:
            pass
            
        return processes
    
    def kill_processes(self, processes):
        """지정된 프로세스들을 종료합니다."""
        killed = []
        for proc in processes:
            try:
                print(f"프로세스 종료 중: PID {proc.pid} - {proc.name()}")
                proc.terminate()
                killed.append(proc.pid)
            except psutil.NoSuchProcess:
                continue
            except psutil.AccessDenied:
                print(f"프로세스 종료 권한 없음: PID {proc.pid}")
                
        # 강제 종료가 필요한 경우
        time.sleep(2)
        for proc in processes:
            try:
                if proc.is_running():
                    print(f"강제 종료: PID {proc.pid}")
                    proc.kill()
            except psutil.NoSuchProcess:
                continue
                
        return killed
    
    def wait_for_port(self, timeout=10):
        """포트가 사용 가능할 때까지 대기합니다."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                for conn in psutil.net_connections():
                    if conn.laddr.port == self.port and conn.status == 'LISTEN':
                        return False
                return True
            except psutil.AccessDenied:
                return True
            time.sleep(0.5)
        return False
    
    def start_web_server(self):
        """웹 서버를 시작합니다."""
        print("🌐 웹 서버 시작 중...")
        
        # uvicorn으로 웹 서버 시작
        cmd = [
            sys.executable, "-m", "uvicorn", 
            "src.web.web_dashboard:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
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
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"✅ 웹 서버 시작됨 (PID: {process.pid})")
            print(f"🌍 서버 주소: http://localhost:{self.port}")
            
            return process
            
        except Exception as e:
            print(f"❌ 웹 서버 시작 실패: {e}")
            return None
    
    def cleanup(self):
        """정리 작업을 수행합니다."""
        # PID 파일 삭제
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except:
                pass
    
    def run(self):
        """메인 실행 함수"""
        print("🚀 A-ki 자동매매 시스템 서버 시작")
        print("=" * 50)
        
        # 1. 기존 프로세스 정리
        print("🔍 기존 프로세스 확인 중...")
        processes = self.find_processes()
        
        if processes:
            print(f"📋 발견된 프로세스: {len(processes)}개")
            for proc in processes:
                try:
                    print(f"  - PID {proc.pid}: {proc.name()}")
                except psutil.NoSuchProcess:
                    continue
            
            print("🛑 기존 프로세스 종료 중...")
            killed = self.kill_processes(processes)
            print(f"✅ 종료된 프로세스: {len(killed)}개")
            
            # 포트 해제 대기
            if self.wait_for_port():
                print("✅ 포트 8000 해제 완료")
            else:
                print("⚠️  포트 8000이 아직 사용 중입니다.")
        else:
            print("✅ 실행 중인 프로세스가 없습니다.")
        
        # 2. 웹 서버 시작
        process = self.start_web_server()
        
        if process:
            print("\n🎉 서버가 성공적으로 시작되었습니다!")
            print("📝 종료하려면 Ctrl+C를 누르세요.")
            
            try:
                # 서버 출력 모니터링
                for line in process.stdout:
                    print(line.rstrip())
            except KeyboardInterrupt:
                print("\n🛑 서버 종료 중...")
                process.terminate()
                process.wait()
                self.cleanup()
                print("✅ 서버가 종료되었습니다.")
        else:
            print("❌ 서버 시작에 실패했습니다.")
            sys.exit(1)

def signal_handler(signum, frame):
    """시그널 핸들러"""
    print("\n🛑 서버 종료 신호를 받았습니다.")
    sys.exit(0)

if __name__ == "__main__":
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 프로세스 매니저 실행
    manager = ProcessManager()
    manager.run() 