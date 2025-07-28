"""
주식 데이터 수집기
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
from src.core.logger import logger
from src.core.config import Config


class DataCollector:
    def __init__(self):
        self.symbol = Config.SYMBOL
        self.interval = Config.DATA_INTERVAL
        self.history_days = Config.HISTORY_DAYS

    def get_historical_data(self, symbol=None, period=None):
        """
        과거 주식 데이터 수집
        """
        try:
            symbol = symbol or self.symbol
            period = period or self.history_days

            # 한국 주식의 경우 .KS 추가
            if symbol.isdigit():
                ticker_symbol = f"{symbol}.KS"
            elif symbol.startswith("A") and symbol[1:].isdigit():
                # A로 시작하는 종목코드 (우선주 등)는 A를 제거하고 .KS 추가
                ticker_symbol = f"{symbol[1:]}.KS"
            else:
                ticker_symbol = symbol

            ticker = yf.Ticker(ticker_symbol)

            # 과거 데이터 수집 - 1분봉 대신 일봉 데이터 사용
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period)

            # 1분봉은 8일치 제한이 있으므로 일봉 데이터 사용
            data = ticker.history(
                start=start_date, end=end_date, interval="1d"  # 일봉 데이터 사용
            )

            if data.empty:
                logger.warning(f"데이터를 가져올 수 없습니다: {symbol}")
                return None

            # yfinance는 7개 컬럼: Open, High, Low, Close, Volume, Dividends, Stock Splits
            # 필요한 컬럼만 선택하고 한글명으로 변경
            if len(data.columns) >= 5:
                # 필요한 컬럼만 선택 (Open, High, Low, Close, Volume)
                data = data[["Open", "High", "Low", "Close", "Volume"]]
                data.columns = ["시가", "고가", "저가", "종가", "거래량"]
            else:
                logger.warning(f"예상하지 못한 컬럼 수: {len(data.columns)}")
                return None

            logger.info(f"{symbol} 과거 데이터 수집 완료: {len(data)}개 데이터")
            return data

        except Exception as e:
            logger.error(f"과거 데이터 수집 중 오류: {e}")
            return None

    def get_realtime_price(self, symbol=None):
        """
        실시간 주가 정보 수집
        """
        try:
            symbol = symbol or self.symbol

            if symbol.isdigit():
                ticker_symbol = f"{symbol}.KS"
            elif symbol.startswith("A") and symbol[1:].isdigit():
                # A로 시작하는 종목코드 (우선주 등)는 A를 제거하고 .KS 추가
                ticker_symbol = f"{symbol[1:]}.KS"
            else:
                ticker_symbol = symbol

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            current_price = info.get("regularMarketPrice", 0)
            previous_close = info.get("previousClose", 0)
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0

            realtime_data = {
                "symbol": symbol,
                "current_price": current_price,
                "previous_close": previous_close,
                "change": change,
                "change_percent": change_percent,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"실시간 가격 수집: {symbol} - {current_price:,}원 ({change_percent:+.2f}%)"
            )
            return realtime_data

        except Exception as e:
            logger.error(f"실시간 가격 수집 중 오류: {e}")
            return None

    def get_market_data(self, symbol=None):
        """
        시장 데이터 수집 (거래량, 시가총액 등)
        """
        try:
            symbol = symbol or self.symbol

            if symbol.isdigit():
                ticker_symbol = f"{symbol}.KS"
            elif symbol.startswith("A") and symbol[1:].isdigit():
                # A로 시작하는 종목코드 (우선주 등)는 A를 제거하고 .KS 추가
                ticker_symbol = f"{symbol[1:]}.KS"
            else:
                ticker_symbol = symbol

            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            market_data = {
                "symbol": symbol,
                "market_cap": info.get("marketCap", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
                "pe_ratio": info.get("trailingPE", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "timestamp": datetime.now().isoformat(),
            }

            return market_data

        except Exception as e:
            logger.error(f"시장 데이터 수집 중 오류: {e}")
            return None

    def calculate_technical_indicators(self, data):
        """
        기술적 지표 계산
        """
        try:
            if data is None or data.empty:
                return None

            # 이동평균선
            data["SMA_5"] = data["종가"].rolling(window=Config.SHORT_PERIOD).mean()
            data["SMA_20"] = data["종가"].rolling(window=Config.LONG_PERIOD).mean()

            # RSI (상대강도지수) - 표준 방식으로 개선
            delta = data["종가"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            # 지수이동평균 사용 (표준 RSI 계산 방식)
            avg_gain = gain.ewm(span=14, adjust=False).mean()
            avg_loss = loss.ewm(span=14, adjust=False).mean()
            
            rs = avg_gain / avg_loss
            data["RSI"] = 100 - (100 / (1 + rs))

            # MACD
            exp1 = data["종가"].ewm(span=12, adjust=False).mean()
            exp2 = data["종가"].ewm(span=26, adjust=False).mean()
            data["MACD"] = exp1 - exp2
            data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
            data["MACD_Histogram"] = data["MACD"] - data["MACD_Signal"]

            # 볼린저 밴드
            data["BB_Middle"] = data["종가"].rolling(window=20).mean()
            bb_std = data["종가"].rolling(window=20).std()
            data["BB_Upper"] = data["BB_Middle"] + (bb_std * 2)
            data["BB_Lower"] = data["BB_Middle"] - (bb_std * 2)

            # 거래량 이동평균
            data["Volume_SMA"] = data["거래량"].rolling(window=20).mean()

            logger.info("기술적 지표 계산 완료")
            return data

        except Exception as e:
            logger.error(f"기술적 지표 계산 중 오류: {e}")
            return data
