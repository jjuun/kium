"""
매수/매도 조건 관리 시스템
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from src.core.logger import logger

@dataclass
class ConditionItem:
    id: Optional[int]
    symbol: str
    condition_type: str  # 'buy' or 'sell'
    category: str        # 'price', 'rsi', 'ma', 'volume', 'volatility', 'custom'
    value: str           # 조건 값(예: 가격, 지표 등)
    description: str     # 설명
    success_rate: Optional[float]  # 성공률
    total_signals: int   # 총 신호 수
    successful_signals: int  # 성공한 신호 수
    avg_profit: Optional[float]  # 평균 수익률
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'condition_type': self.condition_type,
            'category': self.category,
            'value': self.value,
            'description': self.description,
            'success_rate': self.success_rate,
            'total_signals': self.total_signals,
            'successful_signals': self.successful_signals,
            'avg_profit': self.avg_profit,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class ConditionGroup:
    id: Optional[int]
    symbol: str
    name: str
    logic: str  # 'AND' or 'OR'
    priority: int
    is_active: bool
    conditions: List[ConditionItem]  # 그룹에 포함된 조건들
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'logic': self.logic,
            'priority': self.priority,
            'is_active': self.is_active,
            'conditions': [condition.to_dict() for condition in self.conditions],
            'condition_count': len(self.conditions),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ConditionManager:
    """매수/매도 조건 관리 클래스"""
    def __init__(self, db_path: str = "auto_trading.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conditions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        condition_type TEXT NOT NULL, -- 'buy' or 'sell'
                        category TEXT DEFAULT 'custom',
                        value TEXT NOT NULL,
                        description TEXT,
                        success_rate REAL DEFAULT NULL,
                        total_signals INTEGER DEFAULT 0,
                        successful_signals INTEGER DEFAULT 0,
                        avg_profit REAL DEFAULT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conditions_symbol_type
                    ON conditions(symbol, condition_type)
                """)
                
                # 조건 그룹 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS condition_groups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        name TEXT NOT NULL,
                        logic TEXT NOT NULL, -- 'AND' or 'OR'
                        priority INTEGER DEFAULT 5,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 조건 그룹 매핑 테이블
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS condition_group_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_id INTEGER NOT NULL,
                        condition_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (group_id) REFERENCES condition_groups(id) ON DELETE CASCADE,
                        FOREIGN KEY (condition_id) REFERENCES conditions(id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_condition_groups_symbol
                    ON condition_groups(symbol)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_condition_group_mappings_group
                    ON condition_group_mappings(group_id)
                """)
                conn.commit()
                logger.info("매수/매도 조건 테이블 초기화 완료")
        except Exception as e:
            logger.error(f"조건 테이블 초기화 실패: {e}")
            raise
    
    def add_condition(self, symbol: str, condition_type: str, category: str, value: str, description: str = "") -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conditions (symbol, condition_type, category, value, description, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """, (symbol, condition_type, category, value, description, datetime.now(), datetime.now()))
                conn.commit()
                logger.info(f"조건 추가 완료: {symbol} {condition_type} {category} {value}")
                return True
        except Exception as e:
            logger.error(f"조건 추가 실패: {e}")
            return False
    
    def remove_condition(self, condition_id: int) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conditions WHERE id = ?", (condition_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"조건 삭제 완료: {condition_id}")
                    return True
                else:
                    logger.warning(f"조건 삭제 실패: {condition_id}")
                    return False
        except Exception as e:
            logger.error(f"조건 삭제 실패: {e}")
            return False
    
    def update_condition(self, condition_id: int, value: str = None, description: str = None, is_active: bool = None) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                update_fields = []
                params = []
                if value is not None:
                    update_fields.append("value = ?")
                    params.append(value)
                if description is not None:
                    update_fields.append("description = ?")
                    params.append(description)
                if is_active is not None:
                    update_fields.append("is_active = ?")
                    params.append(is_active)
                if not update_fields:
                    logger.warning("수정할 내용이 없습니다.")
                    return False
                update_fields.append("updated_at = ?")
                params.append(datetime.now())
                params.append(condition_id)
                query = f"UPDATE conditions SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, params)
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"조건 수정 완료: {condition_id}")
                    return True
                else:
                    logger.warning(f"조건 수정 실패: {condition_id}")
                    return False
        except Exception as e:
            logger.error(f"조건 수정 실패: {e}")
            return False
    
    def get_conditions(self, symbol: str = None, condition_type: str = None, active_only: bool = False) -> List[ConditionItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = "SELECT id, symbol, condition_type, category, value, description, success_rate, total_signals, successful_signals, avg_profit, is_active, created_at, updated_at FROM conditions WHERE 1=1"
                params = []
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                if condition_type:
                    query += " AND condition_type = ?"
                    params.append(condition_type)
                if active_only:
                    query += " AND is_active = 1"
                query += " ORDER BY created_at DESC"
                cursor.execute(query, params)
                items = []
                for row in cursor.fetchall():
                    items.append(ConditionItem(
                        id=row[0],
                        symbol=row[1],
                        condition_type=row[2],
                        category=row[3] or 'custom',
                        value=row[4],
                        description=row[5],
                        success_rate=row[6],
                        total_signals=row[7] or 0,
                        successful_signals=row[8] or 0,
                        avg_profit=row[9],
                        is_active=bool(row[10]),
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        updated_at=datetime.fromisoformat(row[12]) if row[12] else None
                    ))
                return items
        except Exception as e:
            logger.error(f"조건 목록 조회 실패: {e}")
            return []
    
    def get_condition(self, condition_id: int) -> Optional[ConditionItem]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, symbol, condition_type, category, value, description, success_rate, total_signals, successful_signals, avg_profit, is_active, created_at, updated_at FROM conditions WHERE id = ?", (condition_id,))
                row = cursor.fetchone()
                if row:
                    return ConditionItem(
                        id=row[0],
                        symbol=row[1],
                        condition_type=row[2],
                        category=row[3] or 'custom',
                        value=row[4],
                        description=row[5],
                        success_rate=row[6],
                        total_signals=row[7] or 0,
                        successful_signals=row[8] or 0,
                        avg_profit=row[9],
                        is_active=bool(row[10]),
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        updated_at=datetime.fromisoformat(row[12]) if row[12] else None
                    )
                else:
                    return None
        except Exception as e:
            logger.error(f"조건 단건 조회 실패: {e}")
            return None
    
    def update_condition_performance(self, condition_id: int, success_rate: float, total_signals: int, successful_signals: int, avg_profit: float) -> bool:
        """조건의 성과 지표 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE conditions 
                    SET success_rate = ?, total_signals = ?, successful_signals = ?, avg_profit = ?, updated_at = ?
                    WHERE id = ?
                """, (success_rate, total_signals, successful_signals, avg_profit, datetime.now(), condition_id))
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"조건 성과 업데이트 완료: {condition_id} - 성공률: {success_rate}%")
                    return True
                else:
                    logger.warning(f"조건 성과 업데이트 실패: {condition_id}")
                    return False
        except Exception as e:
            logger.error(f"조건 성과 업데이트 실패: {e}")
            return False
    
    # 조건 그룹 관리 메서드들
    def create_condition_group(self, symbol: str, name: str, logic: str, priority: int = 5) -> Optional[int]:
        """조건 그룹 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO condition_groups (symbol, name, logic, priority, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                """, (symbol, name, logic, priority, datetime.now(), datetime.now()))
                group_id = cursor.lastrowid
                conn.commit()
                logger.info(f"조건 그룹 생성 완료: {symbol} {name}")
                return group_id
        except Exception as e:
            logger.error(f"조건 그룹 생성 실패: {e}")
            return None
    
    def add_condition_to_group(self, group_id: int, condition_id: int) -> bool:
        """조건을 그룹에 추가"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO condition_group_mappings (group_id, condition_id)
                    VALUES (?, ?)
                """, (group_id, condition_id))
                conn.commit()
                logger.info(f"조건을 그룹에 추가 완료: {group_id} -> {condition_id}")
                return True
        except Exception as e:
            logger.error(f"조건을 그룹에 추가 실패: {e}")
            return False
    
    def remove_condition_from_group(self, group_id: int, condition_id: int) -> bool:
        """조건을 그룹에서 제거"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM condition_group_mappings 
                    WHERE group_id = ? AND condition_id = ?
                """, (group_id, condition_id))
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"조건을 그룹에서 제거 완료: {group_id} -> {condition_id}")
                    return True
                else:
                    logger.warning(f"조건을 그룹에서 제거 실패: {group_id} -> {condition_id}")
                    return False
        except Exception as e:
            logger.error(f"조건을 그룹에서 제거 실패: {e}")
            return False
    
    def get_condition_groups(self, symbol: str = None, active_only: bool = False) -> List[ConditionGroup]:
        """조건 그룹 목록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query = """
                    SELECT id, symbol, name, logic, priority, is_active, created_at, updated_at 
                    FROM condition_groups WHERE 1=1
                """
                params = []
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                if active_only:
                    query += " AND is_active = 1"
                query += " ORDER BY priority DESC, created_at DESC"
                
                cursor.execute(query, params)
                groups = []
                for row in cursor.fetchall():
                    group_id = row[0]
                    # 그룹에 포함된 조건들 조회
                    conditions = self._get_conditions_in_group(group_id)
                    
                    groups.append(ConditionGroup(
                        id=group_id,
                        symbol=row[1],
                        name=row[2],
                        logic=row[3],
                        priority=row[4],
                        is_active=bool(row[5]),
                        conditions=conditions,
                        created_at=datetime.fromisoformat(row[6]) if row[6] else None,
                        updated_at=datetime.fromisoformat(row[7]) if row[7] else None
                    ))
                return groups
        except Exception as e:
            logger.error(f"조건 그룹 목록 조회 실패: {e}")
            return []
    
    def _get_conditions_in_group(self, group_id: int) -> List[ConditionItem]:
        """그룹에 포함된 조건들 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.id, c.symbol, c.condition_type, c.category, c.value, c.description, 
                           c.success_rate, c.total_signals, c.successful_signals, c.avg_profit, 
                           c.is_active, c.created_at, c.updated_at
                    FROM conditions c
                    JOIN condition_group_mappings cgm ON c.id = cgm.condition_id
                    WHERE cgm.group_id = ?
                    ORDER BY c.created_at
                """, (group_id,))
                
                conditions = []
                for row in cursor.fetchall():
                    conditions.append(ConditionItem(
                        id=row[0],
                        symbol=row[1],
                        condition_type=row[2],
                        category=row[3] or 'custom',
                        value=row[4],
                        description=row[5],
                        success_rate=row[6],
                        total_signals=row[7] or 0,
                        successful_signals=row[8] or 0,
                        avg_profit=row[9],
                        is_active=bool(row[10]),
                        created_at=datetime.fromisoformat(row[11]) if row[11] else None,
                        updated_at=datetime.fromisoformat(row[12]) if row[12] else None
                    ))
                return conditions
        except Exception as e:
            logger.error(f"그룹 조건 조회 실패: {e}")
            return []
    
    def delete_condition_group(self, group_id: int) -> bool:
        """조건 그룹 삭제"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM condition_groups WHERE id = ?", (group_id,))
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"조건 그룹 삭제 완료: {group_id}")
                    return True
                else:
                    logger.warning(f"조건 그룹 삭제 실패: {group_id}")
                    return False
        except Exception as e:
            logger.error(f"조건 그룹 삭제 실패: {e}")
            return False
    
    def update_group_priority(self, group_id: int, priority: int) -> bool:
        """그룹 우선순위 업데이트"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE condition_groups 
                    SET priority = ?, updated_at = ?
                    WHERE id = ?
                """, (priority, datetime.now(), group_id))
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"그룹 우선순위 업데이트 완료: {group_id} -> {priority}")
                    return True
                else:
                    logger.warning(f"그룹 우선순위 업데이트 실패: {group_id}")
                    return False
        except Exception as e:
            logger.error(f"그룹 우선순위 업데이트 실패: {e}")
            return False 