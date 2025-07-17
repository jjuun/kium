#!/usr/bin/env python3
"""
잘못된 종목코드 수정 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from src.core.logger import logger

def fix_symbol_codes():
    """잘못된 종목코드 수정"""
    try:
        with sqlite3.connect("auto_trading.db") as conn:
            cursor = conn.cursor()
            
            # 현재 감시종목 확인
            cursor.execute("SELECT id, symbol, symbol_name FROM watchlist")
            current_symbols = cursor.fetchall()
            
            logger.info("현재 감시종목:")
            for row in current_symbols:
                logger.info(f"  - {row[1]} ({row[2]})")
            
            # 잘못된 종목코드 수정 (A 접두사 제거)
            corrections = [
                ("A900300", "900300"),
                ("A005930", "005930"),
                ("A000660", "000660"),
                ("A035420", "035420"),
                ("A051910", "051910"),
                ("A006400", "006400"),
                ("A035720", "035720"),
                ("A207940", "207940"),
                ("A068270", "068270"),
                ("A323410", "323410"),
            ]
            
            updated_count = 0
            for old_symbol, new_symbol in corrections:
                cursor.execute("UPDATE watchlist SET symbol = ? WHERE symbol = ?", (new_symbol, old_symbol))
                if cursor.rowcount > 0:
                    updated_count += 1
                    logger.info(f"종목코드 수정: {old_symbol} → {new_symbol}")
            
            # 매매 조건 테이블명 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%condition%'")
            condition_tables = cursor.fetchall()
            logger.info(f"매매 조건 관련 테이블: {[table[0] for table in condition_tables]}")
            
            # 매매 조건 테이블 수정 (테이블명이 다를 수 있음)
            for table_name in [table[0] for table in condition_tables]:
                try:
                    for old_symbol, new_symbol in corrections:
                        cursor.execute(f"UPDATE {table_name} SET symbol = ? WHERE symbol = ?", (new_symbol, old_symbol))
                        if cursor.rowcount > 0:
                            logger.info(f"매매 조건 테이블 {table_name} 종목코드 수정: {old_symbol} → {new_symbol}")
                except Exception as e:
                    logger.warning(f"테이블 {table_name} 수정 실패: {e}")
            
            conn.commit()
            logger.info(f"종목코드 수정 완료: {updated_count}개 수정됨")
            
            # 수정 후 감시종목 확인
            cursor.execute("SELECT id, symbol, symbol_name FROM watchlist ORDER BY symbol")
            updated_symbols = cursor.fetchall()
            
            logger.info("수정 후 감시종목:")
            for row in updated_symbols:
                logger.info(f"  - {row[1]} ({row[2]})")
                
    except Exception as e:
        logger.error(f"종목코드 수정 실패: {e}")

if __name__ == "__main__":
    fix_symbol_codes() 