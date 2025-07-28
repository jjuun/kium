"""
키움 조건 검색 WebSocket 클라이언트
"""

import asyncio
import json
import websockets
import ssl
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from src.core.logger import logger
from src.core.config import Config


class ConditionSearchClient:
    """키움 조건 검색 WebSocket 클라이언트"""
    
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.keep_running = True
        self.access_token = None
        self.registered_conditions = set()  # 등록된 조건식 목록
        self.condition_list = []  # 조건식 목록
        self.on_condition_result = None  # 조건 만족 시 콜백
        self.receive_task = None  # 메시지 수신 태스크
        
        # WebSocket URL 설정
        if Config.KIWOOM_IS_SIMULATION:
            self.socket_url = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"
        else:
            self.socket_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
    
    def set_access_token(self, token: str):
        """액세스 토큰 설정"""
        self.access_token = token
    
    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """조건 만족 시 콜백 함수 설정"""
        self.on_condition_result = callback
    
    async def connect(self) -> bool:
        """WebSocket 서버에 연결"""
        try:
            if not self.access_token:
                logger.error("액세스 토큰이 설정되지 않았습니다.")
                return False
            
            logger.info(f"조건 검색 WebSocket 연결 시도: {self.socket_url}")
            
            # WebSocket 연결 시도 (타임아웃 설정)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.socket_url, ssl=ssl_context),
                timeout=10.0
            )
            self.connected = True
            
            # 로그인 패킷 전송
            login_packet = {
                'trnm': 'LOGIN',
                'token': self.access_token
            }
            await self.send_message(login_packet)
            
            # 로그인 응답 대기 (최대 5초)
            for i in range(50):
                await asyncio.sleep(0.1)
                # 로그인 성공 여부는 receive_messages에서 처리됨
                break
            
            logger.info("조건 검색 WebSocket 연결 성공")
            return True
            
        except asyncio.TimeoutError:
            logger.error("조건 검색 WebSocket 연결 시간 초과")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"조건 검색 WebSocket 연결 실패: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """WebSocket 연결 종료"""
        self.keep_running = False
        
        # 실행 중인 메시지 수신 태스크 취소
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None
        
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("조건 검색 WebSocket 연결 종료")
    
    async def send_message(self, message: Dict[str, Any]):
        """메시지 전송"""
        if not self.connected:
            await self.connect()
        
        if self.connected:
            if not isinstance(message, str):
                message = json.dumps(message)
            await self.websocket.send(message)
            logger.debug(f"조건 검색 메시지 전송: {message}")
    
    async def receive_messages(self):
        """메시지 수신 처리"""
        # 이미 실행 중인 태스크가 있으면 취소
        if self.receive_task and not self.receive_task.done():
            logger.warning("기존 메시지 수신 태스크가 실행 중입니다. 새로운 태스크를 시작합니다.")
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        # 새로운 태스크 시작
        self.receive_task = asyncio.current_task()
        
        while self.keep_running:
            try:
                if not self.connected:
                    await asyncio.sleep(1)
                    continue
                
                response = json.loads(await self.websocket.recv())
                await self.handle_message(response)
                
            except websockets.ConnectionClosed:
                logger.warning("조건 검색 WebSocket 연결이 끊어졌습니다.")
                self.connected = False
                await asyncio.sleep(5)  # 재연결 대기
                await self.connect()
            except asyncio.CancelledError:
                logger.info("조건 검색 메시지 수신 태스크가 취소되었습니다.")
                break
            except Exception as e:
                logger.error(f"조건 검색 메시지 수신 오류: {e}")
                await asyncio.sleep(1)
        
        self.receive_task = None
    
    async def handle_message(self, response: Dict[str, Any]):
        """수신된 메시지 처리"""
        trnm = response.get('trnm')
        
        if trnm == 'LOGIN':
            if response.get('return_code') != 0:
                logger.error(f"조건 검색 로그인 실패: {response.get('return_msg')}")
                await self.disconnect()
            else:
                logger.info("조건 검색 로그인 성공")
        
        elif trnm == 'PING':
            # PING 응답
            await self.send_message(response)
        
        elif trnm == 'CNSRLST':
            # 조건 검색식 목록 응답
            await self.handle_condition_list(response)
        
        elif trnm == 'CNSRREG':
            # 조건 검색식 등록 응답
            await self.handle_condition_register(response)
        
        elif trnm == 'CNSRUNREG':
            # 조건 검색식 해제 응답
            await self.handle_condition_unregister(response)
        
        elif trnm == 'CNSRRESULT':
            # 조건 검색 결과 응답
            await self.handle_condition_result(response)
        
        else:
            logger.debug(f"조건 검색 메시지 수신: {response}")
    
    async def handle_condition_list(self, response: Dict[str, Any]):
        """조건 검색식 목록 처리"""
        try:
            if response.get('return_code') == 0:
                data = response.get('data', [])
                self.condition_list = data
                logger.info(f"조건 검색식 목록 조회 성공: {len(data)}개")
            else:
                logger.error(f"조건 검색식 목록 조회 실패: {response.get('return_msg')}")
        except Exception as e:
            logger.error(f"조건 검색식 목록 처리 오류: {e}")
    
    async def handle_condition_register(self, response: Dict[str, Any]):
        """조건 검색식 등록 처리"""
        try:
            if response.get('return_code') == 0:
                condition_seq = response.get('condition_seq')
                self.registered_conditions.add(condition_seq)
                logger.info(f"조건 검색식 등록 성공: {condition_seq}")
            else:
                logger.error(f"조건 검색식 등록 실패: {response.get('return_msg')}")
        except Exception as e:
            logger.error(f"조건 검색식 등록 처리 오류: {e}")
    
    async def handle_condition_unregister(self, response: Dict[str, Any]):
        """조건 검색식 해제 처리"""
        try:
            if response.get('return_code') == 0:
                condition_seq = response.get('condition_seq')
                self.registered_conditions.discard(condition_seq)
                logger.info(f"조건 검색식 해제 성공: {condition_seq}")
            else:
                logger.error(f"조건 검색식 해제 실패: {response.get('return_msg')}")
        except Exception as e:
            logger.error(f"조건 검색식 해제 처리 오류: {e}")
    
    async def handle_condition_result(self, response: Dict[str, Any]):
        """조건 검색 결과 처리"""
        try:
            if response.get('return_code') == 0:
                result_data = response.get('data', {})
                
                # 결과 데이터 구조화
                structured_result = {
                    'timestamp': datetime.now().isoformat(),
                    'condition_seq': result_data.get('condition_seq'),
                    'condition_name': result_data.get('condition_name', '알 수 없는 조건'),
                    'symbol': result_data.get('symbol'),
                    'symbol_name': result_data.get('symbol_name'),
                    'current_price': result_data.get('current_price'),
                    'price_change': result_data.get('price_change', 0),
                    'volume': result_data.get('volume', 0),
                    'signal_type': result_data.get('signal_type', 'UNKNOWN'),
                    'raw_data': result_data
                }
                
                if self.on_condition_result:
                    await self.on_condition_result(structured_result)
                
                logger.info(f"조건 검색 결과 수신: {structured_result['condition_name']} - {structured_result['symbol_name']} ({structured_result['symbol']}) - {structured_result['signal_type']}")
            else:
                logger.error(f"조건 검색 결과 처리 실패: {response.get('return_msg')}")
        except Exception as e:
            logger.error(f"조건 검색 결과 처리 오류: {e}")
    
    async def get_condition_list(self) -> List[Dict[str, Any]]:
        """조건 검색식 목록 조회"""
        try:
            if not self.connected:
                logger.info("조건 검색 WebSocket 연결 시도...")
                await self.connect()
            
            if self.connected:
                # 기존 조건 목록 초기화
                self.condition_list = []
                
                # 조건 검색식 목록 요청
                request = {
                    'trnm': 'CNSRLST'
                }
                await self.send_message(request)
                
                # 응답 대기 (최대 10초)
                for i in range(100):
                    await asyncio.sleep(0.1)
                    if self.condition_list:
                        logger.info(f"조건 검색식 목록 조회 성공: {len(self.condition_list)}개")
                        return self.condition_list
                
                logger.warning("조건 검색식 목록 응답 대기 시간 초과")
                return []
            else:
                logger.error("조건 검색 WebSocket이 연결되지 않았습니다.")
                return []
                
        except Exception as e:
            logger.error(f"조건 검색식 목록 조회 실패: {e}")
            return []
    
    async def register_condition(self, condition_seq: str) -> bool:
        """조건 검색식 등록"""
        try:
            if not self.connected:
                await self.connect()
            
            if self.connected:
                request = {
                    'trnm': 'CNSRREG',
                    'condition_seq': condition_seq
                }
                await self.send_message(request)
                
                # 응답 대기 (최대 3초)
                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if condition_seq in self.registered_conditions:
                        return True
                
                logger.error(f"조건 검색식 등록 응답 대기 시간 초과: {condition_seq}")
                return False
            else:
                logger.error("조건 검색 WebSocket이 연결되지 않았습니다.")
                return False
                
        except Exception as e:
            logger.error(f"조건 검색식 등록 실패: {e}")
            return False
    
    async def unregister_condition(self, condition_seq: str) -> bool:
        """조건 검색식 해제"""
        try:
            if not self.connected:
                await self.connect()
            
            if self.connected:
                request = {
                    'trnm': 'CNSRUNREG',
                    'condition_seq': condition_seq
                }
                await self.send_message(request)
                
                # 응답 대기 (최대 3초)
                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if condition_seq not in self.registered_conditions:
                        return True
                
                logger.error(f"조건 검색식 해제 응답 대기 시간 초과: {condition_seq}")
                return False
            else:
                logger.error("조건 검색 WebSocket이 연결되지 않았습니다.")
                return False
                
        except Exception as e:
            logger.error(f"조건 검색식 해제 실패: {e}")
            return False
    
    async def run(self):
        """WebSocket 클라이언트 실행"""
        await self.connect()
        await self.receive_messages()
    
    def get_registered_conditions(self) -> List[str]:
        """등록된 조건식 목록 반환"""
        return list(self.registered_conditions)
    
    def is_condition_registered(self, condition_seq: str) -> bool:
        """조건식 등록 여부 확인"""
        return condition_seq in self.registered_conditions 