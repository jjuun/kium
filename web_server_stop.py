#!/usr/bin/env python3
"""
A-ki 자동매매 시스템 서버 종료 스크립트
실행 중인 모든 관련 프로세스를 안전하게 종료합니다.
"""

import os
import sys
import time
import psutil
from pathlib import Path

class ProcessKiller:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.pid_file = self.project_root / "server.pid"
        self.port = 8000
        
    def find_processes(self):
        """현재 실행 중인 관련 프로세스들을 찾습니다."""
        processes = []
        
        # PID 파일에서 프로세스 확인
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running():
                            processes.append(proc)
                    except psutil.NoSuchProcess:
                        pass
            except (ValueError, IOError):
                pass
        
        # Python 프로세스 중 A-ki 관련 프로세스 찾기
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                    cmdline = proc.info['cmdline']
                    if cmdline and any('A-ki' in str(arg) or 'main.py' in str(arg) or 'web_dashboard' in str(arg) for arg in cmdline):
                        if proc not in processes:
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
    
    def kill_processes(self, processes, force=False):
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
                    
        return killed, failed
    
    def cleanup(self):
        """정리 작업을 수행합니다."""
        # PID 파일 삭제
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
                print("✅ PID 파일 삭제됨")
            except:
                print("⚠️  PID 파일 삭제 실패")
    
    def run(self, force=False):
        """메인 실행 함수"""
        print("🛑 A-ki 자동매매 시스템 서버 종료")
        print("=" * 50)
        
        # 1. 기존 프로세스 확인
        print("🔍 실행 중인 프로세스 확인 중...")
        processes = self.find_processes()
        
        if not processes:
            print("✅ 실행 중인 프로세스가 없습니다.")
            self.cleanup()
            return
        
        print(f"📋 발견된 프로세스: {len(processes)}개")
        for proc in processes:
            try:
                print(f"  - PID {proc.pid}: {proc.name()}")
            except psutil.NoSuchProcess:
                continue
        
        # 2. 프로세스 종료
        print("🛑 프로세스 종료 중...")
        killed, failed = self.kill_processes(processes, force)
        
        print(f"✅ 종료된 프로세스: {len(killed)}개")
        if failed:
            print(f"❌ 종료 실패한 프로세스: {len(failed)}개")
        
        # 3. 정리 작업
        self.cleanup()
        
        print("🎉 서버 종료 완료!")

def main():
    force = '--force' in sys.argv or '-f' in sys.argv
    
    killer = ProcessKiller()
    killer.run(force)

if __name__ == "__main__":
    main() 