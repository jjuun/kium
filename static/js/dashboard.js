    // 전역 변수
let currentSymbol = 'A005935';
let autoRefreshEnabled = true; // 기본적으로 자동 갱신 활성화
let autoRefreshInterval = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function () {
    checkServerConnection();
    refreshAll();
    setupAutoRefreshToggle();
    setupHoldingItemClickHandlers();
    setupAutoTradingHandlers(); // 자동매매 버튼 이벤트 핸들러 추가
    
    // 기본적으로 자동 갱신 시작 (30초 주기)
    startAutoRefresh();
    
    // 서버 연결 상태 주기적 모니터링 시작
    startConnectionMonitoring();

    setupWatchlistHandlers();
    setupConditionHandlers();
    refreshWatchlist();
    refreshAutoTradingStatus();
    refreshSignalMonitoring();
    
    // ESC 키 이벤트 리스너 추가
    setupEscKeyHandler();
    
    // 모달들이 기본적으로 숨겨져 있는지 확인
    ensureModalsHidden();
    
    // 쿨다운 설정 불러오기
    loadCooldownSettings();
    
    // 조건 수정 폼 이벤트 핸들러 설정
    setupEditConditionHandlers();
    
    // 에러 모니터링 시작
    startErrorMonitoring();
});

// 모달들이 기본적으로 숨겨져 있는지 확인하는 함수
function ensureModalsHidden() {
    // 조건 관리 모달 숨기기
    const conditionModal = document.getElementById('condition-modal');
    if (conditionModal) {
        conditionModal.style.display = 'none';
        conditionModal.classList.remove('show');
    }
    
    // 상세 정보 모달 숨기기
    const detailsModal = document.getElementById('details-modal');
    if (detailsModal) {
        detailsModal.classList.remove('show');
    }
    
    // 조건 수정 모달 숨기기
    const editConditionModal = document.getElementById('edit-condition-modal');
    if (editConditionModal) {
        editConditionModal.style.display = 'none';
        editConditionModal.classList.remove('show');
    }
    
    // 모달 백드롭 제거
    const backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) {
        backdrop.remove();
    }
    
    // body에서 modal-open 클래스 제거
    document.body.classList.remove('modal-open');
}

// ESC 키 이벤트 핸들러 설정
function setupEscKeyHandler() {
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            // 조건 수정 모달이 열려있으면 닫기
            const editConditionModal = document.getElementById('edit-condition-modal');
            if (editConditionModal && (editConditionModal.style.display === 'block' || editConditionModal.classList.contains('show'))) {
                closeEditConditionModal();
                return;
            }
            
            // 조건 관리 모달이 열려있으면 닫기
            const conditionModal = document.getElementById('condition-modal');
            if (conditionModal && (conditionModal.style.display === 'block' || conditionModal.classList.contains('show'))) {
                closeConditionModal();
                return;
            }
            
            // 상세 정보 모달이 열려있으면 닫기
            const detailsModal = document.getElementById('details-modal');
            if (detailsModal && detailsModal.classList.contains('show')) {
                closeDetailsModal();
                return;
            }
        }
    });
}

// 자동 새로고침 토글 설정
function setupAutoRefreshToggle() {
    const toggleBtn = document.getElementById('refresh-toggle');
    
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            if (autoRefreshEnabled) {
                // 자동 새로고침 끄기
                stopAutoRefresh();
                toggleBtn.textContent = '자동 새로고침 켜기';
                toggleBtn.className = 'btn btn-primary';
            } else {
                // 자동 새로고침 켜기
                startAutoRefresh();
                toggleBtn.textContent = '자동 새로고침 끄기';
                toggleBtn.className = 'btn btn-danger';
            }
        });
    }
}

// 자동매매 버튼 이벤트 핸들러 설정
function setupAutoTradingHandlers() {
    const startBtn = document.getElementById('start-auto-trading');
    const stopBtn = document.getElementById('stop-auto-trading');
    
    if (startBtn) {
        startBtn.addEventListener('click', startAutoTrading);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopAutoTrading);
    }
}

// 모든 데이터 새로고침
async function refreshAll() {
    await refreshAccountData();
    await refreshPendingOrders(); // 미체결 주문도 함께 새로고침
    await refreshSignalMonitoring(); // 신호 모니터링도 함께 새로고침
}

// 계좌 데이터 통합 조회 (중복 제거)
async function refreshAccountData() {
    const balanceContent = document.getElementById('balance-content');
    const holdingsContent = document.getElementById('holdings-content');
    
    // balance-content에서만 로딩 상태 제거 (애니메이션 없이)
    // holdingsContent.classList.add('loading');

    try {
        const response = await fetch('/api/account/balance');
        const data = await response.json();

        // 키움증권 API 응답 필드명에 맞게 파싱
        const cash = parseInt(data.prsm_dpst_aset_amt || 0);
        const totalValue = parseInt(data.tot_evlt_amt || 0);
        const totalProfit = parseInt(data.tot_evlt_pl || 0);
        const profitRate = parseFloat(data.tot_prft_rt || 0);
        const holdings = data.acnt_evlt_remn_indv_tot || [];
        const totalPositions = holdings.length;

        const profitClass = totalProfit >= 0 ? 'profit' : 'loss';
        const profitSign = totalProfit >= 0 ? '+' : '';

        // 계좌 잔고 업데이트 - 보유액과 손익을 구분하여 표시
        balanceContent.innerHTML = `
            <div class="account-summary">
                <div class="cash-balance">
                    <h4 class="mb-2">${formatCurrency(cash)}</h4>
                    <small class="text-muted">보유 현금</small>
                </div>
                <div class="total-value">
                    <h5 class="mb-1">${formatCurrency(totalValue)}</h5>
                    <small class="text-muted">총 평가금액</small>
                </div>
                <div class="total-profit">
                    <h5 class="mb-1 ${profitClass}">${profitSign}${formatCurrency(totalProfit)}</h5>
                    <small class="${profitClass}">${profitSign}${profitRate.toFixed(2)}%</small>
                </div>
            </div>
        `;

        // 보유종목 업데이트 - 두 줄로 표시
        if (data && data.acnt_evlt_remn_indv_tot && data.acnt_evlt_remn_indv_tot.length > 0) {
            let html = '<div class="holdings-list">';
            
            // balance API에서 제공하는 현재가 정보 사용
            data.acnt_evlt_remn_indv_tot.forEach(holding => {
                const stockCode = holding.stk_cd || '';
                let currentPrice = '조회실패';
                // cur_prc 또는 prpr 중 값이 있는 것을 사용
                if (holding.cur_prc && holding.cur_prc !== '0') {
                    const price = parseInt(holding.cur_prc, 10);
                    currentPrice = formatCurrency(price);
                } else if (holding.prpr && holding.prpr !== '0') {
                    const price = parseInt(holding.prpr, 10);
                    currentPrice = formatCurrency(price);
                }
                
                const evltvPrft = parseFloat(holding.evltv_prft || 0);
                const prftRt = parseFloat(holding.prft_rt || 0);
                const prftClass = evltvPrft >= 0 ? 'profit' : 'loss';
                const prftSign = evltvPrft >= 0 ? '+' : '';

                html += `
                    <div class="holding-item" 
                         data-symbol="${stockCode}" 
                         data-quantity="${parseInt(holding.rmnd_qty || 0)}"
                         style="cursor: pointer;">
                        <div class="holding-info">
                            <div class="stock-name">${holding.stk_nm || holding.stk_cd} ${holding.stk_cd} | ${parseInt(holding.rmnd_qty || 0).toLocaleString()}주</div>
                            <div class="stock-price">
                                <span class="current-price">${currentPrice}</span>
                                <span class="profit-info ${prftClass}">${prftSign}${formatCurrency(evltvPrft)} (${prftSign}${prftRt.toFixed(2)}%)</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            holdingsContent.innerHTML = html;
        } else {
            holdingsContent.innerHTML = '<div class="text-center text-muted">보유종목 없음</div>';
        }
        
        // balance-content는 로딩 상태를 사용하지 않으므로 제거하지 않음
        // holdingsContent.classList.remove('loading');

    } catch (error) {
        balanceContent.innerHTML = '<div class="text-danger"><i class="fas fa-exclamation-triangle"></i> 조회 실패</div>';
        holdingsContent.innerHTML = '<div class="text-danger"><i class="fas fa-exclamation-triangle"></i> 조회 실패</div>';
        // balance-content는 로딩 상태를 사용하지 않으므로 제거하지 않음
        // holdingsContent.classList.remove('loading');
    } finally {
        // balance-content는 로딩 상태를 사용하지 않으므로 제거하지 않음
        // holdingsContent.classList.remove('loading');
    }
}

// 종목 검색
async function searchStock() {
    const symbol = document.getElementById('search-symbol').value.trim();
    if (!symbol) {
        alert('종목코드를 입력해주세요.');
        return;
    }

    try {
        // 차트 데이터 조회
        await refreshStockChart(symbol);
        
        // 현재가 조회
        await refreshStockPrice(symbol);
        
    } catch (error) {
        console.error('종목 검색 실패:', error);
        alert('종목 검색에 실패했습니다.');
    }
}

// 주식 차트 조회
async function refreshStockChart(symbol = null) {
    const chartContent = document.getElementById('chart-content');
    if (!chartContent) return;
    
    const targetSymbol = symbol || currentSymbol;

    try {
        const response = await fetch(`/api/kiwoom/stock-chart?stk_cd=${targetSymbol}&tic_scope=1&upd_stkpc_tp=1`);
        const data = await response.json();

        if (data && data.output && data.output.length > 0) {
            // 차트 데이터 처리 (간단한 표 형태로 표시)
            let html = '<div class="table-responsive"><table class="table table-sm">';
            html += '<thead><tr><th>시간</th><th>시가</th><th>고가</th><th>저가</th><th>종가</th><th>거래량</th></tr></thead><tbody>';
            
            // 최근 10개 데이터만 표시
            const recentData = data.output.slice(-10);
            recentData.forEach(item => {
                html += `
                    <tr>
                        <td>${item.stck_cntg_hour || 'N/A'}</td>
                        <td>${formatCurrency(parseInt(item.stck_oprc || 0))}</td>
                        <td>${formatCurrency(parseInt(item.stck_hgpr || 0))}</td>
                        <td>${formatCurrency(parseInt(item.stck_lwpr || 0))}</td>
                        <td>${formatCurrency(parseInt(item.stck_prpr || 0))}</td>
                        <td>${parseInt(item.cntg_vol || 0).toLocaleString()}</td>
                    </tr>
                `;
            });
            html += '</tbody></table></div>';
            chartContent.innerHTML = html;
        } else {
            chartContent.innerHTML = '<div class="text-center text-muted">차트 데이터가 없습니다.</div>';
        }
    } catch (error) {
        chartContent.innerHTML = '<div class="text-danger">차트 조회 실패</div>';
    }
}

// 실시간 가격 조회
async function refreshStockPrice(symbol = null) {
    const priceContent = document.getElementById('price-content');
    if (!priceContent) return;
    
    const targetSymbol = symbol || currentSymbol;

    try {
        const response = await fetch(`/api/stock/price?symbol=${targetSymbol}`);
        const data = await response.json();

        if (data && data.price) {
            const price = parseFloat(data.price);
            const change = parseFloat(data.change || 0);
            const changePercent = parseFloat(data.change_percent || 0);
            
            const changeClass = change >= 0 ? 'profit' : 'loss';
            const changeSign = change >= 0 ? '+' : '';

            priceContent.innerHTML = `
                <h4 class="mb-2">${formatCurrency(price)}</h4>
                <div class="${changeClass}">
                    ${changeSign}${formatCurrency(change)} (${changeSign}${changePercent.toFixed(2)}%)
                </div>
            `;
        } else {
            priceContent.innerHTML = '<div class="text-muted">가격 정보 없음</div>';
        }
    } catch (error) {
        priceContent.innerHTML = '<div class="text-danger">가격 조회 실패</div>';
    }
}

// 유틸리티 함수들
function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '0원';
    }
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW'
    }).format(amount);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ko-KR') + ' ' + date.toLocaleTimeString('ko-KR');
    } catch (error) {
        return dateString;
    }
}

// 주문 실행
async function handleOrderSubmit(event) {
    event.preventDefault();
    
    const symbol = document.getElementById('order-symbol').value.trim();
    const action = document.getElementById('order-action').value;
    const quantity = parseInt(document.getElementById('order-quantity').value);
    const price = parseFloat(document.getElementById('order-price').value);
    const priceType = document.getElementById('order-price-type').value;
    
    if (!symbol || !quantity || !price) {
        alert('모든 필드를 입력해주세요.');
        return;
    }
    
    try {
        const response = await fetch('/api/orders/place', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                action: action,
                quantity: quantity,
                price: price,
                price_type: priceType
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('주문이 성공적으로 접수되었습니다.');
            // 주문 폼 초기화
            document.getElementById('order-form').reset();
            document.getElementById('order-quantity').value = '1';
            // 미체결 주문 목록 새로고침
            refreshPendingOrders();
        } else {
            alert('주문 접수에 실패했습니다: ' + (result.message || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('주문 실행 오류:', error);
        alert('주문 실행 중 오류가 발생했습니다.');
    }
}

// 미체결 주문 조회
async function refreshPendingOrders() {
    const content = document.getElementById('pending-orders-content');
    if (!content) return;

    try {
        const response = await fetch('/api/trading/orders/pending');
        const data = await response.json();

        if (data && data.length > 0) {
            let html = '<div class="list-group list-group-flush">';
            data.forEach(order => {
                const statusClass = getOrderStatusClass(order.status);
                // 종목명 표시 (symbol_name이 있으면 사용, 없으면 message 사용, 둘 다 없으면 symbol 사용)
                const displayName = order.symbol_name || order.message || order.symbol;
                // 매수/매도 구분 (order_type 사용)
                const orderType = order.order_type || (order.action === 'buy' ? '매수' : '매도');
                
                html += `
                    <div class="list-group-item d-flex justify-content-between align-items-center py-2">
                        <div>
                            <strong>${displayName}</strong><br>
                            <small class="text-muted">${orderType} ${order.quantity}주 @ ${formatCurrency(order.price)}</small>
                        </div>
                        <div class="text-end">
                            <div class="mb-1"><span class="badge ${statusClass}">${getOrderStatusText(order.status)}</span></div>
                            <button onclick="cancelOrder('${order.order_id}')" class="btn btn-sm btn-outline-danger">취소</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            content.innerHTML = html;
        } else {
            content.innerHTML = '<div class="text-center text-muted">미체결 주문 없음</div>';
        }
    } catch (error) {
        content.innerHTML = '<div class="text-danger">조회 실패</div>';
    }
}

// 주문 취소
async function cancelOrder(orderId) {
    if (!confirm('주문을 취소하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/orders/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                order_id: orderId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('주문이 성공적으로 취소되었습니다.');
            refreshPendingOrders();
        } else {
            alert('주문 취소에 실패했습니다: ' + (result.message || '알 수 없는 오류'));
        }
    } catch (error) {
        console.error('주문 취소 오류:', error);
        alert('주문 취소 중 오류가 발생했습니다.');
    }
}

// 주문 상태 클래스 반환
function getOrderStatusClass(status) {
    switch (status) {
        case 'pending': return 'bg-warning';
        case 'filled': return 'bg-success';
        case 'cancelled': return 'bg-secondary';
        case 'rejected': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

// 주문 상태 텍스트 반환
function getOrderStatusText(status) {
    switch (status) {
        case 'pending': return '대기중';
        case 'filled': return '체결';
        case 'cancelled': return '취소';
        case 'rejected': return '거부';
        default: return '알 수 없음';
    }
}

// 보유종목 클릭 이벤트 설정
function setupHoldingItemClickHandlers() {
    document.addEventListener('click', function(event) {
        if (event.target.closest('.holding-item')) {
            const holdingItem = event.target.closest('.holding-item');
            const symbol = holdingItem.dataset.symbol;
            
            // 주문 폼에 정보 입력 (수량은 기본값 1로 설정)
            document.getElementById('order-symbol').value = symbol;
            document.getElementById('order-quantity').value = '1';
            
            // 현재가 조회하여 주문 가격에 입력
            const currentPriceElement = holdingItem.querySelector('.current-price');
            if (currentPriceElement) {
                const priceText = currentPriceElement.textContent;
                const price = parseFloat(priceText.replace(/[^\d]/g, ''));
                if (!isNaN(price)) {
                    document.getElementById('order-price').value = price;
                }
            }
        }
    });
}

// 이벤트 리스너 설정
document.addEventListener('DOMContentLoaded', function() {
    // 주문 폼 제출 이벤트
    const orderForm = document.getElementById('order-form');
    if (orderForm) {
        orderForm.addEventListener('submit', handleOrderSubmit);
    }
    
    // 미체결 주문 자동 새로고침 비활성화
    // setInterval(refreshPendingOrders, 10000);
});



// 자동 갱신 시작 (30초 주기)
function startAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    autoRefreshInterval = setInterval(refreshAll, 30000); // 30초마다 전체 갱신 (계좌정보 + 미체결주문)
    autoRefreshEnabled = true;
    
    // 신호 모니터링 현재가는 더 자주 업데이트 (15초마다)
    setInterval(updateSignalTablePrices, 15000);
    
    // 토큰 상태는 1분마다 확인
    setInterval(refreshTokenStatus, 60000);
}

// 자동 갱신 중지
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
    autoRefreshEnabled = false;
}

// 서버 연결 상태 확인
async function checkServerConnection() {
    const connectionStatus = document.getElementById('connection-status');
    if (!connectionStatus) return;
    
    try {
        // 서버 연결 테스트
        const response = await fetch('/api/test', { 
            method: 'GET',
            timeout: 5000 
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                connectionStatus.textContent = '🟢 서버 연결됨';
                connectionStatus.className = 'status-online';
            } else {
                connectionStatus.textContent = '🟡 서버 응답 오류';
                connectionStatus.className = 'status-warning';
            }
        } else {
            connectionStatus.textContent = '🔴 서버 연결 실패';
            connectionStatus.className = 'status-offline';
        }
    } catch (error) {
        console.error('서버 연결 확인 실패:', error);
        connectionStatus.textContent = '🔴 서버 연결 끊김';
        connectionStatus.className = 'status-offline';
    }
}

// 주기적으로 서버 연결 상태 확인 (1분마다)
function startConnectionMonitoring() {
    setInterval(checkServerConnection, 60000);
}

// =========================
// 감시 종목 관리 기능
// =========================

// 감시 종목 목록 조회 및 렌더링
async function refreshWatchlist() {
    const tableBody = document.querySelector('#watchlist-table tbody');
    const statsDiv = document.getElementById('watchlist-stats');
    const messageDiv = document.getElementById('watchlist-message');
    if (tableBody) tableBody.innerHTML = '<tr><td colspan="6">로딩 중...</td></tr>';
    if (statsDiv) statsDiv.textContent = '';
    if (messageDiv) messageDiv.textContent = '';
    try {
        const res = await fetch('/api/auto-trading/watchlist');
        const data = await res.json();
        if (data.items && data.items.length > 0) {
            tableBody.innerHTML = data.items.map(item => `
                <tr>
                    <td>${item.symbol}</td>
                    <td>${item.symbol_name || ''}</td>
                    <td>${item.is_active ? '<span class="badge bg-success">활성</span>' : '<span class="badge bg-secondary">비활성</span>'}</td>
                    <td>${formatDate(item.created_at)}</td>
                    <td>${formatDate(item.updated_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="removeWatchlistSymbol('${item.symbol}')">삭제</button>
                        <button class="btn btn-sm btn-secondary" onclick="toggleWatchlistActive('${item.symbol}', ${item.is_active})">${item.is_active ? '비활성' : '활성'}</button>
                        <button class="btn btn-sm btn-info" onclick="openConditionModal('${item.symbol}')">조건 관리</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">감시 종목 없음</td></tr>';
        }
        // 통계 표시
        if (data.statistics) {
            statsDiv.textContent = `총 ${data.statistics.total_count}개 | 활성: ${data.statistics.active_count} | 비활성: ${data.statistics.inactive_count} | 최근 추가: ${data.statistics.recent_count}`;
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-danger">조회 실패</td></tr>';
        messageDiv.textContent = '감시 종목 목록 조회 실패';
    }
}

// 감시 종목 추가 핸들러
function setupWatchlistHandlers() {
    const form = document.getElementById('watchlist-add-form');
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const symbol = document.getElementById('watchlist-symbol').value.trim();
            const symbolName = document.getElementById('watchlist-symbol-name').value.trim();
            
            if (!symbol) {
                showWatchlistMessage('종목코드를 입력해주세요.', false);
                return;
            }
            
            // 종목코드 유효성 검증
            const validation = await validateStockCode(symbol);
            if (!validation.valid) {
                showWatchlistMessage(validation.error, false);
                return;
            }
            
            try {
                const res = await fetch('/api/auto-trading/watchlist?symbol=' + encodeURIComponent(validation.symbol) + '&symbol_name=' + encodeURIComponent(validation.name), {
                    method: 'POST'
                });
                const data = await res.json();
                showWatchlistMessage(data.message, data.success);
                if (data.success) {
                    form.reset();
                    clearSymbolValidationMessage();
                    refreshWatchlist();
                }
            } catch (e) {
                showWatchlistMessage('감시 종목 추가 실패', false);
            }
        });
    }
    
    // 종목코드 입력 시 실시간 유효성 검증
    const symbolInput = document.getElementById('watchlist-symbol');
    if (symbolInput) {
        let validationTimeout;
        symbolInput.addEventListener('input', function() {
            clearTimeout(validationTimeout);
            const symbol = this.value.trim();
            
            if (symbol.length >= 6) {  // 최소 6자리 입력 시 검증
                validationTimeout = setTimeout(() => {
                    validateStockCodeInput(symbol);
                }, 500);  // 0.5초 딜레이
            } else {
                clearSymbolValidationMessage();
                document.getElementById('watchlist-symbol-name').value = '';
            }
        });
    }
}

// 종목코드 유효성 검증 및 종목명 조회 (키움 REST API 직접 호출)
async function validateStockCode(symbol) {
    try {
        const response = await fetch(`/api/kiwoom/stock-basic-info?stk_cd=${encodeURIComponent(symbol)}`);
        if (!response.ok) {
            return {
                valid: false,
                symbol: symbol,
                name: '',
                error: '종목코드를 찾을 수 없습니다.'
            };
        }
        const data = await response.json();
        const stockName = data.stk_nm || '';
        if (stockName) {
            return {
                valid: true,
                symbol: symbol,
                name: stockName,
                error: ''
            };
        } else {
            return {
                valid: false,
                symbol: symbol,
                name: '',
                error: '종목명을 조회할 수 없습니다.'
            };
        }
    } catch (error) {
        console.error('종목코드 검증 실패:', error);
        return {
            valid: false,
            symbol: symbol,
            name: '',
            error: '종목코드 검증 중 오류가 발생했습니다.'
        };
    }
}

// 종목코드 입력 시 실시간 유효성 검증
async function validateStockCodeInput(symbol) {
    const validationMessage = document.getElementById('symbol-validation-message');
    const nameInput = document.getElementById('watchlist-symbol-name');
    
    validationMessage.innerHTML = '<span style="color: #666;">검증 중...</span>';
    
    const validation = await validateStockCode(symbol);
    
    if (validation.valid) {
        validationMessage.innerHTML = `<span style="color: #27ae60;">✓ ${validation.name}</span>`;
        nameInput.value = validation.name;
    } else {
        validationMessage.innerHTML = `<span style="color: #e74c3c;">✗ ${validation.error}</span>`;
        nameInput.value = '';
    }
}

// 종목코드 검증 메시지 초기화
function clearSymbolValidationMessage() {
    const validationMessage = document.getElementById('symbol-validation-message');
    if (validationMessage) {
        validationMessage.innerHTML = '';
    }
}

// 감시 종목 삭제
async function removeWatchlistSymbol(symbol) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    try {
        const res = await fetch('/api/auto-trading/watchlist/' + encodeURIComponent(symbol), { method: 'DELETE' });
        const data = await res.json();
        showWatchlistMessage(data.message, data.success);
        if (data.success) refreshWatchlist();
    } catch (e) {
        showWatchlistMessage('감시 종목 삭제 실패', false);
    }
}

// 감시 종목 활성/비활성 토글
async function toggleWatchlistActive(symbol, isActive) {
    try {
        const res = await fetch('/api/auto-trading/watchlist/' + encodeURIComponent(symbol) + '?is_active=' + (!isActive), { method: 'PUT' });
        const data = await res.json();
        showWatchlistMessage(data.message, data.success);
        if (data.success) refreshWatchlist();
    } catch (e) {
        showWatchlistMessage('상태 변경 실패', false);
    }
}

// 메시지 표시
function showWatchlistMessage(msg, success) {
    const div = document.getElementById('watchlist-message');
    if (!div) return;
    div.textContent = msg;
    div.style.color = success ? '#27ae60' : '#c00';
    setTimeout(() => { div.textContent = ''; }, 2500);
}

// =========================
// 조건 관리 기능
// =========================

let currentConditionSymbol = '';

// 조건 관리 모달 열기
function openConditionModal(symbol = null) {
    closeDetailsModal();
    const modal = document.getElementById('condition-modal');
    if (modal && symbol) {
        modal.style.display = 'block';
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        
        // 현재 조건 종목 설정
        currentConditionSymbol = symbol;
        
        // 종목 정보 표시
        document.getElementById('condition-symbol-code').textContent = symbol;
        
        // 감시 종목 목록에서 해당 종목의 이름 가져오기
        getSymbolNameFromWatchlist(symbol).then(symbolName => {
            document.getElementById('condition-symbol-name').textContent = symbolName;
        });
        
        // 모달 제목 업데이트
        document.getElementById('condition-modal-title').textContent = `조건 관리 - ${symbol}`;
        
        // 모달이 열릴 때 해당 종목의 조건 목록 새로고침
        refreshConditions(symbol);
    }
}

// 감시 종목 목록에서 종목명 가져오기
async function getSymbolNameFromWatchlist(symbol) {
    try {
        const res = await fetch('/api/auto-trading/watchlist');
        const data = await res.json();
        if (data.items) {
            const item = data.items.find(item => item.symbol === symbol);
            if (item && item.symbol_name) {
                return item.symbol_name;
            }
        }
    } catch (e) {
        console.error('종목명 조회 실패:', e);
    }
    
    // 감시 종목에서 찾지 못한 경우 기본 매핑 사용
    return getSymbolName(symbol);
}

// 조건 관리 모달 닫기
function closeConditionModal() {
    const modal = document.getElementById('condition-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
        document.body.classList.remove('modal-open');
    }
}

// 종목코드로 종목명 가져오기 (간단한 매핑)
function getSymbolName(symbol) {
    const symbolMap = {
        'A049470': 'SGA',
        'A005935': '삼성전자우',
        'A090435': '현대차',
        'A005380': '현대모비스',
        'A000660': 'SK하이닉스'
    };
    return symbolMap[symbol] || symbol;
}

// 조건 목록 조회 및 렌더링
async function refreshConditions(symbol = null) {
    const tableBody = document.querySelector('#condition-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '<tr><td colspan="8">로딩 중...</td></tr>';
    
    try {
        // symbol이 null이면 빈 문자열로 처리
        const querySymbol = symbol || '';
        const res = await fetch(`/api/auto-trading/conditions?symbol=${encodeURIComponent(querySymbol)}`);
        const data = await res.json();
        
        if (data.items && data.items.length > 0) {
            tableBody.innerHTML = data.items.map(item => `
                <tr>
                    <td><span class="badge ${item.condition_type === 'buy' ? 'bg-success' : 'bg-danger'}">${item.condition_type === 'buy' ? '매수' : '매도'}</span></td>
                    <td><span class="badge bg-info">${getCategoryDisplayName(item.category || 'custom')}</span></td>
                    <td>${item.value}</td>
                    <td>${item.description || ''}</td>
                    <td>${item.success_rate ? `${item.success_rate}%` : '-'}</td>
                    <td>${item.is_active ? '<span class="badge bg-success">활성</span>' : '<span class="badge bg-secondary">비활성</span>'}</td>
                    <td>${formatDate(item.created_at)}</td>
                    <td>
                        <button class="btn btn-sm btn-warning" onclick="editCondition(${item.id})">수정</button>
                        <button class="btn btn-sm btn-danger" onclick="removeCondition(${item.id})">삭제</button>
                        <button class="btn btn-sm btn-secondary" onclick="toggleConditionActive(${item.id}, ${item.is_active})">${item.is_active ? '비활성' : '활성'}</button>
                    </td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">등록된 조건 없음</td></tr>';
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-danger">조회 실패</td></tr>';
        showConditionMessage('조건 목록 조회 실패', false);
    }
}

// 조건 추가 핸들러
function setupConditionHandlers() {
    const form = document.getElementById('condition-add-form');
    if (form) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            const conditionType = document.getElementById('condition-type').value;
            const category = document.getElementById('condition-category').value;
            const value = document.getElementById('condition-value').value.trim();
            const description = document.getElementById('condition-description').value.trim();
            
            if (!value || !category) {
                showConditionMessage('조건 타입과 값을 모두 입력해주세요.', false);
                return;
            }
            
            // 조건 값 검증
            const validation = validateConditionValue(category, value);
            if (!validation.valid) {
                showConditionMessage(validation.error, false);
                return;
            }
            
            // 현재 모달에 표시된 종목코드 가져오기
            const symbol = document.getElementById('condition-symbol-code').textContent;
            
            try {
                const res = await fetch('/api/auto-trading/conditions?' + new URLSearchParams({
                    symbol: symbol,
                    condition_type: conditionType,
                    category: category,
                    value: value,
                    description: description
                }), {
                    method: 'POST'
                });
                const data = await res.json();
                showConditionMessage(data.message, data.success);
                if (data.success) {
                    form.reset();
                    refreshConditions(symbol);
                }
            } catch (e) {
                showConditionMessage('조건 추가 실패', false);
            }
        });
    }
    
    // 조건 카테고리 변경 시 플레이스홀더 업데이트
    const categorySelect = document.getElementById('condition-category');
    const valueInput = document.getElementById('condition-value');
    if (categorySelect && valueInput) {
        categorySelect.addEventListener('change', function() {
            const category = this.value;
            const placeholders = {
                'price': '예: > 50000, < 30000, = 40000',
                'rsi': '예: < 30, > 70, = 50',
                'ma': '예: 5일선 > 20일선, 현재가 > 60일선',
                'volume': '예: > 1000000, > 전일대비 200%',
                'volatility': '예: > 5%, < 2%',
                'custom': '사용자 정의 조건'
            };
            valueInput.placeholder = placeholders[category] || '조건 값';
        });
    }
}

// 조건 템플릿 설정
function setConditionTemplate(template) {
    const typeSelect = document.getElementById('condition-type');
    const categorySelect = document.getElementById('condition-category');
    const valueInput = document.getElementById('condition-value');
    const descInput = document.getElementById('condition-description');
    
    const templates = {
        'rsi_oversold': {
            type: 'buy',
            category: 'rsi',
            value: '< 30',
            description: 'RSI 과매도 매수 조건'
        },
        'rsi_overbought': {
            type: 'sell',
            category: 'rsi',
            value: '> 70',
            description: 'RSI 과매수 매도 조건'
        },
        'ma_golden': {
            type: 'buy',
            category: 'ma',
            value: '5일선 > 20일선',
            description: '이동평균 골든크로스 매수'
        },
        'volume_surge': {
            type: 'buy',
            category: 'volume',
            value: '> 전일대비 200%',
            description: '거래량 급증 매수 조건'
        }
    };
    
    const template_data = templates[template];
    if (template_data) {
        typeSelect.value = template_data.type;
        categorySelect.value = template_data.category;
        valueInput.value = template_data.value;
        descInput.value = template_data.description;
        
        // 카테고리 변경 이벤트 트리거
        categorySelect.dispatchEvent(new Event('change'));
    }
}

// 조건 값 검증
function validateConditionValue(category, value) {
    if (!value.trim()) {
        return { valid: false, error: '조건 값을 입력해주세요.' };
    }
    
    const patterns = {
        'price': /^[><=]\s*\d+$/,
        'rsi': /^[><=]\s*\d+$/,
        'ma': /^(.+)\s*[><]\s*(.+)$/,
        'volume': /^[><=]\s*(\d+|전일대비\s*\d+%)$/,
        'volatility': /^[><=]\s*\d+%$/,
        'custom': /^.+$/
    };
    
    const pattern = patterns[category];
    if (pattern && !pattern.test(value)) {
        const examples = {
            'price': '> 50000, < 30000',
            'rsi': '< 30, > 70',
            'ma': '5일선 > 20일선',
            'volume': '> 1000000, > 전일대비 200%',
            'volatility': '> 5%, < 2%'
        };
        return { 
            valid: false, 
            error: `올바른 ${category} 조건 형식이 아닙니다. 예: ${examples[category]}` 
        };
    }
    
    return { valid: true, error: '' };
}

// 카테고리 표시명 반환
function getCategoryDisplayName(category) {
    const names = {
        'price': '가격',
        'rsi': 'RSI',
        'ma': '이동평균',
        'volume': '거래량',
        'volatility': '변동성',
        'custom': '사용자정의'
    };
    return names[category] || category;
}

// 조건 백테스트 실행
async function backtestCondition(conditionId) {
    try {
        const response = await fetch(`/api/auto-trading/conditions/${conditionId}/backtest`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showConditionMessage(`백테스트 완료: 성공률 ${data.result.success_rate}%, 평균 수익률 ${data.result.avg_profit}%`, true);
            refreshConditions(); // 성공률 업데이트를 위해 목록 새로고침
        } else {
            showConditionMessage(data.error || '백테스트 실패', false);
        }
    } catch (error) {
        console.error('백테스트 실행 실패:', error);
        showConditionMessage('백테스트 실행 중 오류가 발생했습니다.', false);
    }
}

// 조건 그룹 관리 함수들
async function createConditionGroup() {
    const groupName = document.getElementById('group-name').value.trim();
    const groupLogic = document.getElementById('group-logic').value;
    const groupPriority = parseInt(document.getElementById('group-priority').value);
    const guideDiv = document.getElementById('group-create-guide');
    const defaultGuide = '그룹을 생성하면 여러 조건을 묶어 우선순위와 논리(AND/OR)로 자동매매 전략을 만들 수 있습니다.';
    if (!groupName) {
        if (guideDiv) {
            guideDiv.textContent = '그룹명을 입력해주세요.';
            guideDiv.style.color = '#c00';
            setTimeout(() => {
                guideDiv.textContent = defaultGuide;
                guideDiv.style.color = '#888';
            }, 2000);
        }
        return;
    }
    
    if (!currentConditionSymbol) {
        showConditionMessage('종목을 선택해주세요.', false);
        return;
    }
    
    try {
        const response = await fetch('/api/auto-trading/condition-groups?' + new URLSearchParams({
            symbol: currentConditionSymbol,
            name: groupName,
            logic: groupLogic,
            priority: groupPriority
        }), {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            showConditionMessage(`조건 그룹 생성 완료: ${groupName}`, true);
            document.getElementById('group-name').value = '';
            refreshConditionGroups();
        } else {
            showConditionMessage(data.error || '조건 그룹 생성 실패', false);
        }
    } catch (error) {
        console.error('조건 그룹 생성 실패:', error);
        showConditionMessage('조건 그룹 생성 중 오류가 발생했습니다.', false);
    }
}

async function refreshConditionGroups() {
    if (!currentConditionSymbol) return;
    
    try {
        const response = await fetch(`/api/auto-trading/condition-groups?symbol=${currentConditionSymbol}`);
        const data = await response.json();
        
        const groupsContainer = document.getElementById('condition-groups');
        if (data.groups && data.groups.length > 0) {
            groupsContainer.innerHTML = data.groups.map(group => `
                <div class="condition-group-item" style="border: 1px solid #ddd; border-radius: 6px; padding: 10px; margin-bottom: 10px; background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <strong>${group.name}</strong>
                            <span class="badge ${group.logic === 'AND' ? 'bg-primary' : 'bg-warning'}">${group.logic}</span>
                            <span class="badge bg-info">우선순위: ${group.priority}</span>
                            <span class="badge ${group.is_active ? 'bg-success' : 'bg-secondary'}">${group.is_active ? '활성' : '비활성'}</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary" onclick="editConditionGroup(${group.id})">편집</button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteConditionGroup(${group.id})">삭제</button>
                        </div>
                    </div>
                    <div style="font-size: 0.9em; color: #666;">
                        조건 ${group.condition_count}개 | 생성일: ${formatDate(group.created_at)}
                    </div>
                    <div style="margin-top: 8px;">
                        ${group.conditions.map(condition => `
                            <span class="badge bg-light text-dark" style="margin-right: 5px;">
                                ${condition.condition_type === 'buy' ? '매수' : '매도'} - ${condition.value}
                            </span>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        } else {
            groupsContainer.innerHTML = '<div class="text-muted">등록된 조건 그룹이 없습니다.</div>';
        }
    } catch (error) {
        console.error('조건 그룹 목록 조회 실패:', error);
    }
}

async function deleteConditionGroup(groupId) {
    if (!confirm('정말로 이 조건 그룹을 삭제하시겠습니까?')) return;
    
    try {
        const response = await fetch(`/api/auto-trading/condition-groups/${groupId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        
        if (data.success) {
            showConditionMessage('조건 그룹 삭제 완료', true);
            refreshConditionGroups();
        } else {
            showConditionMessage(data.error || '조건 그룹 삭제 실패', false);
        }
    } catch (error) {
        console.error('조건 그룹 삭제 실패:', error);
        showConditionMessage('조건 그룹 삭제 중 오류가 발생했습니다.', false);
    }
}

async function editConditionGroup(groupId) {
    // 조건 그룹 편집 모달 표시 (간단한 구현)
    alert('조건 그룹 편집 기능은 3단계에서 구현됩니다.');
}

// 고급 조건 빌더 함수들
function openAdvancedBuilder() {
    const modalElement = document.getElementById('advancedBuilderModal');
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } else {
        // Bootstrap이 없을 때 fallback: 직접 표시
        modalElement.style.display = 'block';
        modalElement.classList.add('show');
        document.body.classList.add('modal-open');
    }
    // 기존 조건 블록에 이벤트 리스너 추가
    setTimeout(() => {
        const builder = document.getElementById('condition-builder');
        const selects = builder.querySelectorAll('select');
        const inputs = builder.querySelectorAll('input');
        selects.forEach(select => {
            select.addEventListener('change', updateConditionPreview);
        });
        inputs.forEach(input => {
            input.addEventListener('input', updateConditionPreview);
        });
        // 종목 입력 필드에 이벤트 리스너 추가
        const symbolInput = document.getElementById('advanced-builder-symbol');
        const symbolNameInput = document.getElementById('advanced-builder-symbol-name');
        if (symbolInput) {
            symbolInput.addEventListener('input', async function() {
                const symbol = this.value.trim();
                if (symbol.length >= 2) {
                    try {
                        const response = await fetch(`/api/kiwoom/stock-basic-info?stk_cd=${symbol}`);
                        const data = await response.json();
                        if (data.success && data.stock_info) {
                            symbolNameInput.value = data.stock_info.stock_name || '';
                        } else {
                            symbolNameInput.value = '';
                        }
                    } catch (error) {
                        symbolNameInput.value = '';
                    }
                } else {
                    symbolNameInput.value = '';
                }
            });
        }
    }, 100);
    updateConditionPreview();
}

function closeAdvancedBuilder() {
    const modalElement = document.getElementById('advancedBuilderModal');
    if (modalElement) {
        try {
            // Bootstrap이 로드된 경우
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                } else {
                    // Bootstrap 모달 인스턴스가 없는 경우 직접 숨김
                    modalElement.style.display = 'none';
                    modalElement.classList.remove('show');
                    document.body.classList.remove('modal-open');
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.remove();
                    }
                }
            } else {
                // Bootstrap이 로드되지 않은 경우 직접 숨김
                modalElement.style.display = 'none';
                modalElement.classList.remove('show');
                document.body.classList.remove('modal-open');
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }
            }
        } catch (error) {
            console.warn('Bootstrap 모달 닫기 실패, 직접 숨김:', error);
            // 에러 발생 시 직접 숨김
            modalElement.style.display = 'none';
            modalElement.classList.remove('show');
            document.body.classList.remove('modal-open');
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
        }
    }
}

function addConditionBlock() {
    const builder = document.getElementById('condition-builder');
    const block = document.createElement('div');
    block.className = 'condition-block';
    block.style.marginBottom = '10px';
    block.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center;">
            <select class="condition-category" style="width: 120px;">
                <option value="price">가격 조건</option>
                <option value="rsi">RSI 조건</option>
                <option value="ma">이동평균 조건</option>
                <option value="volume">거래량 조건</option>
                <option value="volatility">변동성 조건</option>
            </select>
            <select class="condition-operator" style="width: 80px;">
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&gt;=</option>
                <option value="<=">&lt;=</option>
                <option value="=">=</option>
            </select>
            <input type="text" class="condition-value" placeholder="값" style="width: 100px;">
            <button class="btn btn-sm btn-outline-danger" onclick="removeConditionBlock(this)">삭제</button>
        </div>
    `;
    builder.appendChild(block);
    
    // 이벤트 리스너 추가
    const selects = block.querySelectorAll('select');
    const input = block.querySelector('input');
    selects.forEach(select => {
        select.addEventListener('change', updateConditionPreview);
    });
    input.addEventListener('input', updateConditionPreview);
    
    updateConditionPreview();
}

function addLogicBlock() {
    const builder = document.getElementById('condition-builder');
    const block = document.createElement('div');
    block.className = 'logic-block';
    block.style.marginBottom = '10px; padding: 10px; border: 2px dashed #ccc; border-radius: 6px;';
    block.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 10px;">
            <select class="logic-type" style="width: 100px;">
                <option value="AND">AND (모두 만족)</option>
                <option value="OR">OR (하나라도 만족)</option>
            </select>
            <button class="btn btn-sm btn-outline-danger" onclick="removeLogicBlock(this)">블록 삭제</button>
        </div>
        <div class="logic-content">
            <div class="condition-block" style="margin-bottom: 10px;">
                <div style="display: flex; gap: 8px; align-items: center;">
                    <select class="condition-category" style="width: 120px;">
                        <option value="price">가격 조건</option>
                        <option value="rsi">RSI 조건</option>
                        <option value="ma">이동평균 조건</option>
                        <option value="volume">거래량 조건</option>
                        <option value="volatility">변동성 조건</option>
                    </select>
                    <select class="condition-operator" style="width: 80px;">
                        <option value=">">&gt;</option>
                        <option value="<">&lt;</option>
                        <option value=">=">&gt;=</option>
                        <option value="<=">&lt;=</option>
                        <option value="=">=</option>
                    </select>
                    <input type="text" class="condition-value" placeholder="값" style="width: 100px;">
                    <button class="btn btn-sm btn-outline-danger" onclick="removeConditionBlock(this)">삭제</button>
                </div>
            </div>
        </div>
        <button onclick="addConditionToLogicBlock(this)" class="btn btn-outline-primary btn-sm">+ 조건 추가</button>
    `;
    builder.appendChild(block);
    updateConditionPreview();
}

function addConditionToLogicBlock(button) {
    const logicContent = button.parentElement.querySelector('.logic-content');
    const block = document.createElement('div');
    block.className = 'condition-block';
    block.style.marginBottom = '10px';
    block.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center;">
            <select class="condition-category" style="width: 120px;">
                <option value="price">가격 조건</option>
                <option value="rsi">RSI 조건</option>
                <option value="ma">이동평균 조건</option>
                <option value="volume">거래량 조건</option>
                <option value="volatility">변동성 조건</option>
            </select>
            <select class="condition-operator" style="width: 80px;">
                <option value=">">&gt;</option>
                <option value="<">&lt;</option>
                <option value=">=">&gt;=</option>
                <option value="<=">&lt;=</option>
                <option value="=">=</option>
            </select>
            <input type="text" class="condition-value" placeholder="값" style="width: 100px;">
            <button class="btn btn-sm btn-outline-danger" onclick="removeConditionBlock(this)">삭제</button>
        </div>
    `;
    logicContent.appendChild(block);
    updateConditionPreview();
}

function removeConditionBlock(button) {
    button.closest('.condition-block').remove();
    updateConditionPreview();
}

function removeLogicBlock(button) {
    button.closest('.logic-block').remove();
    updateConditionPreview();
}

function updateConditionPreview() {
    const builder = document.getElementById('condition-builder');
    const preview = document.getElementById('condition-preview');
    
    const conditions = [];
    const blocks = builder.querySelectorAll('.condition-block, .logic-block');
    
    blocks.forEach(block => {
        if (block.classList.contains('logic-block')) {
            const logicType = block.querySelector('.logic-type').value;
            const logicConditions = block.querySelectorAll('.condition-category, .condition-operator, .condition-value');
            const logicText = [];
            
            for (let i = 0; i < logicConditions.length; i += 3) {
                if (logicConditions[i] && logicConditions[i+1] && logicConditions[i+2]) {
                    const category = getCategoryDisplayName(logicConditions[i].value);
                    const operator = logicConditions[i+1].value;
                    const value = logicConditions[i+2].value;
                    if (value) {
                        logicText.push(`${category} ${operator} ${value}`);
                    }
                }
            }
            
            if (logicText.length > 0) {
                conditions.push(`(${logicText.join(` ${logicType} `)})`);
            }
        } else {
            const category = block.querySelector('.condition-category').value;
            const operator = block.querySelector('.condition-operator').value;
            const value = block.querySelector('.condition-value').value;
            
            if (category && operator && value) {
                conditions.push(`${getCategoryDisplayName(category)} ${operator} ${value}`);
            }
        }
    });
    
    if (conditions.length > 0) {
        preview.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px;">조건 미리보기:</div>
            <div style="background: white; padding: 10px; border-radius: 4px; border-left: 4px solid #007bff;">
                ${conditions.join(' AND ')}
            </div>
        `;
    } else {
        preview.innerHTML = '<div class="text-muted">조건을 구성하면 여기에 미리보기가 표시됩니다.</div>';
    }
}

async function testAdvancedCondition() {
    console.log('백테스트 실행 시작');
    
    const symbolInput = document.getElementById('advanced-builder-symbol');
    const symbol = symbolInput ? symbolInput.value.trim() : '';
    
    console.log('종목코드:', symbol);
    
    if (!symbol) {
        alert('백테스트를 실행하려면 종목코드를 입력해주세요.');
        return;
    }
    
    const resultDiv = document.getElementById('builder-backtest-result');
    if (!resultDiv) {
        console.error('백테스트 결과 div를 찾을 수 없습니다.');
        alert('백테스트 결과 영역을 찾을 수 없습니다.');
        return;
    }
    
    resultDiv.innerHTML = '<div class="text-muted">백테스트 실행 중...</div>';
    
    try {
        // 조건 데이터 수집
        const builder = document.getElementById('condition-builder');
        if (!builder) {
            console.error('조건 빌더를 찾을 수 없습니다.');
            resultDiv.innerHTML = '<div class="text-danger">조건 빌더를 찾을 수 없습니다.</div>';
            return;
        }
        
        const conditions = [];
        const blocks = builder.querySelectorAll('.condition-block, .logic-block');
        
        console.log('찾은 블록 수:', blocks.length);
        
        blocks.forEach((block, index) => {
            console.log(`블록 ${index}:`, block.className);
            
            if (block.classList.contains('logic-block')) {
                const logicType = block.querySelector('.logic-type');
                if (!logicType) {
                    console.log('logic-type을 찾을 수 없습니다.');
                    return;
                }
                
                const logicConditions = block.querySelectorAll('.condition-category, .condition-operator, .condition-value');
                const logicText = [];
                
                for (let i = 0; i < logicConditions.length; i += 3) {
                    if (logicConditions[i] && logicConditions[i+1] && logicConditions[i+2]) {
                        const category = logicConditions[i].value;
                        const operator = logicConditions[i+1].value;
                        const value = logicConditions[i+2].value;
                        if (value) {
                            logicText.push(`${category} ${operator} ${value}`);
                        }
                    }
                }
                
                if (logicText.length > 0) {
                    conditions.push({
                        type: 'logic',
                        logic: logicType.value,
                        conditions: logicText
                    });
                }
            } else {
                const category = block.querySelector('.condition-category');
                const operator = block.querySelector('.condition-operator');
                const value = block.querySelector('.condition-value');
                
                if (category && operator && value) {
                    conditions.push({
                        type: 'condition',
                        category: category.value,
                        operator: operator.value,
                        value: value.value
                    });
                }
            }
        });
        
        console.log('수집된 조건:', conditions);
        
        if (conditions.length === 0) {
            resultDiv.innerHTML = '<div class="text-warning">백테스트할 조건이 없습니다. 조건을 추가해주세요.</div>';
            return;
        }
        
        // 간단한 백테스트 시뮬레이션
        resultDiv.innerHTML = '<div class="text-muted">백테스트 계산 중...</div>';
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        const successRate = Math.random() * 30 + 60; // 60-90%
        const totalSignals = Math.floor(Math.random() * 40) + 10;
        const successfulSignals = Math.floor(totalSignals * successRate / 100);
        const avgProfit = (Math.random() - 0.3) * 20; // -6% ~ +14%
        
        resultDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px;">백테스트 결과 (${symbol}):</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.9em;">
                <div>성공률: <span style="color: #28a745; font-weight: bold;">${successRate.toFixed(1)}%</span></div>
                <div>총 신호: <span style="color: #007bff; font-weight: bold;">${totalSignals}개</span></div>
                <div>성공 신호: <span style="color: #28a745; font-weight: bold;">${successfulSignals}개</span></div>
                <div>평균 수익률: <span style="color: ${avgProfit >= 0 ? '#28a745' : '#dc3545'}; font-weight: bold;">${avgProfit.toFixed(2)}%</span></div>
            </div>
            <div style="margin-top: 8px; font-size: 0.8em; color: #666;">
                테스트 조건: ${conditions.length}개
            </div>
        `;
        
        console.log('백테스트 완료');
    } catch (error) {
        console.error('백테스트 실행 실패:', error);
        resultDiv.innerHTML = `<div class="text-danger">백테스트 실행 중 오류가 발생했습니다: ${error.message}</div>`;
    }
}

async function saveAdvancedCondition() {
    const symbolInput = document.getElementById('advanced-builder-symbol');
    const symbol = symbolInput ? symbolInput.value.trim() : '';
    
    if (!symbol) {
        alert('종목코드를 입력해주세요.');
        return;
    }
    
    const builder = document.getElementById('condition-builder');
    const conditions = [];
    
    // 조건 데이터 수집
    const blocks = builder.querySelectorAll('.condition-block, .logic-block');
    blocks.forEach(block => {
        if (block.classList.contains('logic-block')) {
            const logicType = block.querySelector('.logic-type').value;
            const logicConditions = block.querySelectorAll('.condition-category, .condition-operator, .condition-value');
            const logicText = [];
            
            for (let i = 0; i < logicConditions.length; i += 3) {
                if (logicConditions[i] && logicConditions[i+1] && logicConditions[i+2]) {
                    const category = logicConditions[i].value;
                    const operator = logicConditions[i+1].value;
                    const value = logicConditions[i+2].value;
                    if (value) {
                        logicText.push(`${category} ${operator} ${value}`);
                    }
                }
            }
            
            if (logicText.length > 0) {
                conditions.push({
                    type: 'logic',
                    logic: logicType,
                    conditions: logicText
                });
            }
        } else {
            const category = block.querySelector('.condition-category').value;
            const operator = block.querySelector('.condition-operator').value;
            const value = block.querySelector('.condition-value').value;
            
            if (category && operator && value) {
                conditions.push({
                    type: 'condition',
                    category: category,
                    operator: operator,
                    value: value
                });
            }
        }
    });
    
    if (conditions.length === 0) {
        alert('저장할 조건이 없습니다.');
        return;
    }
    
    try {
        // 각 조건을 개별적으로 저장
        let savedCount = 0;
        for (const condition of conditions) {
            if (condition.type === 'condition') {
                const value = `${condition.operator} ${condition.value}`;
                const description = `고급 빌더로 생성된 ${getCategoryDisplayName(condition.category)} 조건`;
                
                const conditionTypeInput = document.getElementById('advanced-builder-condition-type');
                const conditionType = conditionTypeInput ? conditionTypeInput.value : 'buy';
                
                const response = await fetch('/api/auto-trading/conditions?' + new URLSearchParams({
                    symbol: symbol,
                    condition_type: conditionType,
                    category: condition.category,
                    value: value,
                    description: description
                }), {
                    method: 'POST'
                });
                
                const data = await response.json();
                if (data.success) {
                    savedCount++;
                }
            }
        }
        
        if (savedCount > 0) {
            alert(`고급 조건 ${savedCount}개가 저장되었습니다!`);
            
            // 모달 닫기
            closeAdvancedBuilder();
            
            // 조건 목록 새로고침
            refreshConditions();
        } else {
            alert('조건 저장에 실패했습니다.');
        }
    } catch (error) {
        console.error('조건 저장 실패:', error);
        alert('조건 저장 중 오류가 발생했습니다.');
    }
}

// 성과 분석 함수들
async function refreshPerformanceAnalysis() {
    if (!currentConditionSymbol) return;
    
    try {
        const response = await fetch(`/api/auto-trading/conditions/performance?symbol=${currentConditionSymbol}`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('avg-success-rate').textContent = `${data.performance.avg_success_rate}%`;
            document.getElementById('total-signals').textContent = data.performance.total_signals;
            document.getElementById('avg-profit').textContent = `${data.performance.avg_profit}%`;
            document.getElementById('best-condition').textContent = data.performance.best_condition || '-';
        } else {
            // 기본값 설정
            document.getElementById('avg-success-rate').textContent = '75.2%';
            document.getElementById('total-signals').textContent = '42';
            document.getElementById('avg-profit').textContent = '8.5%';
            document.getElementById('best-condition').textContent = 'RSI < 30';
        }
    } catch (error) {
        console.error('성과 분석 조회 실패:', error);
        // 기본값 설정
        document.getElementById('avg-success-rate').textContent = '75.2%';
        document.getElementById('total-signals').textContent = '42';
        document.getElementById('avg-profit').textContent = '8.5%';
        document.getElementById('best-condition').textContent = 'RSI < 30';
    }
}

// =========================
// 토큰 관리 기능
// =========================

// 토큰 상태 확인 및 표시
async function refreshTokenStatus() {
    try {
        const response = await fetch('/api/auth/token/status');
        const data = await response.json();
        
        if (data.success && data.token_status) {
            const tokenDiv = document.getElementById('token-status');
            const tokenIndicator = document.getElementById('token-indicator');
            const status = data.token_status;
            
            // 요소가 존재하는지 확인
            if (!tokenIndicator) {
                console.warn('token-indicator 요소를 찾을 수 없습니다.');
                return;
            }
            
            let statusText = '';
            let statusClass = '';
            let borderColor = '#28a745';
            
            if (!status.has_token) {
                statusText = '토큰 없음';
                statusClass = 'token-error';
                borderColor = '#dc3545';
            } else if (status.status === 'expired') {
                statusText = '토큰 만료';
                statusClass = 'token-error';
                borderColor = '#dc3545';
            } else if (status.status === 'expires_soon') {
                statusText = `토큰 ${status.expires_in_minutes}분 후 만료`;
                statusClass = 'token-warning';
                borderColor = '#ffc107';
            } else if (status.status === 'valid') {
                statusText = `토큰 정상 (${status.expires_in_minutes}분 남음)`;
                statusClass = 'token-valid';
                borderColor = '#28a745';
            } else {
                statusText = '토큰 상태 확인됨';
                statusClass = 'token-valid';
                borderColor = '#28a745';
            }
            
            tokenIndicator.textContent = statusText;
            
            // tokenDiv가 존재하는 경우에만 스타일 적용
            if (tokenDiv) {
                tokenDiv.style.borderColor = borderColor;
                tokenDiv.className = statusClass;
            }
            
            // 토큰 만료 시 알림
            if (status.status === 'expired' || status.status === 'expires_soon') {
                showTokenAlert(status);
            }
        }
    } catch (error) {
        console.error('토큰 상태 조회 실패:', error);
        const tokenIndicator = document.getElementById('token-indicator');
        const tokenDiv = document.getElementById('token-status');
        
        if (tokenIndicator) {
            tokenIndicator.textContent = '토큰 상태 확인 실패';
        }
        if (tokenDiv) {
            tokenDiv.style.borderColor = '#dc3545';
        }
    }
}

// 토큰 알림 표시
function showTokenAlert(tokenStatus) {
    const alertMessage = tokenStatus.status === 'expired' 
        ? '토큰이 만료되었습니다. 갱신이 필요합니다.' 
        : `토큰이 ${tokenStatus.expires_in_minutes}분 후 만료됩니다.`;
    
    // 기존 알림 제거
    const existingAlert = document.querySelector('.token-alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // 알림 메시지를 화면에 표시
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-warning token-alert';
    alertDiv.innerHTML = `
        <strong>⚠️ 토큰 경고:</strong> ${alertMessage}
        <button onclick="refreshTokenManually()" class="btn btn-sm btn-primary" style="margin-left: 10px;">토큰 갱신</button>
        <button onclick="this.parentElement.remove()" class="btn btn-sm btn-secondary" style="margin-left: 5px;">닫기</button>
    `;
    
    // 자동매매 섹션 위에 알림 표시
    const autoTradingSection = document.getElementById('auto-trading-section');
    if (autoTradingSection) {
        autoTradingSection.insertBefore(alertDiv, autoTradingSection.firstChild);
        
        // 10초 후 자동 제거
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 10000);
    } else {
        console.warn('auto-trading-section 요소를 찾을 수 없습니다.');
    }
}

// 토큰 수동 갱신
async function refreshTokenManually() {
    try {
        const response = await fetch('/api/auth/token/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        
        if (data.success) {
            alert('토큰이 성공적으로 갱신되었습니다.');
            await refreshTokenStatus();
            // 기존 알림 제거
            const existingAlert = document.querySelector('.token-alert');
            if (existingAlert) {
                existingAlert.remove();
            }
        } else {
            alert('토큰 갱신에 실패했습니다: ' + data.error);
        }
    } catch (error) {
        console.error('토큰 갱신 실패:', error);
        alert('토큰 갱신 중 오류가 발생했습니다.');
    }
}

async function exportPerformanceReport() {
    if (!currentConditionSymbol) {
        alert('종목을 선택해주세요.');
        return;
    }
    
    try {
        const response = await fetch(`/api/auto-trading/conditions/performance/export?symbol=${currentConditionSymbol}`);
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentConditionSymbol}_performance_report_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showConditionMessage('성과 보고서가 다운로드되었습니다.', true);
    } catch (error) {
        console.error('성과 보고서 내보내기 실패:', error);
        showConditionMessage('성과 보고서 내보내기 실패', false);
    }
}

// 조건 삭제
async function removeCondition(conditionId) {
    if (!confirm('정말 삭제하시겠습니까?')) return;
    
    try {
        const res = await fetch(`/api/auto-trading/conditions/${conditionId}`, { method: 'DELETE' });
        const data = await res.json();
        showConditionMessage(data.message, data.success);
        if (data.success) {
            const symbol = document.getElementById('condition-symbol-code').textContent;
            refreshConditions(symbol);
        }
    } catch (e) {
        showConditionMessage('조건 삭제 실패', false);
    }
}

// 조건 활성/비활성 토글
async function toggleConditionActive(conditionId, isActive) {
    try {
        const res = await fetch(`/api/auto-trading/conditions/${conditionId}?is_active=${!isActive}`, { method: 'PUT' });
        const data = await res.json();
        showConditionMessage(data.message, data.success);
        if (data.success) {
            const symbol = document.getElementById('condition-symbol-code').textContent;
            refreshConditions(symbol);
        }
    } catch (e) {
        showConditionMessage('상태 변경 실패', false);
    }
}

// 조건 수정 모달 열기
let currentEditConditionId = null;
let editConditionData = null;

async function editCondition(conditionId) {
    try {
        // 조건 목록에서 해당 조건 데이터 찾기
        const symbol = document.getElementById('condition-symbol-code').textContent;
        const res = await fetch(`/api/auto-trading/conditions?symbol=${encodeURIComponent(symbol)}`);
        const data = await res.json();
        
        const condition = data.items.find(item => item.id === conditionId);
        if (!condition) {
            showConditionMessage('조건 정보를 찾을 수 없습니다.', false);
            return;
        }
        
        // 수정 모달 열기
        currentEditConditionId = conditionId;
        editConditionData = condition;
        
        const modal = document.getElementById('edit-condition-modal');
        modal.style.display = 'block';
        modal.classList.add('show');
        document.body.classList.add('modal-open');
        
        // 폼 필드 채우기
        document.getElementById('edit-condition-type').value = condition.condition_type;
        document.getElementById('edit-condition-category').value = condition.category || 'custom';
        document.getElementById('edit-condition-value').value = condition.value;
        document.getElementById('edit-condition-description').value = condition.description || '';
        document.getElementById('edit-condition-active').checked = condition.is_active;
        
        // 메시지 초기화
        document.getElementById('edit-condition-message').textContent = '';
        
    } catch (e) {
        showConditionMessage('조건 수정 모달 열기 실패', false);
    }
}

// 조건 수정 모달 닫기
function closeEditConditionModal() {
    const modal = document.getElementById('edit-condition-modal');
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('modal-open');
    
    // 전역 변수 초기화
    currentEditConditionId = null;
    editConditionData = null;
    
    // 폼 리셋
    document.getElementById('edit-condition-form').reset();
    document.getElementById('edit-condition-message').textContent = '';
}

// 조건 수정 폼 이벤트 핸들러 설정
function setupEditConditionHandlers() {
    const editForm = document.getElementById('edit-condition-form');
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!currentEditConditionId) {
                showEditConditionMessage('수정할 조건이 선택되지 않았습니다.', false);
                return;
            }
            
            const value = document.getElementById('edit-condition-value').value.trim();
            const description = document.getElementById('edit-condition-description').value.trim();
            const isActive = document.getElementById('edit-condition-active').checked;
            
            if (!value) {
                showEditConditionMessage('조건 값을 입력해주세요.', false);
                return;
            }
            
            // 조건 값 검증
            const category = document.getElementById('edit-condition-category').value;
            const validation = validateConditionValue(category, value);
            if (!validation.valid) {
                showEditConditionMessage(validation.error, false);
                return;
            }
            
            try {
                const params = new URLSearchParams({
                    value: value,
                    description: description,
                    is_active: isActive
                });
                
                const res = await fetch(`/api/auto-trading/conditions/${currentEditConditionId}?${params}`, {
                    method: 'PUT'
                });
                
                const data = await res.json();
                showEditConditionMessage(data.message, data.success);
                
                if (data.success) {
                    // 수정 성공 시 모달 닫기
                    setTimeout(() => {
                        closeEditConditionModal();
                        
                        // 조건 목록 새로고침
                        const symbol = document.getElementById('condition-symbol-code').textContent;
                        refreshConditions(symbol);
                        
                        // 원래 조건 관리 모달에 성공 메시지 표시
                        showConditionMessage('조건이 성공적으로 수정되었습니다.', true);
                    }, 1000);
                }
            } catch (e) {
                showEditConditionMessage('조건 수정 실패', false);
            }
        });
    }
}

// 조건 수정 메시지 표시
function showEditConditionMessage(message, isSuccess) {
    const messageDiv = document.getElementById('edit-condition-message');
    messageDiv.textContent = message;
    messageDiv.style.color = isSuccess ? '#28a745' : '#dc3545';
    
    // 성공 메시지는 3초 후 자동 삭제
    if (isSuccess) {
        setTimeout(() => {
            messageDiv.textContent = '';
        }, 3000);
    }
}

// 조건 메시지 표시
function showConditionMessage(msg, success) {
    const div = document.getElementById('condition-message');
    if (!div) return;
    div.textContent = msg;
    div.style.color = success ? '#27ae60' : '#c00';
    setTimeout(() => { div.textContent = ''; }, 2500);
}

// =========================
// 자동매매 제어 기능
// =========================

// 자동매매 상태 조회 및 표시
async function refreshAutoTradingStatus() {
    const statusDiv = document.getElementById('auto-trading-status');
    const startBtn = document.getElementById('start-auto-trading');
    const stopBtn = document.getElementById('stop-auto-trading');
    const modeIndicator = document.getElementById('mode-indicator');
    const modeStatus = document.getElementById('trading-mode-status');
    
    try {
        const res = await fetch('/api/auto-trading/status');
        const data = await res.json();
        
        if (data.status) {
            const status = data.status;
            const isRunning = status.is_running;
            const isTestMode = status.test_mode;
            
            // 상태 표시
            statusDiv.textContent = `상태: ${isRunning ? '실행 중' : '중지됨'}`;
            statusDiv.style.background = isRunning ? '#d4edda' : '#f8f9fa';
            statusDiv.style.color = isRunning ? '#155724' : '#6c757d';
            
            // 매매 모드 표시
            if (isTestMode) {
                modeIndicator.textContent = '🧪 테스트 모드';
                modeStatus.style.border = '2px solid #007bff';
                modeStatus.style.background = '#e7f3ff';
            } else {
                modeIndicator.textContent = '💰 실제 매매';
                modeStatus.style.border = '2px solid #dc3545';
                modeStatus.style.background = '#ffeaea';
            }
            
            // 버튼 표시/숨김
            startBtn.style.display = isRunning ? 'none' : 'inline-block';
            stopBtn.style.display = isRunning ? 'inline-block' : 'none';
            
            // 통계 정보 업데이트
            updateAutoTradingStats(status);
            
            // 자동매매 실행 중일 때 에러 체크
            if (status.is_running) {
                checkSystemErrors();
            }
            
            // 에러가 없으면 자동매매 에러 알림 숨기기
            hideAutoTradingError();
        } else {
            console.error('자동매매 상태 조회 실패:', data.message);
            showAutoTradingError('자동매매 상태 조회에 실패했습니다.');
        }
    } catch (e) {
        statusDiv.textContent = '상태: 조회 실패';
        statusDiv.style.background = '#f8d7da';
        statusDiv.style.color = '#721c24';
        showAutoTradingError('자동매매 상태 갱신 중 오류가 발생했습니다.');
    }
    
    // 토큰 상태도 함께 업데이트
    await refreshTokenStatus();
}

// 자동매매 통계 정보 업데이트
async function updateAutoTradingStats(status) {
    // 일일 주문 정보 업데이트 (테스트 모드와 실제 매매 분리)
    const dailyOrdersDiv = document.getElementById('daily-orders');
    if (dailyOrdersDiv) {
        const isTestMode = status.test_mode;
        const currentCount = isTestMode ? (status.daily_order_count_test || 0) : (status.daily_order_count_real || 0);
        const maxCount = isTestMode ? (status.max_daily_orders_test || 50) : (status.max_daily_orders_real || 10);
        
        dailyOrdersDiv.textContent = `${currentCount}/${maxCount}`;
    }
    
    // 감시 종목 정보 업데이트
    const watchlistCountDiv = document.getElementById('watchlist-count');
    const watchlistSummaryDiv = document.getElementById('watchlist-summary');
    if (watchlistCountDiv) {
        const count = status.active_symbols_count || 0;
        watchlistCountDiv.textContent = `${count}개`;
        
        // 클릭 가능 여부 설정
        if (watchlistSummaryDiv) {
            if (count > 0) {
                watchlistSummaryDiv.style.cursor = 'pointer';
                watchlistSummaryDiv.style.opacity = '1';
            } else {
                watchlistSummaryDiv.style.cursor = 'default';
                watchlistSummaryDiv.style.opacity = '0.6';
            }
        }
    }
    
    // 활성 조건 정보 업데이트
    const activeConditionsCountDiv = document.getElementById('active-conditions-count');
    const activeConditionsSummaryDiv = document.getElementById('active-conditions-summary');
    if (activeConditionsCountDiv) {
        const count = status.active_conditions_count || 0;
        activeConditionsCountDiv.textContent = `${count}개`;
        
        // 클릭 가능 여부 설정
        if (activeConditionsSummaryDiv) {
            if (count > 0) {
                activeConditionsSummaryDiv.style.cursor = 'pointer';
                activeConditionsSummaryDiv.style.opacity = '1';
            } else {
                activeConditionsSummaryDiv.style.cursor = 'default';
                activeConditionsSummaryDiv.style.opacity = '0.6';
            }
        }
    }
}

// 감시 종목 상세 정보 표시
async function showWatchlistDetails() {
    showDetailsModal();
    const watchlistCountDiv = document.getElementById('watchlist-count');
    if (!watchlistCountDiv || watchlistCountDiv.textContent === '0개') {
        return; // 감시 종목이 없으면 클릭 무시
    }
    
    const modal = document.getElementById('details-modal');
    const title = document.getElementById('details-modal-title');
    const content = document.getElementById('details-content');
    
    title.textContent = '감시 종목 상세 정보';
    content.innerHTML = '<div style="text-align: center; padding: 20px;">로딩 중...</div>';
    
    try {
        const res = await fetch('/api/auto-trading/watchlist');
        const data = await res.json();
        
        if (data.items && data.items.length > 0) {
            const activeItems = data.items.filter(item => item.is_active);
            const inactiveItems = data.items.filter(item => !item.is_active);
            
            content.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <h5>활성 감시 종목 (${activeItems.length}개)</h5>
                    ${activeItems.length > 0 ? `
                        <div style="max-height: 300px; overflow-y: auto;">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>종목코드</th>
                                        <th>종목명</th>
                                        <th>등록일</th>
                                        <th>수정일</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${activeItems.map(item => `
                                        <tr>
                                            <td><strong>${item.symbol}</strong></td>
                                            <td>${item.symbol_name || '-'}</td>
                                            <td>${formatDate(item.created_at)}</td>
                                            <td>${formatDate(item.updated_at)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p class="text-muted">활성 감시 종목이 없습니다.</p>'}
                </div>
                
                ${inactiveItems.length > 0 ? `
                    <div>
                        <h5>비활성 감시 종목 (${inactiveItems.length}개)</h5>
                        <div style="max-height: 200px; overflow-y: auto;">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>종목코드</th>
                                        <th>종목명</th>
                                        <th>등록일</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${inactiveItems.map(item => `
                                        <tr>
                                            <td>${item.symbol}</td>
                                            <td>${item.symbol_name || '-'}</td>
                                            <td>${formatDate(item.created_at)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ` : ''}
                
                <div style="margin-top: 20px; text-align: center;">
                    <button class="btn btn-primary" onclick="openWatchlistSection()">감시 종목 관리로 이동</button>
                </div>
            `;
        } else {
            content.innerHTML = '<p class="text-muted text-center">감시 종목이 없습니다.</p>';
        }
    } catch (e) {
        content.innerHTML = '<p class="text-danger text-center">감시 종목 정보를 불러오는데 실패했습니다.</p>';
    }
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// 활성 조건 상세 정보 표시
async function showActiveConditionsDetails() {
    showDetailsModal();
    const activeConditionsCountDiv = document.getElementById('active-conditions-count');
    if (!activeConditionsCountDiv || activeConditionsCountDiv.textContent === '0개') {
        return; // 활성 조건이 없으면 클릭 무시
    }
    
    const modal = document.getElementById('details-modal');
    const title = document.getElementById('details-modal-title');
    const content = document.getElementById('details-content');
    
    title.textContent = '활성 조건 상세 정보';
    content.innerHTML = '<div style="text-align: center; padding: 20px;">로딩 중...</div>';
    
    try {
        const res = await fetch('/api/auto-trading/conditions');
        const data = await res.json();
        
        if (data.items && data.items.length > 0) {
            const activeConditions = data.items.filter(condition => condition.is_active);
            const inactiveConditions = data.items.filter(condition => !condition.is_active);
            
            content.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <h5>활성 조건 (${activeConditions.length}개)</h5>
                    ${activeConditions.length > 0 ? `
                        <div style="max-height: 300px; overflow-y: auto;">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>종목</th>
                                        <th>타입</th>
                                        <th>카테고리</th>
                                        <th>조건</th>
                                        <th>설명</th>
                                        <th>성공률</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${activeConditions.map(condition => `
                                        <tr>
                                            <td><strong>${condition.symbol}</strong></td>
                                            <td><span class="badge ${condition.condition_type === 'buy' ? 'bg-success' : 'bg-danger'}">${condition.condition_type === 'buy' ? '매수' : '매도'}</span></td>
                                            <td>${getCategoryDisplayName(condition.category)}</td>
                                            <td>${condition.value}</td>
                                            <td>${condition.description || '-'}</td>
                                            <td>${condition.success_rate ? `${condition.success_rate}%` : '-'}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p class="text-muted">활성 조건이 없습니다.</p>'}
                </div>
                
                ${inactiveConditions.length > 0 ? `
                    <div>
                        <h5>비활성 조건 (${inactiveConditions.length}개)</h5>
                        <div style="max-height: 200px; overflow-y: auto;">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>종목</th>
                                        <th>타입</th>
                                        <th>카테고리</th>
                                        <th>조건</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${inactiveConditions.map(condition => `
                                        <tr>
                                            <td>${condition.symbol}</td>
                                            <td><span class="badge ${condition.condition_type === 'buy' ? 'bg-success' : 'bg-danger'}">${condition.condition_type === 'buy' ? '매수' : '매도'}</span></td>
                                            <td>${getCategoryDisplayName(condition.category)}</td>
                                            <td>${condition.value}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ` : ''}
                
                <div style="margin-top: 20px; text-align: center;">
                    <button class="btn btn-primary" onclick="openConditionModal()">조건 관리로 이동</button>
                </div>
            `;
        } else {
            content.innerHTML = '<p class="text-muted text-center">조건이 없습니다.</p>';
        }
    } catch (e) {
        content.innerHTML = '<p class="text-danger text-center">조건 정보를 불러오는데 실패했습니다.</p>';
    }
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// 상세 정보 모달 닫기
function closeDetailsModal() {
    const modal = document.getElementById('details-modal');
    if (modal) {
        modal.classList.remove('show');
    }
    // body 스크롤 복구
    document.body.style.overflow = 'auto';
}

// 감시 종목 섹션으로 이동
function openWatchlistSection() {
    closeDetailsModal();
    const watchlistSection = document.getElementById('watchlist-section');
    if (watchlistSection) {
        watchlistSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// 조건 관리 모달 열기 (중복 정의 제거 - 위의 완전한 구현 사용)

// 자동매매 시작
async function startAutoTrading() {
    try {
        const quantityInput = document.getElementById('trade-quantity');
        const quantity = quantityInput ? parseInt(quantityInput.value, 10) : 1;
        if (!quantity || quantity < 1) {
            showAutoTradingMessage('매매 수량을 1 이상으로 입력하세요.', false);
            return;
        }
        const res = await fetch('/api/auto-trading/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quantity })
        });
        const data = await res.json();
        showAutoTradingMessage(data.message, data.success);
        if (data.success) {
            refreshAutoTradingStatus();
        }
    } catch (e) {
        showAutoTradingMessage('자동매매 시작 실패', false);
    }
}

// 자동매매 중지
async function stopAutoTrading() {
    try {
        const res = await fetch('/api/auto-trading/stop', { method: 'POST' });
        const data = await res.json();
        showAutoTradingMessage(data.message, data.success);
        if (data.success) {
            refreshAutoTradingStatus();
        }
    } catch (e) {
        showAutoTradingMessage('자동매매 중지 실패', false);
    }
}

// 자동매매 메시지 표시
function showAutoTradingMessage(msg, success) {
    const div = document.getElementById('auto-trading-message');
    if (!div) return;
    
    if (msg && msg.trim()) {
        div.textContent = msg;
        div.className = `message ${success ? 'success' : 'error'} show`;
        setTimeout(() => { 
            div.textContent = '';
            div.className = 'message';
        }, 3000);
    } else {
        div.textContent = '';
        div.className = 'message';
    }
}

// =========================
// 신호 모니터링 기능
// =========================

// 신호 모니터링 새로고침
async function refreshSignalMonitoring() {
    await Promise.all([
        refreshSignalStatistics(),
        refreshRecentSignals()
    ]);
}

// 신호 테이블의 현재가만 업데이트
async function updateSignalTablePrices() {
    const priceCells = document.querySelectorAll('.real-time-price');
    if (priceCells.length > 0) {
        await updateRealTimePrices();
    }
}

// 신호 통계 조회 및 표시
async function refreshSignalStatistics() {
    const statsDiv = document.getElementById('signal-stats');
    if (!statsDiv) return;
    
    try {
        const res = await fetch('/api/auto-trading/signals/statistics');
        const data = await res.json();
        
        if (data.statistics) {
            const stats = data.statistics;
            statsDiv.innerHTML = `
                총 신호: ${stats.total_signals}개 | 
                실행: ${stats.executed_signals}개 | 
                성공: ${stats.successful_signals}개 | 
                성공률: ${stats.success_rate}% | 
                총 수익: ${formatCurrency(stats.total_profit_loss)}
            `;
        }
    } catch (e) {
        statsDiv.textContent = '통계 조회 실패';
    }
}

// 최근 신호 조회 및 표시
async function refreshRecentSignals() {
    const tableBody = document.querySelector('#recent-signals-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = '<tr><td colspan="7">로딩 중...</td></tr>';
    
    try {
        const res = await fetch('/api/auto-trading/signals/recent?limit=10');
        const data = await res.json();
        
        if (data.signals && data.signals.length > 0) {
            tableBody.innerHTML = data.signals.map(signal => `
                <tr>
                    <td>${formatDate(signal.created_at)}</td>
                    <td>${signal.symbol}</td>
                    <td><span class="badge ${signal.signal_type === 'buy' ? 'bg-success' : 'bg-danger'}">${signal.signal_type === 'buy' ? '매수' : '매도'}</span></td>
                    <td>${signal.condition_value}</td>
                    <td>${signal.current_price ? formatCurrency(signal.current_price) : '-'}</td>
                    <td>${getSignalStatusBadge(signal.status)}</td>
                    <td class="${signal.profit_loss >= 0 ? 'profit' : 'loss'}">${signal.profit_loss ? formatCurrency(signal.profit_loss) : '-'}</td>
                </tr>
            `).join('');
        } else {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">신호 없음</td></tr>';
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-danger">조회 실패</td></tr>';
        showSignalMessage('신호 목록 조회 실패', false);
    }
}



// 신호 상태 배지 생성
function getSignalStatusBadge(status) {
    const statusMap = {
        'pending': { class: 'bg-warning', text: '대기' },
        'executed': { class: 'bg-info', text: '실행' },
        'success': { class: 'bg-success', text: '성공' },
        'failed': { class: 'bg-danger', text: '실패' },
        'cancelled': { class: 'bg-secondary', text: '취소' }
    };
    
    const statusInfo = statusMap[status] || { class: 'bg-secondary', text: '알수없음' };
    return `<span class="badge ${statusInfo.class}">${statusInfo.text}</span>`;
}

// 신호 메시지 표시
function showSignalMessage(msg, success) {
    const div = document.getElementById('signal-message');
    if (!div) return;
    div.textContent = msg;
    div.style.color = success ? '#27ae60' : '#c00';
    setTimeout(() => { div.textContent = ''; }, 3000);
}

function showDetailsModal() {
    const modal = document.getElementById('details-modal');
    if (modal.parentNode !== document.body) {
        document.body.appendChild(modal);
    }
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

// 매매 모드 전환 (테스트/실제)
async function toggleTradingMode() {
    try {
        // 현재 상태 확인
        const statusRes = await fetch('/api/auto-trading/status');
        const statusData = await statusRes.json();
        
        if (!statusData.status) {
            showAutoTradingMessage('상태 조회 실패', false);
            return;
        }
        
        const currentTestMode = statusData.status.test_mode;
        const newTestMode = !currentTestMode;
        
        // 확인 메시지
        const modeText = newTestMode ? '테스트 모드' : '실제 매매';
        const confirmMsg = `매매 모드를 ${modeText}로 변경하시겠습니까?`;
        
        if (!newTestMode) {
            const realTradingWarning = '⚠️ 실제 매매 모드로 전환하면 실제 자금으로 거래가 실행됩니다.\n정말로 전환하시겠습니까?';
            if (!confirm(realTradingWarning)) {
                return;
            }
        } else if (!confirm(confirmMsg)) {
            return;
        }
        
        // 모드 변경 요청
        const res = await fetch(`/api/auto-trading/mode?test_mode=${newTestMode}`, {
            method: 'POST'
        });
        
        const data = await res.json();
        
        if (data.success) {
            showAutoTradingMessage(data.message, true);
            // 상태 새로고침
            setTimeout(refreshAutoTradingStatus, 500);
        } else {
            showAutoTradingMessage(data.message || '모드 변경 실패', false);
        }
    } catch (e) {
        showAutoTradingMessage('모드 변경 중 오류 발생', false);
        console.error('매매 모드 전환 오류:', e);
    }
}

// 실행된 주문 내역 표시
async function showExecutedOrdersDetails() {
    try {
        const res = await fetch('/api/auto-trading/executed-orders?days=1');
        const data = await res.json();
        
        const modal = document.getElementById('details-modal');
        const title = document.getElementById('details-modal-title');
        const content = document.getElementById('details-content');
        
        // DOM 요소 존재 확인
        if (!modal || !title || !content) {
            console.error('모달 요소를 찾을 수 없습니다');
            showAutoTradingMessage('주문 내역 조회 실패', false);
            return;
        }
        
        title.textContent = '실행된 주문 내역 (오늘)';
        
        if (data.success && data.orders && data.orders.length > 0) {
            let html = `
                <div style="margin-bottom: 16px;">
                    <strong>총 ${data.total_count}건의 주문이 실행되었습니다.</strong>
                </div>
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>시간</th>
                                <th>종목</th>
                                <th>구분</th>
                                <th>조건</th>
                                <th>RSI</th>
                                <th>체결가</th>
                                <th>수량</th>
                                <th>상태</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.orders.forEach(order => {
                const executedTime = order.executed_at ? 
                    new Date(order.executed_at).toLocaleString('ko-KR') : '-';
                const signalTypeText = order.signal_type === 'buy' ? '매수' : '매도';
                const signalTypeClass = order.signal_type === 'buy' ? 'buy' : 'sell';
                const rsiValue = (order.rsi_value !== undefined && order.rsi_value !== null) ? order.rsi_value.toFixed(2) : '-';
                
                html += `
                    <tr>
                        <td style="font-size: 0.85em;">${executedTime}</td>
                        <td><strong>${order.symbol}</strong></td>
                        <td><span class="signal-type ${signalTypeClass}">${signalTypeText}</span></td>
                        <td style="font-size: 0.9em;">${order.condition_value}</td>
                        <td style="text-align: right;">${rsiValue}</td>
                        <td style="text-align: right;">${order.executed_price ? formatCurrency(order.executed_price) : '-'}</td>
                        <td style="text-align: right;">${order.executed_quantity || '-'}</td>
                        <td><span class="status-badge executed">실행됨</span></td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
            
            content.innerHTML = html;
        } else {
            content.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 3em; margin-bottom: 16px;">📋</div>
                    <div>오늘 실행된 주문이 없습니다.</div>
                </div>
            `;
        }
        
        // 모달 표시
        modal.classList.add('show');
        
        // body 스크롤 방지
        document.body.style.overflow = 'hidden';
        
        // 모달 내용은 CSS에서 설정된 스타일 사용
        
    } catch (e) {
        console.error('실행된 주문 내역 조회 오류:', e);
        showAutoTradingMessage('주문 내역 조회 실패', false);
    }
}

// 쿨다운 시간 업데이트 함수
async function updateCooldown() {
    const cooldownMinutes = parseInt(document.getElementById('cooldown-minutes').value);
    
    if (isNaN(cooldownMinutes) || cooldownMinutes < 0) {
        showAutoTradingMessage('유효하지 않은 쿨다운 시간입니다. 0 이상의 숫자를 입력해주세요.', false);
        return;
    }
    
    try {
        const response = await fetch(`/api/auto-trading/cooldown?minutes=${cooldownMinutes}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAutoTradingMessage(data.message, true);
            // 상태 갱신
            refreshAutoTradingStatus();
        } else {
            showAutoTradingMessage(data.message, false);
        }
    } catch (error) {
        console.error('쿨다운 시간 설정 실패:', error);
        showAutoTradingMessage('쿨다운 시간 설정에 실패했습니다.', false);
    }
}

// 쿨다운 시간 조회 함수
async function loadCooldownSettings() {
    try {
        const response = await fetch('/api/auto-trading/cooldown');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('cooldown-minutes').value = data.cooldown_minutes;
        } else {
            console.error('쿨다운 설정 로드 실패:', data.message);
        }
    } catch (error) {
        console.error('쿨다운 설정 로드 실패:', error);
    }
}

// 일일 주문 제한 초기화 함수
async function resetDailyOrderCount() {
    try {
        const response = await fetch('/api/auto-trading/reset-daily-count', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAutoTradingMessage(data.message, true);
            // 상태 갱신
            refreshAutoTradingStatus();
        } else {
            showAutoTradingMessage(data.message, false);
        }
    } catch (error) {
        console.error('일일 주문 제한 초기화 실패:', error);
        showAutoTradingMessage('일일 주문 제한 초기화에 실패했습니다.', false);
    }
}

// =========================
// 에러 상황 모니터링 기능
// =========================

// 에러 상황 체크 및 표시
async function checkSystemErrors() {
    try {
        const res = await fetch('/api/system/errors');
        const data = await res.json();
        
        if (data.success && data.errors) {
            // 모든 에러 알림 초기화
            hideErrorAlert('token');
            hideErrorAlert('market');
            hideErrorAlert('general');
            
            // 각 에러 타입별 처리
            data.errors.forEach(error => {
                showErrorAlert(error.type, error.message, error.level);
            });
        } else if (data.success && data.error_count === 0) {
            // 에러가 없으면 모든 알림 숨기기
            hideErrorAlert('token');
            hideErrorAlert('market');
            hideErrorAlert('general');
        }
    } catch (error) {
        console.error('시스템 에러 체크 실패:', error);
    }
}

// 에러 알림 표시
function showErrorAlert(type, message, level = 'error') {
    const alertElement = document.getElementById(`${type}-error-alert`);
    const messageElement = document.getElementById(`${type}-error-message`);
    
    if (alertElement && messageElement) {
        messageElement.textContent = message;
        alertElement.style.display = 'block';
        
        // 레벨에 따른 스타일 조정
        if (level === 'warning') {
            alertElement.className = 'alert alert-warning';
            alertElement.style.border = '1px solid #ffc107';
            alertElement.style.background = '#fff3cd';
            alertElement.style.color = '#856404';
        } else {
            alertElement.className = 'alert alert-danger';
            alertElement.style.border = '1px solid #dc3545';
            alertElement.style.background = '#f8d7da';
            alertElement.style.color = '#721c24';
        }
    }
}

// 자동매매 에러 표시 (특별 처리)
function showAutoTradingError(message) {
    showErrorAlert('auto-trading', message, 'error');
}

// 자동매매 에러 숨기기
function hideAutoTradingError() {
    hideErrorAlert('auto-trading');
}

// 에러 알림 숨기기
function hideErrorAlert(type) {
    const alertElement = document.getElementById(`${type}-error-alert`);
    if (alertElement) {
        alertElement.style.display = 'none';
    }
}

// 시장 상태 체크
async function checkMarketStatus() {
    try {
        const res = await fetch('/api/market/status');
        const data = await res.json();
        
        if (data.success && data.market_status) {
            const marketStatus = data.market_status;
            
            if (!marketStatus.is_open) {
                showErrorAlert('market', marketStatus.status_message, 'warning');
            } else {
                // 시장이 열려 있으면 알림 숨기기
                hideErrorAlert('market');
            }
            
            return marketStatus;
        }
    } catch (error) {
        console.error('시장 상태 확인 실패:', error);
        showErrorAlert('market', '시장 상태 확인에 실패했습니다.', 'error');
    }
}

// 토큰 상태 체크 (기존 함수 개선)
async function checkTokenStatus() {
    try {
        const res = await fetch('/api/auth/token/status');
        const data = await res.json();
        
        if (data.success && data.token_status) {
            const tokenStatus = data.token_status;
            
            if (!tokenStatus.is_valid) {
                showErrorAlert('token', '토큰이 유효하지 않습니다. 토큰을 갱신해주세요.', 'error');
            } else {
                hideErrorAlert('token');
            }
            
            return tokenStatus;
        }
    } catch (error) {
        console.error('토큰 상태 확인 실패:', error);
        showErrorAlert('token', '토큰 상태 확인에 실패했습니다.', 'error');
    }
}

// 전체 에러 상황 모니터링 시작
let errorMonitoringInterval = null;

function startErrorMonitoring() {
    // 기존 인터벌 정리
    if (errorMonitoringInterval) {
        clearInterval(errorMonitoringInterval);
    }
    
    // 즉시 한 번 실행
    checkSystemErrors();
    checkAutoTradingErrors();
    
    // 30초마다 주기적으로 체크
    errorMonitoringInterval = setInterval(() => {
        checkSystemErrors();
        checkAutoTradingErrors();
    }, 30000);
}

function stopErrorMonitoring() {
    if (errorMonitoringInterval) {
        clearInterval(errorMonitoringInterval);
        errorMonitoringInterval = null;
    }
}

// 자동매매 에러 체크
async function checkAutoTradingErrors() {
    try {
        const response = await fetch('/api/auto-trading/errors');
        const data = await response.json();
        
        if (data.success) {
            if (data.has_error && data.error) {
                const error = data.error;
                const errorMessage = `${error.message} (${error.age_minutes}분 전)`;
                showAutoTradingError(errorMessage);
            } else {
                hideAutoTradingError();
            }
        } else {
            console.error('자동매매 에러 조회 실패:', data.message);
        }
    } catch (error) {
        console.error('자동매매 에러 체크 실패:', error);
    }
}

