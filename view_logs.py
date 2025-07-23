#!/usr/bin/env python3
"""
A-ki 서버 로그 뷰어
실시간으로 서버 로그를 확인할 수 있습니다.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

def tail_log_file(log_file: Path, lines: int = 50, follow: bool = False):
    """로그 파일의 마지막 부분을 출력하고 필요시 실시간 추적"""
    if not log_file.exists():
        print(f"❌ 로그 파일이 없습니다: {log_file}")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # 마지막 N줄 읽기
            all_lines = f.readlines()
            start_line = max(0, len(all_lines) - lines)
            
            print(f"📋 {log_file.name} (마지막 {lines}줄):")
            print("=" * 60)
            
            for line in all_lines[start_line:]:
                print(line.rstrip())
            
            if follow:
                print("\n🔄 실시간 로그 추적 중... (Ctrl+C로 종료)")
                print("=" * 60)
                
                # 파일 크기 기억
                f.seek(0, 2)  # 파일 끝으로 이동
                last_size = f.tell()
                
                while True:
                    time.sleep(1)
                    
                    # 파일 크기 확인
                    current_size = f.tell()
                    if current_size > last_size:
                        # 새로운 내용 읽기
                        f.seek(last_size)
                        new_content = f.read()
                        if new_content:
                            print(new_content.rstrip())
                        last_size = current_size
                        
    except KeyboardInterrupt:
        if follow:
            print("\n🛑 로그 추적 종료")
    except Exception as e:
        print(f"❌ 로그 읽기 오류: {e}")

def view_all_logs(log_dir: Path, lines: int = 30, follow: bool = False):
    """모든 로그 파일 확인"""
    log_files = [
        log_dir / "server.log",
        log_dir / "trading.log", 
        log_dir / "monitor.log"
    ]
    
    for log_file in log_files:
        if log_file.exists():
            print(f"\n{'='*80}")
            tail_log_file(log_file, lines, follow=False)  # follow는 개별 파일에서만 지원
        else:
            print(f"\n❌ 로그 파일이 없습니다: {log_file.name}")

def search_logs(log_dir: Path, keyword: str, case_sensitive: bool = False):
    """로그에서 키워드 검색"""
    log_files = [
        log_dir / "server.log",
        log_dir / "trading.log",
        log_dir / "monitor.log"
    ]
    
    found_count = 0
    
    for log_file in log_files:
        if not log_file.exists():
            continue
            
        print(f"\n🔍 {log_file.name}에서 '{keyword}' 검색:")
        print("-" * 60)
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    search_line = line if case_sensitive else line.lower()
                    search_keyword = keyword if case_sensitive else keyword.lower()
                    
                    if search_keyword in search_line:
                        found_count += 1
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(f"[{timestamp}] {line_num:6d}: {line.rstrip()}")
                        
        except Exception as e:
            print(f"❌ 검색 오류: {e}")
    
    print(f"\n📊 검색 결과: {found_count}개 발견")

def main():
    parser = argparse.ArgumentParser(description='A-ki 서버 로그 뷰어')
    parser.add_argument('--file', choices=['server', 'trading', 'monitor'], 
                       help='특정 로그 파일 선택')
    parser.add_argument('--lines', type=int, default=50, help='출력할 줄 수')
    parser.add_argument('--follow', '-f', action='store_true', help='실시간 추적')
    parser.add_argument('--search', '-s', help='키워드 검색')
    parser.add_argument('--case-sensitive', action='store_true', help='대소문자 구분 검색')
    
    args = parser.parse_args()
    
    log_dir = Path(__file__).parent / "logs"
    
    if not log_dir.exists():
        print(f"❌ 로그 디렉토리가 없습니다: {log_dir}")
        return
    
    if args.search:
        # 검색 모드
        search_logs(log_dir, args.search, args.case_sensitive)
    elif args.file:
        # 특정 파일 모드
        log_file = log_dir / f"{args.file}.log"
        tail_log_file(log_file, args.lines, args.follow)
    else:
        # 전체 로그 모드
        view_all_logs(log_dir, args.lines, args.follow)

if __name__ == "__main__":
    main() 