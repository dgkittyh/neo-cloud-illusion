from datetime import datetime, timedelta
import yfinance as yf
import json
import os
import requests
from bs4 import BeautifulSoup
import re

# 1. 장 마감 날짜 계산 함수
def get_last_market_close():
    today = datetime.now()
    weekday = today.weekday()
    if today.hour < 11:
        today = today - timedelta(days=1)
        weekday = today.weekday()
    if weekday == 5: target_date = today - timedelta(days=1)
    elif weekday == 6: target_date = today - timedelta(days=2)
    else: target_date = today
    return target_date.strftime("%B %d, %Y")

current_date = get_last_market_close()
today_str = datetime.now().strftime("%Y-%m-%d")

# 2. 포트폴리오 티커 리스트
tickers = [
    "NBIS", "CRWV", "IREN", "WULF", "HUT", "APLD", "CIFR", "CORZ", "FRMI", "MARA",
    "CLSK", "BTDR", "KEEL", "WYFI", "HIVE", "NUAI", "DGXX", "SLNH", "GLXY", "RIOT"
]

# 💡 [토스증권 웹 핀포인트 수집 엔진]
def fetch_shares_from_toss_web(ticker_symbol):
    try:
        url = f"https://www.tossinvest.com/stocks/{ticker_symbol}/analytics"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text_data = soup.get_text()
            
            match = re.search(r'(?:발행주식수|상장주식수|주식수)\s*([\d,]+)', text_data)
            if match:
                return int(match.group(1).replace(',', ''))
            
            script_match = re.search(r'"sharesOutstanding"\s*:\s*(\d+)', res.text)
            if script_match:
                return int(script_match.group(1))
    except Exception as e:
        print(f"   ⚠️ 토스 웹 피드 파싱 지연 ({ticker_symbol}): {e}")
    return 0

# 3. 히스토리 로드 및 갱신 (비어있는 0바이트 파일 에러 완벽 방어)
current_dir = os.path.dirname(os.path.abspath(__file__))
history_file = os.path.join(current_dir, "history.json")

history_data = {}
if os.path.exists(history_file):
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            # 파일이 존재하고 내용이 있을 때만 로드
            content = f.read().strip()
            if content:
                history_data = json.loads(content)
    except Exception as e:
        print(f"⚠️ 기존 history.json 읽기 실패 (초기화 진행): {e}")
        history_data = {}

stock_data = []
all_base_dates = []
print("🚀 [하이브리드 엔진] 토스증권(주식수) & 야후파이낸스(주가) 데이터 파이프라인 가동...")

for ticker_symbol in tickers:
    try:
        # 주가는 야후 파이낸스 실시간 시세 연동
        ticker_yf = yf.Ticker(ticker_symbol)
        info = ticker_yf.info
        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose') or 0.0
        
        # 주식수는 토스증권 웹 분석 페이지에서 정밀 서치
        shares = fetch_shares_from_toss_web(ticker_symbol)
        
        # 토스 비동기 차단 대비 최후방 안전망 백업
        if shares == 0:
            shares = info.get('sharesOutstanding') or 0
            if ticker_symbol == "GLXY": shares = 389900100
            elif ticker_symbol == "NBIS": shares = 251137524
            
        marketcap = int(shares * price)
        
        if shares > 0 and price > 0:
            if ticker_symbol not in history_data or not history_data[ticker_symbol]:
                history_data[ticker_symbol] = {today_str: int(shares)}
                initial_shares = shares
                first_date = today_str
            else:
                first_date = sorted(history_data[ticker_symbol].keys())[0]
                initial_shares = history_data[ticker_symbol][first_date]
                
                last_recorded_date = sorted(history_data[ticker_symbol].keys())[-1]
                if int(shares) != history_data[ticker_symbol][last_recorded_date]:
                    history_data[ticker_symbol][today_str] = int(shares)
            
            all_base_dates.append(first_date)
            dilution_rate = ((shares - initial_shares) / initial_shares) * 100
            
            stock_data.append({
                "ticker": ticker_symbol,
                "shares": int(shares),
                "price": float(price),
                "marketcap": int(marketcap),
                "dilution": dilution_rate
            })
            print(f" ➔ 📡 하이브리드 연동 완료: {ticker_symbol} -> {shares:,} 주")
            
    except Exception as e:
        print(f"❌ {ticker_symbol} 연동 실패 스킵: {e}")

# 4. 히스토리 파일 세이브
with open(history_file, "w", encoding="utf-8") as f:
    json.dump(history_data, f, indent=4, ensure_ascii=False)

if all_base_dates:
    earliest_date_str = sorted(all_base_dates)[0]
    try:
        dt = datetime.strptime(earliest_date_str, "%Y-%m-%d")
        formatted_base_date = dt.strftime("%B %d, %Y")
    except:
        formatted_base_date = earliest_date_str
else:
    formatted_base_date = today_str

# 5. HTML 행 빌드
table_rows = ""
for s in stock_data:
    try:
        first_date_str = sorted(history_data[s['ticker']].keys())[0]
        dt_obj = datetime.strptime(first_date_str, "%Y-%m-%d")
        display_base_date = dt_obj.strftime("%y/%m/%d")
    except:
        display_base_date = datetime.now().strftime("%y/%m/%d")

    if s['dilution'] > 0:
        dilution_html = f'<td style="color: #ff6781; font-weight: bold;">+{s["dilution"]:.2f}% 🔺 <span style="font-size: 11px; color: #8899a6; font-weight: normal;">({display_base_date} 기점)</span></td>'
    elif s['dilution'] < 0:
        dilution_html = f'<td style="color: #00ba7c; font-weight: bold;">{s["dilution"]:.2f}% 🔻 <span style="font-size: 11px; color: #8899a6; font-weight: normal;">({display_base_date} 기점)</span></td>'
    else:
        dilution_html = f'<td style="color: #8899a6; font-size: 13px;">0.00% <span style="font-size: 11px; color: #536471;">({display_base_date} 기점)</span></td>'

    table_rows += f"""            <tr data-ticker="{s['ticker']}" data-shares="{s['shares']}" data-price="{s['price']}" data-marketcap="{s['marketcap']}">
                <td>${s['ticker']}</td>
                <td>{s['shares']:,}</td>
                {dilution_html}
                <td class="actual-price">${s['price']:,.2f}</td>
                <td>${s['marketcap']:,}</td>
                <td class="adjusted-price"></td>
                <td class="percent-diff"></td>
            </tr>\n"""

# 6. HTML 템플릿 생성
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Neo-Cloud: The Share Count Illusion</title>
    <style>
        body { background-color: #15202b; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; flex-direction: column; align-items: center; padding: 40px; }
        .card { background-color: #1e2732; border-radius: 16px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #38444d; width: 1040px; margin-bottom: 25px; }
        h2 { text-align: center; color: #ffffff; margin-top: 0; margin-bottom: 5px; font-size: 24px; letter-spacing: 0.5px; }
        p.subtitle { text-align: center; color: #8899a6; margin-bottom: 25px; font-size: 15px; line-height: 1.5; }
        .highlight-text { color: #1da1f2; font-weight: bold; }
        .date-badge { font-size: 13px; color: #8899a6; display: block; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; font-size: 15px; }
        th, td { padding: 14px 12px; text-align: right; border-bottom: 1px solid #38444d; vertical-align: middle; }
        th { background-color: #253341; color: #8899a6; font-weight: 600; text-transform: uppercase; font-size: 12px; cursor: pointer; user-select: none; }
        th:hover { background-color: #2c3640; color: #ffffff; }
        th:first-child, td:first-child { text-align: left; font-weight: bold; font-size: 16px; }
        td:first-child { cursor: pointer; color: #1da1f2; }
        td:first-child:hover { text-decoration: underline; }
        tr:hover { background-color: #2c3640; }
        .actual-price { color: #e1e8ed; }
        .adjusted-price { color: #00ba7c; font-weight: bold; font-size: 16px; }
        .percent-diff { color: #ffad1f; font-weight: bold; }
        .base-row { background-color: rgba(29, 161, 242, 0.15) !important; border-left: 4px solid #1da1f2; }
        .base-row td { color: #1da1f2 !important; }
        .base-row .adjusted-price, .base-row .percent-diff, .base-row .actual-price { color: #1da1f2 !important; }
        
        .disclaimer-footer { width: 1040px; background-color: rgba(255, 255, 255, 0.02); border: 1px solid #38444d; border-radius: 12px; padding: 20px; font-size: 12px; color: #8899a6; line-height: 1.6; text-align: justify; box-sizing: border-box; }
        .disclaimer-footer strong { color: #e1e8ed; }
    </style>
</head>
<body>

<div class="card">
    <h2>Neo-Cloud & Infra: The Share Count Illusion</h2>
    <p class="subtitle">
        Isolating the impact of dilution. What if every company had exactly the same number of shares as <span id="baseTickerName" class="highlight-text">$WYFI (38.61M)</span>?<br>
        <span class="date-badge">* Data as of market close on __MARKET_CLOSE_DATE__ (Click Ticker to change Base / Click Header to sort)</span>
    </p>
    
    <table id="stockTable">
        <thead>
            <tr>
                <th onclick="sortTable(0, false)">Ticker ↕</th>
                <th onclick="sortTable(1, true)">Current Shares ↕</th>
                <th onclick="sortTable(2, true)">Dilution ↕</th>
                <th onclick="sortTable(3, true)">Actual Price ($) ↕</th>
                <th onclick="sortTable(4, true)">Market Cap ($) ↕</th>
                <th onclick="sortTable(5, true)">Adjusted Price ($) ↕</th>
                <th id="ratioHeader" onclick="sortTable(6, true)">WYFI / Ticker (%) ↕</th>
            </tr>
        </thead>
        <tbody>
__TABLE_ROWS_PLACEHOLDER__        </tbody>
    </table>
</div>

<div class="disclaimer-footer">
    <strong>⚠️ Legal Disclaimer & Data Source Notice:</strong><br>
    All financial metrics, equity structures, and real-time comparative models displayed on this platform are processed using an automated hybrid tracking pipeline. Real-time asset market pricing is continuously aggregated from the <strong>Yahoo Finance API</strong>, while total integrated corporate share structures and capitalization data are parsed from <strong>Toss Investment (Toss Securities Co., Ltd.)</strong> asset analytics platforms to ensure precise institutional-grade border adjustments.<br><br>
    This tracking infrastructure utilizes <strong>__BASE_DATE_PLACEHOLDER__ as the immutable baseline date</strong> to quantify and compound downstream capital dilution vector updates. Calculated statistics are formulated strictly for computational insight, historical benchmarking, and macro-comparative review; no portion of these automated data feeds translates to formal investment advice, portfolio mandate generation, or equity underwriting valuation. Final transactional discretion belongs exclusively to the operator.<br><br>
    <strong>📧 Contact & Feedback:</strong> For data inquiries, tracking latency issues, or technical feedback, please contact the maintainer at <a href="mailto:dgkittyg@gmail.com" style="color: #1da1f2; text-decoration: none;">dgkittyg@gmail.com</a>.
</div>

<script>
let currentBaseShares = 38614216;
let currentBaseTicker = "WYFI";
let sortDirections = [false, false, false, false, true, false, false];

const formatCurrency = (num) => "$" + num.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
const formatPercent = (num) => num.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + "%";

function updateCalculations(baseShares, baseTicker, skipSort = false) {
    currentBaseShares = baseShares;
    currentBaseTicker = baseTicker;
    document.getElementById("baseTickerName").innerText = `$${baseTicker} (${(baseShares/1000000).toFixed(2)}M)`;
    document.getElementById("ratioHeader").innerText = `${baseTicker} / Ticker (%) ↕`;

    const rows = document.querySelectorAll("#stockTable tbody tr");
    rows.forEach(row => {
        const targetShares = parseFloat(row.getAttribute("data-shares"));
        const marketCap = parseFloat(row.getAttribute("data-marketcap"));
        const adjustedPrice = marketCap / currentBaseShares;
        const ratioPercent = (currentBaseShares / targetShares) * 100;
        
        row.querySelector(".adjusted-price").innerText = formatCurrency(adjustedPrice);
        row.querySelector(".percent-diff").innerText = formatPercent(ratioPercent);
        
        if (row.getAttribute("data-ticker") === baseTicker) {
            row.className = "base-row";
        } else {
            row.className = "";
        }
    });

    if (!skipSort) {
        initMarketCapSort();
    }
}

document.querySelectorAll("#stockTable tbody tr").forEach(row => {
    row.cells[0].addEventListener("click", () => {
        const baseShares = parseFloat(row.getAttribute("data-shares"));
        const baseTicker = row.getAttribute("data-ticker");
        updateCalculations(baseShares, baseTicker, true);
    });
});

function initMarketCapSort() {
    const table = document.getElementById("stockTable");
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    table.querySelectorAll("th")[4].innerText = "Market Cap ($) ▼";
    rows.sort((rowA, rowB) => {
        let numA = parseFloat(rowA.cells[4].innerText.replace(/[\\$,%,]/g, ''));
        let numB = parseFloat(rowB.cells[4].innerText.replace(/[\\$,%,]/g, ''));
        return numB - numA;
    });
    rows.forEach(row => tbody.appendChild(row));
}

function sortTable(columnIndex, isNumeric) {
    const table = document.getElementById("stockTable");
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    sortDirections[columnIndex] = !sortDirections[columnIndex];
    const ascending = sortDirections[columnIndex];
    
    const headers = table.querySelectorAll("th");
    headers.forEach((th, idx) => {
        let baseText = th.innerText.replace(/[▲▼↕]/g, "").trim();
        if (idx === columnIndex) th.innerText = baseText + (ascending ? " ▲" : " ▼");
        else th.innerText = baseText + " ↕";
    });

    rows.sort((rowA, rowB) => {
        let cellRawA = rowA.cells[columnIndex].innerText;
        let cellRawB = rowB.cells[columnIndex].innerText;
        if (isNumeric) {
            let numA = parseFloat(cellRawA.replace(/[\\$,%,\\+🔺🔻-]/g, '')) || 0;
            let numB = parseFloat(cellRawB.replace(/[\\$,%,\\+🔺🔻-]/g, '')) || 0;
            return ascending ? numA - numB : numB - numA;
        } else {
            return ascending ? cellRawA.localeCompare(cellRawB) : cellRawB.localeCompare(cellRawA);
        }
    });
    rows.forEach(row => tbody.appendChild(row));
}

let defaultShares = 38614216;
let defaultTicker = "WYFI";
document.querySelectorAll("#stockTable tbody tr").forEach(row => {
    if(row.getAttribute("data-ticker") === "WYFI") defaultShares = parseFloat(row.getAttribute("data-shares"));
});
updateCalculations(defaultShares, defaultTicker);
</script>
</body>
</html>"""

html_template = html_template.replace("__MARKET_CLOSE_DATE__", current_date)
html_template = html_template.replace("__TABLE_ROWS_PLACEHOLDER__", table_rows)
html_template = html_template.replace("__BASE_DATE_PLACEHOLDER__", formatted_base_date)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("🎉 [출처 및 공식 메일 반영 완료] 무결점 완전 자동화 대시보드가 성공적으로 배포되었습니다!")
