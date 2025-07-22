"""
리스크 관리 클래스
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.core.logger import logger
from src.core.config import Config


class RiskManager:
    def __init__(self):
        self.max_position_size = Config.MAX_POSITION_SIZE
        self.stop_loss_percent = Config.STOP_LOSS_PERCENT
        self.take_profit_percent = Config.TAKE_PROFIT_PERCENT
        self.positions = {}  # 현재 포지션 정보
        self.trade_history = []  # 거래 이력

    def calculate_position_size(self, current_price, available_capital):
        """
        적정 포지션 크기 계산
        """
        try:
            # 기본 포지션 크기 (가용 자본의 10%)
            base_position = available_capital * 0.1

            # 최대 포지션 크기 제한
            position_size = min(base_position, self.max_position_size)

            # 주식 수량 계산 (정수로 반올림)
            quantity = int(position_size / current_price)

            # 최소 거래 단위 확인 (1주)
            if quantity < 1:
                quantity = 1

            actual_position_size = quantity * current_price

            logger.info(f"포지션 크기 계산: {quantity}주 ({actual_position_size:,}원)")
            return quantity, actual_position_size

        except Exception as e:
            logger.error(f"포지션 크기 계산 중 오류: {e}")
            return 0, 0

    def check_stop_loss(self, symbol, current_price):
        """
        손절 조건 확인
        """
        try:
            if symbol not in self.positions:
                return False, None

            position = self.positions[symbol]
            entry_price = position["entry_price"]

            # 손실률 계산
            loss_percent = ((entry_price - current_price) / entry_price) * 100

            # 손절 조건 확인
            if loss_percent >= self.stop_loss_percent:
                logger.warning(f"손절 조건 만족: {symbol} - 손실률 {loss_percent:.2f}%")
                return True, {
                    "action": "STOP_LOSS",
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "loss_percent": loss_percent,
                    "quantity": position["quantity"],
                }

            return False, None

        except Exception as e:
            logger.error(f"손절 확인 중 오류: {e}")
            return False, None

    def check_take_profit(self, symbol, current_price):
        """
        익절 조건 확인
        """
        try:
            if symbol not in self.positions:
                return False, None

            position = self.positions[symbol]
            entry_price = position["entry_price"]

            # 수익률 계산
            profit_percent = ((current_price - entry_price) / entry_price) * 100

            # 익절 조건 확인
            if profit_percent >= self.take_profit_percent:
                logger.info(f"익절 조건 만족: {symbol} - 수익률 {profit_percent:.2f}%")
                return True, {
                    "action": "TAKE_PROFIT",
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "profit_percent": profit_percent,
                    "quantity": position["quantity"],
                }

            return False, None

        except Exception as e:
            logger.error(f"익절 확인 중 오류: {e}")
            return False, None

    def add_position(self, symbol, quantity, price, timestamp=None):
        """
        포지션 추가
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()

            self.positions[symbol] = {
                "quantity": quantity,
                "entry_price": price,
                "entry_time": timestamp,
                "total_value": quantity * price,
            }

            logger.info(f"포지션 추가: {symbol} - {quantity}주 @ {price:,}원")

        except Exception as e:
            logger.error(f"포지션 추가 중 오류: {e}")

    def remove_position(self, symbol, exit_price, timestamp=None):
        """
        포지션 제거
        """
        try:
            if symbol not in self.positions:
                logger.warning(f"존재하지 않는 포지션: {symbol}")
                return None

            if timestamp is None:
                timestamp = datetime.now()

            position = self.positions[symbol]
            entry_price = position["entry_price"]
            quantity = position["quantity"]

            # 수익/손실 계산
            profit_loss = (exit_price - entry_price) * quantity
            profit_loss_percent = ((exit_price - entry_price) / entry_price) * 100

            # 거래 이력에 추가
            trade_record = {
                "symbol": symbol,
                "entry_time": position["entry_time"],
                "exit_time": timestamp,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
                "total_value": quantity * exit_price,
            }

            self.trade_history.append(trade_record)

            # 포지션 제거
            del self.positions[symbol]

            logger.info(
                f"포지션 제거: {symbol} - 수익/손실: {profit_loss:,}원 ({profit_loss_percent:+.2f}%)"
            )

            return trade_record

        except Exception as e:
            logger.error(f"포지션 제거 중 오류: {e}")
            return None

    def get_portfolio_summary(self):
        """
        포트폴리오 요약 정보
        """
        try:
            total_positions = len(self.positions)
            total_value = sum(pos["total_value"] for pos in self.positions.values())

            # 전체 수익/손실 계산
            total_pnl = 0
            total_pnl_percent = 0

            if self.trade_history:
                total_pnl = sum(trade["profit_loss"] for trade in self.trade_history)
                total_invested = sum(
                    trade["entry_price"] * trade["quantity"]
                    for trade in self.trade_history
                )
                if total_invested > 0:
                    total_pnl_percent = (total_pnl / total_invested) * 100

            summary = {
                "total_positions": total_positions,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_percent,
                "total_trades": len(self.trade_history),
                "winning_trades": len(
                    [t for t in self.trade_history if t["profit_loss"] > 0]
                ),
                "losing_trades": len(
                    [t for t in self.trade_history if t["profit_loss"] < 0]
                ),
            }

            return summary

        except Exception as e:
            logger.error(f"포트폴리오 요약 계산 중 오류: {e}")
            return None

    def check_risk_limits(self, symbol, quantity, price):
        """
        리스크 한도 확인
        """
        try:
            # 포지션 크기 한도 확인
            position_value = quantity * price
            if position_value > self.max_position_size:
                logger.warning(
                    f"포지션 크기 한도 초과: {position_value:,}원 > {self.max_position_size:,}원"
                )
                return False, "포지션 크기 한도 초과"

            # 기존 포지션과의 총합 확인
            total_exposure = position_value
            if symbol in self.positions:
                total_exposure += self.positions[symbol]["total_value"]

            if total_exposure > self.max_position_size * 2:
                logger.warning(f"총 노출도 한도 초과: {total_exposure:,}원")
                return False, "총 노출도 한도 초과"

            return True, "OK"

        except Exception as e:
            logger.error(f"리스크 한도 확인 중 오류: {e}")
            return False, str(e)

    def get_position_info(self, symbol):
        """
        특정 포지션 정보 조회
        """
        try:
            if symbol in self.positions:
                return self.positions[symbol]
            else:
                return None

        except Exception as e:
            logger.error(f"포지션 정보 조회 중 오류: {e}")
            return None

    def get_all_positions(self):
        """
        모든 포지션 정보 조회
        """
        try:
            return self.positions.copy()

        except Exception as e:
            logger.error(f"모든 포지션 조회 중 오류: {e}")
            return {}

    def get_trade_history(self, symbol=None, days=None):
        """
        거래 이력 조회
        """
        try:
            if symbol is None and days is None:
                return self.trade_history

            filtered_history = self.trade_history

            # 심볼 필터링
            if symbol:
                filtered_history = [
                    t for t in filtered_history if t["symbol"] == symbol
                ]

            # 기간 필터링
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_history = [
                    t for t in filtered_history if t["exit_time"] >= cutoff_date
                ]

            return filtered_history

        except Exception as e:
            logger.error(f"거래 이력 조회 중 오류: {e}")
            return []
