import os
import json
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import datetime  # 💡 [여기가 누락되어 에러가 났었습니다! 추가 완료]

# ==========================================
# 1. 역사 기록(history.json) 분석 및 최초 기록일 파싱
# ==========================================
tracking_start_date = "26/06/21" # 파일이 없을 때를 대비한 기본값

if os.path.exists("history.json"):
    try:
        with open("history.json", "r", encoding="utf-8") as f:
            history_data = json.load(f)
        
        # history.json의 모든 날짜 키들을 정렬하여 가장 오래된(최초) 날짜를 추출
        sorted_dates = sorted(history_data.keys())
        if sorted_dates:
            first_raw_date = sorted_dates[0]  # 예: "2026-06-21"
            
            # 대시보드 표기용 YY/MM/DD 형태로 변환
            date_parts = first_raw_date.split("-")
            if len(date_parts) == 3:
                tracking_start_date = f"{date_parts[0][2:]}/{date_parts[1]}/{date_parts[2]}"
    except Exception as e:
        print(f"[-] 최초 기록일 파싱 실패 (기본값 사용): {e}")

# ==========================================
# 2. 실시간 데이터 수집 및 연산 (Toss & yfinance)
# ==========================================
# 추적할 티커 리스트 정의
tickers = ["WYFI", "SLNH", "HIVE", "NUAI", "KEEL", "DGXX", "FRMI", "MARA", "CLSK", "BTDR", "BTBT"]

stock_data = {}
print("[*] 실시간 금융 데이터 및 주식수 수집 시작...")

for ticker in tickers:
    try:
        # 야후 파이낸스를 통한 실시간 주가 및 시가총액, 주식수 확보
        stock = yf.Ticker(ticker)
        info = stock.info
        
        current_shares = info.get("sharesOutstanding", 0)
        actual_price = info.get("currentPrice", 0) or info.get("previousClose", 0)
        market_cap = info.get("marketCap", 0)
        
        # 만약 야후 파이낸스에 주식수 누락 시 시총/주가로 역산 방어선 구축
        if current_shares == 0 and actual_price > 0:
            current_shares = int(market_cap / actual_price)
            
        # --------------------------------------------------------
        # 🎯 [핵심] history.json 최초 기록과 비교하여 누적 희석률 연산
        # --------------------------------------------------------
        dilution_rate = 0.0
        if os.path.exists("history.json") and sorted_dates:
            first_date_key = sorted_dates[0]
            # 최초 기록 시점의 해당 종목 주식수 가져오기
            initial_shares = history_data[first_date_key].get(ticker, {}).get("shares", current_shares)
            if initial_shares > 0:
                dilution_rate = ((current_shares - initial_shares) / initial_shares) * 100.0

        # 초기 데이터 베이스라인 할당 (기본 연산용)
        stock_data[ticker] = {
            "current_shares": current_shares,
            "actual_price": actual_price,
            "market_cap": market_cap,
            "dilution": dilution_rate
        }
    except Exception as e:
        print(f"[-] {ticker} 데이터 로드 실패: {e}")

# 데이터 수집 기준일 (오늘 날짜)
today_str = datetime.datetime.now().strftime("%B %d, %Y")

# ==========================================
# 3. HTML 데이터 테이블 행(Row) 동적 빌드
# ==========================================
table_rows = ""
# 기본 베이스라인인 WYFI 주식수 확보 (스크립트 초기 렌더링용)
wyfi_shares = stock_data.get("WYFI", {}).get("current_shares", 38610000)

for ticker, data in stock_data.items():
    # 🎯 [수정 조치] 데이터 행 내부에는 날짜 문자열을 완전히 지우고 '순수 숫자%'만 채웁니다.
    dilution_formatted = f"{data['dilution']:.2f}%"
    
    # WYFI 물량 기준 초기 보정 주가 연산
    adjusted_price = (data['market_cap'] / wyfi_shares) if wyfi_shares > 0 else 0
    ratio = (wyfi_shares / data['current_shares'] * 100) if data['current_shares'] > 0 else 0
    
    table_rows += f"""
    <tr data-shares="{data['current_shares']}" data-marketcap="{data['market_cap']}">
        <td><a href="#" class="ticker-link" data-ticker="{ticker}">${ticker}</a></td>
        <td>{data['current_shares']:,}</td>
        <td class="dilution-cell">{dilution_formatted}</td> <td>${data['actual_price']:.2f}</td>
        <td>${data['market_cap']:,}</td>
        <td class="adj-price">${adjusted_price:.2f}</td>
        <td class="ratio-cell">{ratio:.2f}%</td>
    </tr>
    """

# ==========================================
# 4. 고성능 퀀트 스타일 HTML/JS 웹 프레임 생성
# ==========================================
html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neo-Cloud Share Count Engine</title>
    <style>
        body {{ background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px 20px; }}
        .card {{ max-width: 1200px; margin: 0 auto; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
        h2 {{ color: #ffffff; margin-top: 0; font-size: 1.8rem; border-bottom: 1px solid #21262d; padding-bottom: 12px; }}
        .subtitle {{ color: #8b949e; font-size: 0.95rem; line-height: 1.6; margin-bottom: 24px; }}
        .highlight-text {{ color: #58a6ff; font-weight: bold; }}
        .date-badge {{ display: block; margin-top: 12px; font-size: 0.85rem; color: #6e7681; }}
        .benchmark-badge {{ font-size: 0.8em; font-weight: normal; color: #ff7b72; background: rgba(248,81,112,0.1); padding: 2px 6px; border-radius: 4px; margin-left: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; text-align: right; }}
        th {{ color: #8b949e; font-size: 0.85rem; font-weight: 600; padding: 12px; border-bottom: 2px solid #30363d; cursor: pointer; user-select: none; }}
        th:hover {{ color: #ffffff; background-color: #21262d; }}
        td {{ padding: 12px; border-bottom: 1px solid #21262d; font-size: 0.95rem; font-family: "SFMono-Regular", Consolas, monospace; }}
        tr:hover {{ background-color: #1f242c; }}
        th:first-child, td:first-child {{ text-align: left; font-weight: bold; }}
        .ticker-link {{ color: #58a6ff; text-decoration: none; }}
        .ticker-link:hover {{ text-decoration: underline; }}
        .adj-price {{ color: #3fb950; font-weight: bold; }}
        .ratio-cell {{ color: #d29922; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>Neo-Cloud Share Count: Revenue Growth vs. Price Responsiveness</h2>
        
        <p class="subtitle">
            While a company’s robust revenue expansion serves as a fundamental catalyst, the efficiency with which this growth translates into share price appreciation is strictly dictated by its <strong>outstanding share structure</strong>. 
            An overdiluted share supply acts as a structural drag, severely dampening how dynamically the stock responds to massive top-line growth. This platform quantifies that exact sensitivity, analyzing the physical constraints of float scale on price momentum.<br><br>
            
            <strong>"How would the stock price respond to the same revenue growth under a highly optimized, scarce supply model?"</strong><br>
            By normalizing the float structure of all peer assets against the selected benchmark below, we remove the weight of excessive share supply. This instantly unmasks the <strong>'Adjusted Price'</strong> — revealing the explosive valuation these companies would naturally achieve under a lean equity landscape.<br>
            
            <span class="date-badge">* Data synthesized as of market close on {today_str} • Click any Ticker to shift the Baseline Benchmark • Click Headers to sort</span>
        </p>
        
        <table id="stockTable">
            <thead>
                <tr>
                    <th>TICKER ↕</th>
                    <th>CURRENT SHARES ↕</th>
                    <th>DILUTION ▼ <span class="benchmark-badge">Since {tracking_start_date}</span></th>
                    <th>ACTUAL PRICE ($) ↕</th>
                    <th>MARKET CAP ($) ↕</th>
                    <th id="adjustedPriceHeader">ADJUSTED PRICE ($) ↕</th>
                    <th>WYFI / TICKER (%) ↕</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <script>
        // 💡 실시간 상호작용 및 기준 종목(Baseline) 전환 엔진 JS
        let currentBaseTicker = "WYFI";
        let currentBaseShares = {wyfi_shares};

        document.querySelectorAll('.ticker-link').forEach(link => {{
            link.addEventListener('click', function(e) {{
                e.preventDefault();
                const clickedTicker = this.getAttribute('data-ticker');
                const clickedRow = this.closest('tr');
                const clickedShares = parseFloat(clickedRow.getAttribute('data-shares'));
                
                currentBaseTicker = clickedTicker;
                currentBaseShares = clickedShares;
                
                // 테이블 헤더 및 수식 재정렬 연산
                document.getElementById('adjustedPriceHeader').innerText = `ADJUSTED PRICE BY ${{currentBaseTicker}} ($) ↕`;
                
                document.querySelectorAll('#stockTable tbody tr').forEach(row => {{
                    const targetMarketCap = parseFloat(row.getAttribute('data-marketcap'));
                    const targetShares = parseFloat(row.getAttribute('data-shares'));
                    
                    // 보정 주가 및 비율 동적 재계산
                    const newAdjPrice = targetMarketCap / currentBaseShares;
                    const newRatio = (currentBaseShares / targetShares) * 100;
                    
                    row.querySelector('.adj-price').innerText = `$${{newAdjPrice.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;
                    row.querySelector('.ratio-cell').innerText = `${{newRatio.toFixed(2)}}%`;
                }});
            }});
        }});

        // 테이블 정렬(Sort) 스크립트 엔진
        const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;
        const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
            v1 !== '' && v2 !== '' && !isNaN(v1.replace(/[^0-9.-]/g, '')) && !isNaN(v2.replace(/[^0-9.-]/g, '')) ? 
            parseFloat(v1.replace(/[^0-9.-]/g, '')) - parseFloat(v2.replace(/[^0-9.-]/g, '')) : 
            v1.toString().localeCompare(v2)
            )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));

        document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {{
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            Array.from(tbody.querySelectorAll('tr'))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
                .forEach(tr => tbody.appendChild(tr) );
        }})));
    </script>
</body>
</html>
"""

# ==========================================
# 5. 최종 결과물 index.html 저장
# ==========================================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("[+] 데이터 정규화 완료 및 index.html 빌드 성공!")
