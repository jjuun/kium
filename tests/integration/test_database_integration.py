"""
데이터베이스 통합 테스트
데이터베이스와 관련된 컴포넌트들의 통합 테스트
"""
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.auto_trading.auto_trader import AutoTrader
from src.auto_trading.watchlist_manager import WatchlistManager
from src.auto_trading.condition_manager import ConditionManager
from src.core.data_collector import DataCollector


class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    @pytest.fixture
    def temp_db_path(self):
        """임시 데이터베이스 경로"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        yield db_path
        
        # 테스트 후 정리
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def auto_trader_with_db(self, temp_db_path):
        """데이터베이스가 연결된 AutoTrader 인스턴스"""
        return AutoTrader(db_path=temp_db_path)
    
    def test_database_initialization(self, temp_db_path):
        """데이터베이스 초기화 테스트"""
        # When
        auto_trader = AutoTrader(db_path=temp_db_path)
        
        # Then
        assert os.path.exists(temp_db_path)
        
        # 테이블 존재 확인
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # watchlist 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        assert cursor.fetchone() is not None
        
        # trading_conditions 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trading_conditions'")
        assert cursor.fetchone() is not None
        
        # execution_history 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_history'")
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_watchlist_persistence(self, auto_trader_with_db):
        """감시종목 영속성 테스트"""
        # Given
        symbol = "005935"
        
        # When - 감시종목 추가
        result = auto_trader_with_db.watchlist_manager.add_symbol(symbol)
        
        # Then
        assert result is True
        
        # 데이터베이스에서 확인
        conn = sqlite3.connect(auto_trader_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM watchlist WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row[0] == symbol
        
        # When - 감시종목 제거
        result = auto_trader_with_db.watchlist_manager.remove_symbol(symbol)
        
        # Then
        assert result is True
        
        # 데이터베이스에서 확인
        conn = sqlite3.connect(auto_trader_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM watchlist WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is None
    
    def test_trading_conditions_persistence(self, auto_trader_with_db):
        """거래 조건 영속성 테스트"""
        # Given
        symbol = "005935"
        condition_type = "buy"
        category = "rsi"
        value = "RSI < 30"
        
        # When - 거래 조건 추가
        result = auto_trader_with_db.condition_manager.add_condition(
            symbol, condition_type, category, value
        )
        
        # Then
        assert result is True
        
        # 데이터베이스에서 확인
        conn = sqlite3.connect(auto_trader_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, condition_type, category, value 
            FROM trading_conditions 
            WHERE symbol = ? AND condition_type = ? AND category = ?
        """, (symbol, condition_type, category))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row[0] == symbol
        assert row[1] == condition_type
        assert row[2] == category
        assert row[3] == value
        
        # When - 거래 조건 제거
        conditions = auto_trader_with_db.condition_manager.get_conditions()
        condition_id = conditions[0]['id']
        result = auto_trader_with_db.condition_manager.remove_condition(condition_id)
        
        # Then
        assert result is True
        
        # 데이터베이스에서 확인
        conn = sqlite3.connect(auto_trader_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM trading_conditions WHERE id = ?", (condition_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is None
    
    def test_execution_history_persistence(self, auto_trader_with_db):
        """실행 이력 영속성 테스트"""
        # Given
        symbol = "005935"
        order_type = "buy"
        quantity = 5
        price = 50000
        timestamp = datetime.now()
        
        # When - 실행 이력 추가
        auto_trader_with_db._add_execution_history(
            symbol, order_type, quantity, price, timestamp
        )
        
        # Then
        # 데이터베이스에서 확인
        conn = sqlite3.connect(auto_trader_with_db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, order_type, quantity, price 
            FROM execution_history 
            WHERE symbol = ? AND order_type = ?
        """, (symbol, order_type))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row[0] == symbol
        assert row[1] == order_type
        assert row[2] == quantity
        assert row[3] == price
    
    def test_multiple_symbols_management(self, auto_trader_with_db):
        """다중 종목 관리 테스트"""
        # Given
        symbols = ["005935", "000660", "035420"]
        
        # When - 여러 종목 추가
        for symbol in symbols:
            auto_trader_with_db.watchlist_manager.add_symbol(symbol)
        
        # Then
        active_symbols = auto_trader_with_db.watchlist_manager.get_active_symbols()
        assert len(active_symbols) == 3
        for symbol in symbols:
            assert symbol in active_symbols
        
        # When - 일부 종목 제거
        auto_trader_with_db.watchlist_manager.remove_symbol("000660")
        
        # Then
        active_symbols = auto_trader_with_db.watchlist_manager.get_active_symbols()
        assert len(active_symbols) == 2
        assert "005935" in active_symbols
        assert "035420" in active_symbols
        assert "000660" not in active_symbols
    
    def test_multiple_conditions_management(self, auto_trader_with_db):
        """다중 조건 관리 테스트"""
        # Given
        conditions = [
            ("005935", "buy", "rsi", "RSI < 30"),
            ("005935", "sell", "rsi", "RSI > 70"),
            ("000660", "buy", "ma", "MA5 > MA20")
        ]
        
        # When - 여러 조건 추가
        for symbol, condition_type, category, value in conditions:
            auto_trader_with_db.condition_manager.add_condition(
                symbol, condition_type, category, value
            )
        
        # Then
        all_conditions = auto_trader_with_db.condition_manager.get_conditions()
        assert len(all_conditions) == 3
        
        # 특정 종목의 조건만 조회
        symbol_conditions = auto_trader_with_db.condition_manager.get_conditions_by_symbol("005935")
        assert len(symbol_conditions) == 2
        
        # When - 조건 제거
        condition_id = all_conditions[0]['id']
        auto_trader_with_db.condition_manager.remove_condition(condition_id)
        
        # Then
        remaining_conditions = auto_trader_with_db.condition_manager.get_conditions()
        assert len(remaining_conditions) == 2
    
    def test_database_concurrent_access(self, temp_db_path):
        """데이터베이스 동시 접근 테스트"""
        # Given
        auto_trader1 = AutoTrader(db_path=temp_db_path)
        auto_trader2 = AutoTrader(db_path=temp_db_path)
        
        # When - 두 인스턴스에서 동시에 작업
        auto_trader1.watchlist_manager.add_symbol("005935")
        auto_trader2.watchlist_manager.add_symbol("000660")
        
        # Then
        symbols1 = auto_trader1.watchlist_manager.get_active_symbols()
        symbols2 = auto_trader2.watchlist_manager.get_active_symbols()
        
        assert "005935" in symbols1
        assert "000660" in symbols1
        assert "005935" in symbols2
        assert "000660" in symbols2
    
    def test_database_transaction_rollback(self, auto_trader_with_db):
        """데이터베이스 트랜잭션 롤백 테스트"""
        # Given
        symbol = "005935"
        
        # When - 정상적인 추가
        result1 = auto_trader_with_db.watchlist_manager.add_symbol(symbol)
        
        # Then
        assert result1 is True
        
        # When - 잘못된 데이터로 추가 시도 (롤백 시뮬레이션)
        with patch.object(auto_trader_with_db.watchlist_manager, '_execute_query') as mock_execute:
            mock_execute.side_effect = sqlite3.Error("Database error")
            
            try:
                auto_trader_with_db.watchlist_manager.add_symbol("INVALID")
            except sqlite3.Error:
                pass
        
        # Then - 원래 데이터는 그대로 유지
        active_symbols = auto_trader_with_db.watchlist_manager.get_active_symbols()
        assert symbol in active_symbols
    
    def test_database_migration_compatibility(self, temp_db_path):
        """데이터베이스 마이그레이션 호환성 테스트"""
        # Given - 기존 데이터베이스에 데이터 추가
        auto_trader_old = AutoTrader(db_path=temp_db_path)
        auto_trader_old.watchlist_manager.add_symbol("005935")
        auto_trader_old.condition_manager.add_condition("005935", "buy", "rsi", "RSI < 30")
        
        # When - 새로운 인스턴스로 접근
        auto_trader_new = AutoTrader(db_path=temp_db_path)
        
        # Then - 기존 데이터가 그대로 유지
        symbols = auto_trader_new.watchlist_manager.get_active_symbols()
        conditions = auto_trader_new.condition_manager.get_conditions()
        
        assert "005935" in symbols
        assert len(conditions) == 1
        assert conditions[0]['symbol'] == "005935" 