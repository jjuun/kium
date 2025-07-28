"""
감시 종목 관리 시스템
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from src.core.logger import logger
from src.core.config import Config


@dataclass
class WatchlistItem:
    """감시 종목 정보"""

    id: Optional[int]
    symbol: str
    symbol_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WatchlistManager:
    """감시 종목 관리 클래스"""

    def __init__(self, db_path: str = "auto_trading.db"):
        """
        초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 감시 종목 테이블 생성
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL UNIQUE,
                        symbol_name TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        is_test BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 인덱스 생성
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_watchlist_symbol 
                    ON watchlist(symbol)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_watchlist_active 
                    ON watchlist(is_active)
                """
                )

                conn.commit()
                logger.info("감시 종목 데이터베이스 초기화 완료")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    def _normalize_symbol(self, symbol: str) -> str:
        """종목코드에서 A 접두사 제거"""
        return symbol[1:] if symbol.startswith("A") else symbol

    def add_symbol(self, symbol: str, symbol_name: str = None, is_test: bool = False) -> bool:
        """
        감시 종목 추가

        Args:
            symbol: 종목코드
            symbol_name: 종목명 (선택사항)
            is_test: 테스트 데이터 여부 (기본값: False)

        Returns:
            bool: 추가 성공 여부
        """
        try:
            # 종목코드 정규화 (A 접두사 제거)
            symbol = self._normalize_symbol(symbol)

            # 종목명이 없으면 종목코드로 설정
            if not symbol_name:
                symbol_name = symbol

            # 유효성 검사: 테스트 데이터 방지
            if not is_test:
                # 1. 종목명이 종목코드와 동일한 경우 거부 (테스트 데이터 감지)
                if symbol == symbol_name:
                    logger.warning(f"테스트 데이터 감지: 종목명이 종목코드와 동일 - {symbol}")
                    return False
                
                # 2. 새로운 종목 등록 시 로그 기록 (동적 관리)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 중복 확인
                cursor.execute("SELECT id FROM watchlist WHERE symbol = ?", (symbol,))
                if cursor.fetchone():
                    logger.warning(f"이미 등록된 종목입니다: {symbol}")
                    return False

                # 종목 추가 (is_test 플래그 포함)
                cursor.execute(
                    """
                    INSERT INTO watchlist (symbol, symbol_name, is_active, is_test, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?)
                """,
                    (symbol, symbol_name, is_test, datetime.now(), datetime.now()),
                )

                conn.commit()
                test_flag = "[TEST]" if is_test else ""
                logger.info(f"감시 종목 추가 완료: {symbol} ({symbol_name}) {test_flag}")
                return True

        except Exception as e:
            logger.error(f"감시 종목 추가 실패: {e}")
            return False

    def remove_symbol(self, symbol: str) -> bool:
        """
        감시 종목 제거

        Args:
            symbol: 종목코드

        Returns:
            bool: 제거 성공 여부
        """
        try:
            # 종목코드 정규화 (A 접두사 제거)
            symbol = self._normalize_symbol(symbol)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"감시 종목 제거 완료: {symbol}")
                    return True
                else:
                    logger.warning(f"등록되지 않은 종목입니다: {symbol}")
                    return False

        except Exception as e:
            logger.error(f"감시 종목 제거 실패: {e}")
            return False

    def update_symbol(
        self, symbol: str, symbol_name: str = None, is_active: bool = None
    ) -> bool:
        """
        감시 종목 정보 수정

        Args:
            symbol: 종목코드
            symbol_name: 종목명 (선택사항)
            is_active: 활성화 여부 (선택사항)

        Returns:
            bool: 수정 성공 여부
        """
        try:
            # 종목코드 정규화 (A 접두사 제거)
            symbol = self._normalize_symbol(symbol)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 업데이트할 필드 구성
                update_fields = []
                params = []

                if symbol_name is not None:
                    update_fields.append("symbol_name = ?")
                    params.append(symbol_name)

                if is_active is not None:
                    update_fields.append("is_active = ?")
                    params.append(is_active)

                if not update_fields:
                    logger.warning("수정할 내용이 없습니다.")
                    return False

                update_fields.append("updated_at = ?")
                params.append(datetime.now())
                params.append(symbol)

                # 업데이트 실행
                query = (
                    f"UPDATE watchlist SET {', '.join(update_fields)} WHERE symbol = ?"
                )
                cursor.execute(query, params)

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"감시 종목 수정 완료: {symbol}")
                    return True
                else:
                    logger.warning(f"등록되지 않은 종목입니다: {symbol}")
                    return False

        except Exception as e:
            logger.error(f"감시 종목 수정 실패: {e}")
            return False

    def get_all_symbols(self, active_only: bool = False) -> List[WatchlistItem]:
        """
        모든 감시 종목 조회

        Args:
            active_only: 활성화된 종목만 조회

        Returns:
            List[WatchlistItem]: 감시 종목 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if active_only:
                    cursor.execute(
                        """
                        SELECT id, symbol, symbol_name, is_active, created_at, updated_at
                        FROM watchlist 
                        WHERE is_active = 1
                        ORDER BY symbol
                    """
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, symbol, symbol_name, is_active, created_at, updated_at
                        FROM watchlist 
                        ORDER BY symbol
                    """
                    )

                items = []
                for row in cursor.fetchall():
                    item = WatchlistItem(
                        id=row[0],
                        symbol=row[1],
                        symbol_name=row[2],
                        is_active=bool(row[3]),
                        created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                        updated_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    )
                    items.append(item)

                return items

        except Exception as e:
            logger.error(f"감시 종목 조회 실패: {e}")
            return []

    def get_symbol(self, symbol: str) -> Optional[WatchlistItem]:
        """
        특정 종목 조회

        Args:
            symbol: 종목코드

        Returns:
            Optional[WatchlistItem]: 종목 정보
        """
        try:
            # 종목코드 정규화 (A 접두사 제거)
            symbol = self._normalize_symbol(symbol)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, symbol, symbol_name, is_active, created_at, updated_at
                    FROM watchlist 
                    WHERE symbol = ?
                """,
                    (symbol,),
                )

                row = cursor.fetchone()
                if row:
                    return WatchlistItem(
                        id=row[0],
                        symbol=row[1],
                        symbol_name=row[2],
                        is_active=bool(row[3]),
                        created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                        updated_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    )
                else:
                    return None

        except Exception as e:
            logger.error(f"종목 조회 실패: {e}")
            return None

    def is_symbol_watched(self, symbol: str) -> bool:
        """
        종목이 감시 목록에 있는지 확인

        Args:
            symbol: 종목코드

        Returns:
            bool: 감시 목록 포함 여부
        """
        try:
            # 종목코드 정규화 (A 접두사 제거)
            symbol = self._normalize_symbol(symbol)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT 1 FROM watchlist 
                    WHERE symbol = ? AND is_active = 1
                """,
                    (symbol,),
                )

                return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"종목 감시 여부 확인 실패: {e}")
            return False

    def get_active_symbols(self) -> List[str]:
        """
        활성화된 감시 종목 코드 목록 조회

        Returns:
            List[str]: 활성화된 종목코드 목록
        """
        try:
            items = self.get_all_symbols(active_only=True)
            return [item.symbol for item in items]

        except Exception as e:
            logger.error(f"활성화된 종목 조회 실패: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        감시 종목 통계 정보 조회

        Returns:
            Dict[str, Any]: 통계 정보
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 전체 종목 수
                cursor.execute("SELECT COUNT(*) FROM watchlist")
                total_count = cursor.fetchone()[0]

                # 활성화된 종목 수
                cursor.execute("SELECT COUNT(*) FROM watchlist WHERE is_active = 1")
                active_count = cursor.fetchone()[0]

                # 비활성화된 종목 수
                cursor.execute("SELECT COUNT(*) FROM watchlist WHERE is_active = 0")
                inactive_count = cursor.fetchone()[0]

                # 최근 추가된 종목 (7일 이내)
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM watchlist 
                    WHERE created_at >= datetime('now', '-7 days')
                """
                )
                recent_count = cursor.fetchone()[0]

                return {
                    "total_count": total_count,
                    "active_count": active_count,
                    "inactive_count": inactive_count,
                    "recent_count": recent_count,
                }

        except Exception as e:
            logger.error(f"통계 정보 조회 실패: {e}")
            return {
                "total_count": 0,
                "active_count": 0,
                "inactive_count": 0,
                "recent_count": 0,
            }

    def clear_all(self) -> bool:
        """
        모든 감시 종목 삭제

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM watchlist")
                deleted_count = cursor.rowcount

                conn.commit()
                logger.info(f"모든 감시 종목 삭제 완료: {deleted_count}개")
                return True

        except Exception as e:
            logger.error(f"감시 종목 전체 삭제 실패: {e}")
            return False

    def get_user_symbols(self) -> List[str]:
        """
        사용자가 직접 등록한 종목명 목록 조회 (is_test=False인 종목들)

        Returns:
            List[str]: 사용자 등록 종목명 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT DISTINCT symbol_name 
                    FROM watchlist 
                    WHERE is_test = 0 AND is_active = 1
                    ORDER BY symbol_name
                """
                )

                user_symbols = [row[0] for row in cursor.fetchall()]
                logger.info(f"사용자 등록 종목 수: {len(user_symbols)}")
                return user_symbols

        except Exception as e:
            logger.error(f"사용자 등록 종목 조회 실패: {e}")
            return []

    def get_test_symbols(self) -> List[str]:
        """
        테스트 종목명 목록 조회 (is_test=True인 종목들)

        Returns:
            List[str]: 테스트 종목명 목록
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT DISTINCT symbol_name 
                    FROM watchlist 
                    WHERE is_test = 1
                    ORDER BY symbol_name
                """
                )

                test_symbols = [row[0] for row in cursor.fetchall()]
                logger.info(f"테스트 종목 수: {len(test_symbols)}")
                return test_symbols

        except Exception as e:
            logger.error(f"테스트 종목 조회 실패: {e}")
            return []

    def cleanup_test_data(self) -> int:
        """
        테스트 데이터 정리 (is_test=True인 종목들 삭제)

        Returns:
            int: 삭제된 종목 수
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 삭제할 테스트 종목 수 확인
                cursor.execute("SELECT COUNT(*) FROM watchlist WHERE is_test = 1")
                test_count = cursor.fetchone()[0]

                if test_count == 0:
                    logger.info("삭제할 테스트 데이터가 없습니다.")
                    return 0

                # 테스트 종목 삭제
                cursor.execute("DELETE FROM watchlist WHERE is_test = 1")
                deleted_count = cursor.rowcount

                conn.commit()
                logger.info(f"테스트 데이터 정리 완료: {deleted_count}개 삭제")
                return deleted_count

        except Exception as e:
            logger.error(f"테스트 데이터 정리 실패: {e}")
            return 0
