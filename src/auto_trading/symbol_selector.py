"""
자동 종목 선정 시스템
3단계 필터링을 통해 최적의 자동매매 대상 종목을 선정합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.core.logger import logger
from src.core.data_collector import DataCollector
from src.auto_trading.watchlist_manager import WatchlistManager


@dataclass
class SymbolCandidate:
    """종목 후보 정보"""
    symbol: str
    symbol_name: str
    market_cap: float
    avg_volume: float
    avg_price: float
    volatility: float
    rsi: float
    score: float
    sector: str
    selection_reason: str


class SymbolSelector:
    """자동 종목 선정 클래스"""

    def __init__(self, db_path: str = "auto_trading.db"):
        self.db_path = db_path
        self.data_collector = DataCollector()
        self.watchlist_manager = WatchlistManager(db_path)
        
        # 선정 기준 설정
        self.max_symbols = 15
        self.min_volume = 100000  # 최소 일평균 거래량 (주) - 50만에서 10만으로 완화
        self.min_market_cap = 100000000000  # 최소 시가총액 (1000억원) - 1조에서 1000억으로 완화
        self.max_volatility = 0.20  # 최대 변동성 (20%) - 15%에서 20%로 완화
        self.min_volatility = 0.01  # 최소 변동성 (1%) - 2%에서 1%로 완화
        
        # KOSPI 200 대표 종목들 (실제 거래 가능한 종목들)
        self.kospi200_symbols = [
            "005930",  # 삼성전자
            "000660",  # SK하이닉스
            "035420",  # NAVER
            "035720",  # 카카오
            "005380",  # 현대차
            "051910",  # LG화학
            "068270",  # 셀트리온
            "373220",  # LG에너지솔루션
            "207940",  # 삼성바이오로직스
            "006400",  # 삼성SDI
            "051900",  # LG생활건강
            "017670",  # SK텔레콤
            "034020",  # 두산에너빌리티
            "028260",  # 삼성물산
            "018260",  # 삼성에스디에스
            "032830",  # 삼성생명
            "086790",  # 하나금융지주
            "105560",  # KB금융
            "055550",  # 신한지주
            "033780",  # KT&G
            "096770",  # SK이노베이션
            "010130",  # 고려아연
            "011200",  # HMM
            "015760",  # 한국전력
            "009150",  # 삼성전기
            "010950",  # S-Oil
            "004170",  # 신세계
            "035250",  # 강원랜드
            "034730",  # SK
            "011070",  # LG이노텍
            "012330",  # 현대모비스
            "009830",  # 한화솔루션
            "003670",  # 포스코퓨처엠
            "006800",  # 미래에셋증권
            "000270",  # 기아
            "024110",  # 기업은행
            "008560",  # 메리츠증권
            "030200",  # KT
            "011780",  # 금호석유
            "009540",  # 현대중공업
            "010140",  # 삼성중공업
            "017960",  # 카카오뱅크
            "086280",  # 현대글로비스
            "009240",  # 한샘
            "004990",  # 롯데지주
            "008930",  # 한미사이언스
            "000810",  # 삼성화재
            "002790",  # 아모레G
            "010620",  # 현대미포조선
            "011170",  # 롯데케미칼
            "004370",  # 농심
            "008770",  # 호텔신라
            "000120",  # CJ대한통운
            "003490",  # 대한항공
            "010060",  # OCI
            "009150",  # 삼성전기
            "011200",  # HMM
            "010130",  # 고려아연
            "096770",  # SK이노베이션
            "033780",  # KT&G
            "028260",  # 삼성물산
            "018260",  # 삼성에스디에스
            "032830",  # 삼성생명
            "086790",  # 하나금융지주
            "105560",  # KB금융
            "055550",  # 신한지주
            "017670",  # SK텔레콤
            "034020",  # 두산에너빌리티
            "051900",  # LG생활건강
            "006400",  # 삼성SDI
            "051910",  # LG화학
            "068270",  # 셀트리온
            "373220",  # LG에너지솔루션
            "207940",  # 삼성바이오로직스
            "035720",  # 카카오
            "005380",  # 현대차
            "035420",  # NAVER
            "000660",  # SK하이닉스
            "005930",  # 삼성전자
        ]
        
        # 종목코드별 실제 종목명 매핑
        self.symbol_names = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "035720": "카카오",
            "005380": "현대차",
            "051910": "LG화학",
            "068270": "셀트리온",
            "373220": "LG에너지솔루션",
            "207940": "삼성바이오로직스",
            "006400": "삼성SDI",
            "051900": "LG생활건강",
            "017670": "SK텔레콤",
            "034020": "두산에너빌리티",
            "028260": "삼성물산",
            "018260": "삼성에스디에스",
            "032830": "삼성생명",
            "086790": "하나금융지주",
            "105560": "KB금융",
            "055550": "신한지주",
            "033780": "KT&G",
            "096770": "SK이노베이션",
            "010130": "고려아연",
            "011200": "HMM",
            "015760": "한국전력",
            "009150": "삼성전기",
            "010950": "S-Oil",
            "004170": "신세계",
            "035250": "강원랜드",
            "034730": "SK",
            "011070": "LG이노텍",
            "012330": "현대모비스",
            "009830": "한화솔루션",
            "003670": "포스코퓨처엠",
            "006800": "미래에셋증권",
            "000270": "기아",
            "024110": "기업은행",
            "008560": "메리츠증권",
            "030200": "KT",
            "011780": "금호석유",
            "009540": "현대중공업",
            "010140": "삼성중공업",
            "017960": "카카오뱅크",
            "086280": "현대글로비스",
            "009240": "한샘",
            "004990": "롯데지주",
            "008930": "한미사이언스",
            "000810": "삼성화재",
            "002790": "아모레G",
            "010620": "현대미포조선",
            "011170": "롯데케미칼",
            "004370": "농심",
            "008770": "호텔신라",
            "000120": "CJ대한통운",
            "003490": "대한항공",
            "010060": "OCI",
        }

    def get_initial_pool(self) -> List[str]:
        """1차 선별: 초기 종목 풀 구성"""
        try:
            logger.info("=== 1차 선별: 초기 종목 풀 구성 ===")
            
            # KOSPI 200 종목 중 중복 제거하여 유니크한 종목 리스트 생성
            unique_symbols = list(set(self.kospi200_symbols))
            logger.info(f"초기 종목 풀: {len(unique_symbols)}개 종목")
            
            return unique_symbols[:50]  # 상위 50개 종목만 선택
            
        except Exception as e:
            logger.error(f"초기 종목 풀 구성 실패: {e}")
            return []

    def collect_market_data(self, symbols: List[str]) -> List[SymbolCandidate]:
        """2차 선별: 시장 데이터 수집 및 기술적 지표 계산"""
        try:
            logger.info("=== 2차 선별: 시장 데이터 수집 ===")
            candidates = []
            
            for i, symbol in enumerate(symbols):
                try:
                    logger.info(f"데이터 수집 중: {symbol} ({i+1}/{len(symbols)})")
                    
                    # 과거 데이터 수집 (30일)
                    df = self.data_collector.get_historical_data(symbol, period=30)
                    if df is None or df.empty:
                        continue
                    
                    # 기술적 지표 계산
                    df_with_indicators = self.data_collector.calculate_technical_indicators(df)
                    if df_with_indicators is None:
                        continue
                    
                    # 기본 통계 계산
                    avg_price = df['종가'].mean()
                    avg_volume = df['거래량'].mean()
                    volatility = df['종가'].pct_change().std()
                    
                    # RSI 계산
                    current_rsi = df_with_indicators['RSI'].iloc[-1] if 'RSI' in df_with_indicators.columns else 50
                    
                    # 시가총액 추정 (실제로는 API에서 가져와야 함)
                    market_cap = avg_price * 1000000  # 임시 추정값
                    
                    # 섹터 분류 (실제로는 더 정확한 분류 필요)
                    sector = self._classify_sector(symbol)
                    
                    candidate = SymbolCandidate(
                        symbol=symbol,
                        symbol_name=self.symbol_names.get(symbol, symbol), # 실제 종목명은 API에서 가져와야 함
                        market_cap=market_cap,
                        avg_volume=avg_volume,
                        avg_price=avg_price,
                        volatility=volatility,
                        rsi=current_rsi,
                        score=0.0,  # 나중에 계산
                        sector=sector,
                        selection_reason=""
                    )
                    
                    candidates.append(candidate)
                    
                except Exception as e:
                    logger.warning(f"종목 {symbol} 데이터 수집 실패: {e}")
                    continue
            
            logger.info(f"2차 선별 완료: {len(candidates)}개 종목")
            return candidates
            
        except Exception as e:
            logger.error(f"시장 데이터 수집 실패: {e}")
            return []

    def _classify_sector(self, symbol: str) -> str:
        """종목코드 기반 섹터 분류"""
        # 실제로는 더 정확한 분류가 필요하지만, 임시로 구현
        sector_map = {
            "005930": "반도체", "000660": "반도체",  # 삼성전자, SK하이닉스
            "035420": "IT", "035720": "IT",  # NAVER, 카카오
            "005380": "자동차", "000270": "자동차",  # 현대차, 기아
            "051910": "화학", "068270": "화학",  # LG화학, 셀트리온
            "373220": "배터리", "006400": "배터리",  # LG에너지솔루션, 삼성SDI
            "207940": "바이오", "008930": "바이오",  # 삼성바이오로직스, 한미사이언스
        }
        return sector_map.get(symbol, "기타")

    def apply_filters(self, candidates: List[SymbolCandidate]) -> List[SymbolCandidate]:
        """3차 선별: 필터링 적용"""
        try:
            logger.info("=== 3차 선별: 필터링 적용 ===")
            
            filtered_candidates = []
            filtered_reasons = {
                "volume": 0,
                "market_cap": 0,
                "volatility": 0,
                "rsi": 0
            }
            
            for candidate in candidates:
                # 거래량 필터
                if candidate.avg_volume < self.min_volume:
                    filtered_reasons["volume"] += 1
                    logger.debug(f"거래량 부족으로 필터링: {candidate.symbol} (거래량: {candidate.avg_volume:,.0f}주)")
                    continue
                
                # 시가총액 필터
                if candidate.market_cap < self.min_market_cap:
                    filtered_reasons["market_cap"] += 1
                    logger.debug(f"시가총액 부족으로 필터링: {candidate.symbol} (시가총액: {candidate.market_cap:,.0f}원)")
                    continue
                
                # 변동성 필터
                if candidate.volatility > self.max_volatility or candidate.volatility < self.min_volatility:
                    filtered_reasons["volatility"] += 1
                    logger.debug(f"변동성 기준 미달로 필터링: {candidate.symbol} (변동성: {candidate.volatility:.3f})")
                    continue
                
                # RSI 필터 (과매수/과매도 제외)
                if candidate.rsi > 80 or candidate.rsi < 20:
                    filtered_reasons["rsi"] += 1
                    logger.debug(f"RSI 기준 미달로 필터링: {candidate.symbol} (RSI: {candidate.rsi:.2f})")
                    continue
                
                filtered_candidates.append(candidate)
            
            logger.info(f"필터링 완료: {len(filtered_candidates)}개 종목")
            logger.info(f"필터링 사유별 통계:")
            logger.info(f"  - 거래량 부족: {filtered_reasons['volume']}개")
            logger.info(f"  - 시가총액 부족: {filtered_reasons['market_cap']}개")
            logger.info(f"  - 변동성 기준 미달: {filtered_reasons['volatility']}개")
            logger.info(f"  - RSI 기준 미달: {filtered_reasons['rsi']}개")
            
            return filtered_candidates
            
        except Exception as e:
            logger.error(f"필터링 실패: {e}")
            return []

    def calculate_scores(self, candidates: List[SymbolCandidate]) -> List[SymbolCandidate]:
        """종목별 점수 계산"""
        try:
            logger.info("=== 종목별 점수 계산 ===")
            
            for candidate in candidates:
                score = 0.0
                reasons = []
                
                # 거래량 점수 (30%)
                volume_score = min(candidate.avg_volume / 1000000, 10) * 0.3
                score += volume_score
                if volume_score > 0.2:
                    reasons.append("높은 거래량")
                
                # 변동성 점수 (25%)
                volatility_score = (0.08 - abs(candidate.volatility - 0.05)) * 10 * 0.25
                score += max(volatility_score, 0)
                if 0.03 <= candidate.volatility <= 0.07:
                    reasons.append("적정 변동성")
                
                # RSI 점수 (20%)
                rsi_score = (50 - abs(candidate.rsi - 50)) / 50 * 0.2
                score += rsi_score
                if 40 <= candidate.rsi <= 60:
                    reasons.append("중립적 RSI")
                
                # 시가총액 점수 (15%)
                market_cap_score = min(candidate.market_cap / 10000000000000, 1) * 0.15
                score += market_cap_score
                if candidate.market_cap > 5000000000000:
                    reasons.append("대형주")
                
                # 섹터 다양성 점수 (10%)
                sector_score = 0.1  # 기본 점수
                score += sector_score
                reasons.append("섹터 다양성")
                
                candidate.score = score
                candidate.selection_reason = ", ".join(reasons)
            
            # 점수순 정렬
            candidates.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"점수 계산 완료: 상위 종목 점수 = {candidates[0].score:.3f}")
            return candidates
            
        except Exception as e:
            logger.error(f"점수 계산 실패: {e}")
            return candidates

    def apply_diversification(self, candidates: List[SymbolCandidate]) -> List[SymbolCandidate]:
        """포트폴리오 다각화 적용"""
        try:
            logger.info("=== 포트폴리오 다각화 적용 ===")
            
            selected = []
            sector_count = {}
            
            for candidate in candidates:
                if len(selected) >= self.max_symbols:
                    break
                
                # 섹터별 최대 3개 종목 제한
                if sector_count.get(candidate.sector, 0) >= 3:
                    continue
                
                selected.append(candidate)
                sector_count[candidate.sector] = sector_count.get(candidate.sector, 0) + 1
            
            logger.info(f"다각화 적용 완료: {len(selected)}개 종목 선정")
            logger.info(f"섹터별 분포: {sector_count}")
            
            return selected
            
        except Exception as e:
            logger.error(f"다각화 적용 실패: {e}")
            return candidates[:self.max_symbols]

    def select_symbols(self) -> List[SymbolCandidate]:
        """전체 종목 선정 프로세스 실행"""
        try:
            logger.info("🚀 자동 종목 선정 프로세스 시작")
            
            # 1차 선별: 초기 풀 구성
            initial_symbols = self.get_initial_pool()
            if not initial_symbols:
                logger.error("초기 종목 풀 구성 실패")
                return []
            
            # 2차 선별: 시장 데이터 수집
            candidates = self.collect_market_data(initial_symbols)
            if not candidates:
                logger.error("시장 데이터 수집 실패")
                return []
            
            # 3차 선별: 필터링 적용
            filtered_candidates = self.apply_filters(candidates)
            if not filtered_candidates:
                logger.error("필터링 후 선정 가능한 종목 없음")
                return []
            
            # 점수 계산
            scored_candidates = self.calculate_scores(filtered_candidates)
            
            # 다각화 적용
            final_candidates = self.apply_diversification(scored_candidates)
            
            logger.info(f"✅ 종목 선정 완료: {len(final_candidates)}개 종목")
            
            # 선정 결과 로깅
            for i, candidate in enumerate(final_candidates, 1):
                logger.info(f"{i:2d}. {candidate.symbol} - 점수: {candidate.score:.3f} - {candidate.selection_reason}")
            
            return final_candidates
            
        except Exception as e:
            logger.error(f"종목 선정 프로세스 실패: {e}")
            return []

    def update_watchlist(self, selected_symbols: List[SymbolCandidate]) -> bool:
        """선정된 종목을 감시 종목에 등록"""
        try:
            logger.info("=== 감시 종목 업데이트 ===")
            
            # 기존 테스트 데이터 정리
            deleted_count = self.watchlist_manager.cleanup_test_data()
            logger.info(f"기존 테스트 데이터 정리: {deleted_count}개 삭제")
            
            # 선정된 종목 등록
            success_count = 0
            for candidate in selected_symbols:
                success = self.watchlist_manager.add_symbol(
                    candidate.symbol, 
                    candidate.symbol_name, 
                    is_test=False
                )
                if success:
                    success_count += 1
            
            logger.info(f"감시 종목 등록 완료: {success_count}/{len(selected_symbols)}개")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"감시 종목 업데이트 실패: {e}")
            return False

    def get_selection_summary(self, selected_symbols: List[SymbolCandidate]) -> Dict[str, Any]:
        """선정 결과 요약"""
        try:
            if not selected_symbols:
                return {"error": "선정된 종목이 없습니다."}
            
            # 섹터별 분포
            sector_distribution = {}
            for candidate in selected_symbols:
                sector_distribution[candidate.sector] = sector_distribution.get(candidate.sector, 0) + 1
            
            # 평균 지표
            avg_volume = np.mean([c.avg_volume for c in selected_symbols])
            avg_volatility = np.mean([c.volatility for c in selected_symbols])
            avg_rsi = np.mean([c.rsi for c in selected_symbols])
            avg_score = np.mean([c.score for c in selected_symbols])
            
            return {
                "total_count": len(selected_symbols),
                "sector_distribution": sector_distribution,
                "avg_volume": avg_volume,
                "avg_volatility": avg_volatility,
                "avg_rsi": avg_rsi,
                "avg_score": avg_score,
                "selection_criteria": {
                    "min_volume": self.min_volume,
                    "min_market_cap": self.min_market_cap,
                    "volatility_range": f"{self.min_volatility:.1%} - {self.max_volatility:.1%}",
                    "rsi_range": "20 - 80"
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"선정 결과 요약 생성 실패: {e}")
            return {"error": str(e)} 