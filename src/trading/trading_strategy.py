"""
매매 전략 클래스
"""

import pandas as pd
import numpy as np
from datetime import datetime
from src.core.logger import logger
from src.core.config import Config


class TradingStrategy:
    def __init__(self):
        self.strategy_name = Config.STRATEGY
        self.short_period = Config.SHORT_PERIOD
        self.long_period = Config.LONG_PERIOD

    def sma_crossover_strategy(self, data):
        """
        이동평균선 교차 전략
        """
        try:
            if data is None or data.empty:
                return None

            # 최소 데이터 포인트 확인
            if len(data) < self.long_period:
                logger.warning("충분한 데이터가 없습니다.")
                return None

            # 현재와 이전 데이터
            current = data.iloc[-1]
            previous = data.iloc[-2]

            # 매수 신호: 단기 이동평균이 장기 이동평균을 상향 돌파
            buy_signal = (
                previous["SMA_5"] <= previous["SMA_20"]
                and current["SMA_5"] > current["SMA_20"]
            )

            # 매도 신호: 단기 이동평균이 장기 이동평균을 하향 돌파
            sell_signal = (
                previous["SMA_5"] >= previous["SMA_20"]
                and current["SMA_5"] < current["SMA_20"]
            )

            # RSI 과매수/과매도 확인
            rsi_overbought = current["RSI"] > 70
            rsi_oversold = current["RSI"] < 30

            # MACD 신호 확인
            macd_bullish = current["MACD"] > current["MACD_Signal"]
            macd_bearish = current["MACD"] < current["MACD_Signal"]

            # 볼린저 밴드 위치 확인
            bb_position = (current["종가"] - current["BB_Lower"]) / (
                current["BB_Upper"] - current["BB_Lower"]
            )

            # 거래량 확인
            volume_surge = current["거래량"] > current["Volume_SMA"] * 1.5

            # 매매 신호 생성
            signal = {
                "timestamp": datetime.now(),
                "price": current["종가"],
                "action": "HOLD",
                "confidence": 0.0,
                "reason": [],
            }

            # 매수 신호
            if buy_signal and rsi_oversold and macd_bullish and bb_position < 0.8:
                signal["action"] = "BUY"
                signal["confidence"] = 0.8
                signal["reason"].append("SMA 상향 돌파")
                if volume_surge:
                    signal["confidence"] += 0.1
                    signal["reason"].append("거래량 급증")

            # 매도 신호
            elif sell_signal and rsi_overbought and macd_bearish and bb_position > 0.2:
                signal["action"] = "SELL"
                signal["confidence"] = 0.8
                signal["reason"].append("SMA 하향 돌파")
                if volume_surge:
                    signal["confidence"] += 0.1
                    signal["reason"].append("거래량 급증")

            # 신호가 있으면 로깅
            if signal["action"] != "HOLD":
                logger.info(
                    f"매매 신호: {signal['action']} - 신뢰도: {signal['confidence']:.2f} - 이유: {', '.join(signal['reason'])}"
                )

            return signal

        except Exception as e:
            logger.error(f"이동평균선 교차 전략 실행 중 오류: {e}")
            return None

    def rsi_strategy(self, data):
        """
        RSI 전략
        """
        try:
            if data is None or data.empty:
                return None

            current = data.iloc[-1]

            signal = {
                "timestamp": datetime.now(),
                "price": current["종가"],
                "action": "HOLD",
                "confidence": 0.0,
                "reason": [],
            }

            # RSI 과매도 (매수 신호)
            if current["RSI"] < 30:
                signal["action"] = "BUY"
                signal["confidence"] = 0.7
                signal["reason"].append("RSI 과매도")

            # RSI 과매수 (매도 신호)
            elif current["RSI"] > 70:
                signal["action"] = "SELL"
                signal["confidence"] = 0.7
                signal["reason"].append("RSI 과매수")

            return signal

        except Exception as e:
            logger.error(f"RSI 전략 실행 중 오류: {e}")
            return None

    def macd_strategy(self, data):
        """
        MACD 전략
        """
        try:
            if data is None or data.empty:
                return None

            current = data.iloc[-1]
            previous = data.iloc[-2]

            signal = {
                "timestamp": datetime.now(),
                "price": current["종가"],
                "action": "HOLD",
                "confidence": 0.0,
                "reason": [],
            }

            # MACD 상향 돌파 (매수 신호)
            if (
                previous["MACD"] <= previous["MACD_Signal"]
                and current["MACD"] > current["MACD_Signal"]
            ):
                signal["action"] = "BUY"
                signal["confidence"] = 0.75
                signal["reason"].append("MACD 상향 돌파")

            # MACD 하향 돌파 (매도 신호)
            elif (
                previous["MACD"] >= previous["MACD_Signal"]
                and current["MACD"] < current["MACD_Signal"]
            ):
                signal["action"] = "SELL"
                signal["confidence"] = 0.75
                signal["reason"].append("MACD 하향 돌파")

            return signal

        except Exception as e:
            logger.error(f"MACD 전략 실행 중 오류: {e}")
            return None

    def bollinger_bands_strategy(self, data):
        """
        볼린저 밴드 전략
        """
        try:
            if data is None or data.empty:
                return None

            current = data.iloc[-1]

            signal = {
                "timestamp": datetime.now(),
                "price": current["종가"],
                "action": "HOLD",
                "confidence": 0.0,
                "reason": [],
            }

            # 하단 밴드 터치 (매수 신호)
            if current["종가"] <= current["BB_Lower"]:
                signal["action"] = "BUY"
                signal["confidence"] = 0.6
                signal["reason"].append("볼린저 밴드 하단 터치")

            # 상단 밴드 터치 (매도 신호)
            elif current["종가"] >= current["BB_Upper"]:
                signal["action"] = "SELL"
                signal["confidence"] = 0.6
                signal["reason"].append("볼린저 밴드 상단 터치")

            return signal

        except Exception as e:
            logger.error(f"볼린저 밴드 전략 실행 중 오류: {e}")
            return None

    def combined_strategy(self, data):
        """
        복합 전략 (여러 지표 조합)
        """
        try:
            if data is None or data.empty:
                return None

            # 각 전략별 신호 수집
            sma_signal = self.sma_crossover_strategy(data)
            rsi_signal = self.rsi_strategy(data)
            macd_signal = self.macd_strategy(data)
            bb_signal = self.bollinger_bands_strategy(data)

            signals = [sma_signal, rsi_signal, macd_signal, bb_signal]
            valid_signals = [s for s in signals if s and s["action"] != "HOLD"]

            if not valid_signals:
                return {
                    "timestamp": datetime.now(),
                    "price": data.iloc[-1]["종가"],
                    "action": "HOLD",
                    "confidence": 0.0,
                    "reason": ["모든 지표 중립"],
                }

            # 신호 통합
            buy_signals = [s for s in valid_signals if s["action"] == "BUY"]
            sell_signals = [s for s in valid_signals if s["action"] == "SELL"]

            # 최종 신호 결정
            if len(buy_signals) > len(sell_signals):
                final_signal = {
                    "timestamp": datetime.now(),
                    "price": data.iloc[-1]["종가"],
                    "action": "BUY",
                    "confidence": sum(s["confidence"] for s in buy_signals)
                    / len(buy_signals),
                    "reason": [reason for s in buy_signals for reason in s["reason"]],
                }
            elif len(sell_signals) > len(buy_signals):
                final_signal = {
                    "timestamp": datetime.now(),
                    "price": data.iloc[-1]["종가"],
                    "action": "SELL",
                    "confidence": sum(s["confidence"] for s in sell_signals)
                    / len(sell_signals),
                    "reason": [reason for s in sell_signals for reason in s["reason"]],
                }
            else:
                final_signal = {
                    "timestamp": datetime.now(),
                    "price": data.iloc[-1]["종가"],
                    "action": "HOLD",
                    "confidence": 0.0,
                    "reason": ["신호 충돌"],
                }

            if final_signal["action"] != "HOLD":
                logger.info(
                    f"복합 전략 신호: {final_signal['action']} - 신뢰도: {final_signal['confidence']:.2f}"
                )

            return final_signal

        except Exception as e:
            logger.error(f"복합 전략 실행 중 오류: {e}")
            return None

    def generate_signal(self, data):
        """
        전략에 따른 매매 신호 생성
        """
        try:
            if self.strategy_name == "SMA_CROSSOVER":
                return self.sma_crossover_strategy(data)
            elif self.strategy_name == "RSI":
                return self.rsi_strategy(data)
            elif self.strategy_name == "MACD":
                return self.macd_strategy(data)
            elif self.strategy_name == "BOLLINGER_BANDS":
                return self.bollinger_bands_strategy(data)
            elif self.strategy_name == "COMBINED":
                return self.combined_strategy(data)
            else:
                logger.warning(f"알 수 없는 전략: {self.strategy_name}")
                return None

        except Exception as e:
            logger.error(f"매매 신호 생성 중 오류: {e}")
            return None
