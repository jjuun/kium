"""
감시 종목 관리 시스템 테스트
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.auto_trading.watchlist_manager import WatchlistManager, WatchlistItem


class TestWatchlistManager(unittest.TestCase):
    """감시 종목 관리 시스템 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        # 임시 데이터베이스 파일 생성
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # WatchlistManager 인스턴스 생성
        self.watchlist_manager = WatchlistManager(self.db_path)

    def tearDown(self):
        """테스트 정리"""
        # 임시 데이터베이스 파일 삭제
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_init_database(self):
        """데이터베이스 초기화 테스트"""
        # 데이터베이스 파일이 생성되었는지 확인
        self.assertTrue(os.path.exists(self.db_path))

        # 테이블이 생성되었는지 확인
        import sqlite3

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)

    def test_add_symbol(self):
        """종목 추가 테스트"""
        # 종목 추가
        success = self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.assertTrue(success)

        # 중복 추가 시도 (실패해야 함)
        success = self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.assertFalse(success)

        # 종목코드 정규화 테스트 (A 접두사 자동 추가)
        success = self.watchlist_manager.add_symbol("000660", "SK하이닉스")
        self.assertTrue(success)

        # 조회하여 확인
        items = self.watchlist_manager.get_all_symbols()
        self.assertEqual(len(items), 2)

        symbols = [item.symbol for item in items]
        self.assertIn("005935", symbols)
        self.assertIn("000660", symbols)

    def test_remove_symbol(self):
        """종목 제거 테스트"""
        # 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")

        # 종목 제거
        success = self.watchlist_manager.remove_symbol("005935")
        self.assertTrue(success)

        # 존재하지 않는 종목 제거 시도
        success = self.watchlist_manager.remove_symbol("999999")
        self.assertFalse(success)

        # 조회하여 확인
        items = self.watchlist_manager.get_all_symbols()
        self.assertEqual(len(items), 0)

    def test_update_symbol(self):
        """종목 정보 수정 테스트"""
        # 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")

        # 종목명 수정
        success = self.watchlist_manager.update_symbol(
            "005935", symbol_name="삼성전자(수정)"
        )
        self.assertTrue(success)

        # 활성화 상태 수정
        success = self.watchlist_manager.update_symbol("005935", is_active=False)
        self.assertTrue(success)

        # 조회하여 확인
        item = self.watchlist_manager.get_symbol("005935")
        self.assertIsNotNone(item)
        self.assertEqual(item.symbol_name, "삼성전자(수정)")
        self.assertFalse(item.is_active)

    def test_get_all_symbols(self):
        """전체 종목 조회 테스트"""
        # 여러 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.watchlist_manager.add_symbol("000660", "SK하이닉스")
        self.watchlist_manager.add_symbol("035420", "NAVER")

        # 전체 조회
        items = self.watchlist_manager.get_all_symbols()
        self.assertEqual(len(items), 3)

        # 활성화된 종목만 조회
        active_items = self.watchlist_manager.get_all_symbols(active_only=True)
        self.assertEqual(len(active_items), 3)  # 모두 활성화 상태

        # 하나를 비활성화
        self.watchlist_manager.update_symbol("005935", is_active=False)
        active_items = self.watchlist_manager.get_all_symbols(active_only=True)
        self.assertEqual(len(active_items), 2)

    def test_get_symbol(self):
        """특정 종목 조회 테스트"""
        # 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")

        # 존재하는 종목 조회
        item = self.watchlist_manager.get_symbol("005935")
        self.assertIsNotNone(item)
        self.assertEqual(item.symbol, "005935")
        self.assertEqual(item.symbol_name, "삼성전자")

        # 존재하지 않는 종목 조회
        item = self.watchlist_manager.get_symbol("999999")
        self.assertIsNone(item)

    def test_is_symbol_watched(self):
        """종목 감시 여부 확인 테스트"""
        # 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")

        # 감시 중인 종목 확인
        is_watched = self.watchlist_manager.is_symbol_watched("005935")
        self.assertTrue(is_watched)

        # 감시하지 않는 종목 확인
        is_watched = self.watchlist_manager.is_symbol_watched("999999")
        self.assertFalse(is_watched)

        # 비활성화된 종목 확인
        self.watchlist_manager.update_symbol("005935", is_active=False)
        is_watched = self.watchlist_manager.is_symbol_watched("005935")
        self.assertFalse(is_watched)

    def test_get_active_symbols(self):
        """활성화된 종목 코드 목록 조회 테스트"""
        # 여러 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.watchlist_manager.add_symbol("000660", "SK하이닉스")
        self.watchlist_manager.add_symbol("035420", "NAVER")

        # 하나를 비활성화
        self.watchlist_manager.update_symbol("005935", is_active=False)

        # 활성화된 종목 코드 목록 조회
        active_symbols = self.watchlist_manager.get_active_symbols()
        self.assertEqual(len(active_symbols), 2)
        self.assertIn("000660", active_symbols)
        self.assertIn("035420", active_symbols)
        self.assertNotIn("005935", active_symbols)

    def test_get_statistics(self):
        """통계 정보 조회 테스트"""
        # 여러 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.watchlist_manager.add_symbol("000660", "SK하이닉스")
        self.watchlist_manager.add_symbol("035420", "NAVER")

        # 하나를 비활성화
        self.watchlist_manager.update_symbol("005935", is_active=False)

        # 통계 정보 조회
        stats = self.watchlist_manager.get_statistics()

        self.assertEqual(stats["total_count"], 3)
        self.assertEqual(stats["active_count"], 2)
        self.assertEqual(stats["inactive_count"], 1)
        self.assertGreaterEqual(stats["recent_count"], 3)  # 최근 7일 이내

    def test_clear_all(self):
        """전체 삭제 테스트"""
        # 여러 종목 추가
        self.watchlist_manager.add_symbol("005935", "삼성전자")
        self.watchlist_manager.add_symbol("000660", "SK하이닉스")

        # 전체 삭제
        success = self.watchlist_manager.clear_all()
        self.assertTrue(success)

        # 조회하여 확인
        items = self.watchlist_manager.get_all_symbols()
        self.assertEqual(len(items), 0)

    def test_watchlist_item_to_dict(self):
        """WatchlistItem to_dict 메서드 테스트"""
        item = WatchlistItem(
            id=1,
            symbol="005935",
            symbol_name="삼성전자",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        item_dict = item.to_dict()

        self.assertEqual(item_dict["id"], 1)
        self.assertEqual(item_dict["symbol"], "005935")
        self.assertEqual(item_dict["symbol_name"], "삼성전자")
        self.assertTrue(item_dict["is_active"])
        self.assertIsNotNone(item_dict["created_at"])
        self.assertIsNotNone(item_dict["updated_at"])


if __name__ == "__main__":
    unittest.main()
