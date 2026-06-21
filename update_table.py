from datetime import datetime, timedelta
import yfinance as yf

# 1. 서머타임/윈터타임 통합 안전 시간 계산 함수
def get_last_market_close():
    today = datetime.now()
    weekday = today.weekday()
    
    if today.hour < 11:
        today = today - timedelta(days=1)
        weekday = today.weekday()

    if weekday == 5:
        target_date = today - timedelta(days=1)
    elif weekday == 6:
        target_date = today - timedelta(days=2)
    else:
        target_date = today
        
    return target_date.strftime("%B %d")

current_date = get_last_market_close()

# 2. 추적할 티커 리스트 정의 (총 20개)
tickers = [
    "NBIS", "CRWV", "IREN", "WULF", "HUT", "APLD", "CIFR", "CORZ", "FRMI", "MARA",
    "CLSK", "BTDR", "KEEL", "WYFI", "HIVE", "NUAI", "DGXX", "SLNH", "GLXY", "RIOT"
]

# 3. 야후 파이낸스에서 라이브 데이터 긁어오기
stock_data = []
print("🚀 야후 파이낸스에서 실시간 주가 및 주식수 데이터를 수집하는 중...")

for ticker_symbol in tickers:
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # 주가 가져오기 (종가, 현재가, 전일종가 순으로 예외 처리)
        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose') or 0.0
        # 발행 주식수 가져오기
        shares = info.get('sharesOutstanding') or 0
        # 시가총액 계산 또는 가져오기
        marketcap = info.get('marketCap') or int(shares * price)
        
        if shares > 0 and price > 0:
            stock_data.append({
                "ticker": ticker_symbol,
                "shares": int(shares),
                "price": float(price),
                "marketcap": int(marketcap)
            })
            print(f"✅ {ticker_symbol} 수집 완료: ${price:.2f} / {shares:,}주")
        else:
            print(f"⚠️ {ticker_symbol} 데이터가 불완전함 (Skip)")
    except Exception as e:
        print(f"❌ {ticker_symbol} 데이터 수집 실패: {e}")

# 4. HTML 행(Row) 조립
table_rows = ""
for s in stock_data:
    table_rows += f"""            <tr data-ticker="{s['ticker']}" data-shares="{s['shares']}" data-price="{s['price']}" data-marketcap="{s['marketcap']}">
                <td>${s['ticker']}</td>
                <td>{s['shares']:,}</td>
                <td class="actual-price">${s['price']:,.2f}</td>
                <td>${s['marketcap']:,}</td>
                <td class="adjusted-price"></td>
                <td class="percent-diff"></td>
            </tr>\n"""

# 5. 전체 HTML 코드 템플릿 정의
html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Neo-Cloud: The Share Count Illusion</title>
    <style>
        body {{ background-color: #15202b; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; padding: 40px; }}
        .card {{ background-color: #1e2732; border-radius: 16px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); border: 1px solid #38444d; width: 980px; }}
        h2 {{ text-align: center; color: #ffffff; margin-top: 0; margin-bottom: 5px; font-size: 24px; letter-spacing: 0.5px; }}
        p.subtitle {{ text-align: center; color: #8899a6; margin-bottom: 25px; font-size: 15px; line-height: 1.5; }}
        .highlight-text {{ color: #1da1f2; font-weight: bold; }}
        .date-badge {{ font-size: 13px; color: #8899a6; display: block; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
        th, td {{ padding: 14px 12px; text-align: right; border-bottom: 1px solid #38444d; }}
        th {{ background-color: #253341; color: #8899a6; font-weight: 600; text-transform: uppercase; font-size: 12px; cursor: pointer; user-select: none; }}
        th:hover {{ background-color: #2c3640; color: #ffffff; }}
        th:first-child, td:first-child {{ text-align: left; font-weight: bold; font-size: 16px; }}
        td:first-child {{ cursor: pointer; color: #1da1f2; }}
        td:first-child:hover {{ text-decoration: underline; }}
        tr:hover {{ background-color: #2c3640; }}
        .actual-price {{ color: #e1e8ed; }}
        .adjusted-price {{ color: #00ba7c; font-weight: bold; font-size: 16px; }}
        .percent-diff {{ color: #ffad1f; font-weight: bold; }}
        .base-row {{ background-color: rgba(29, 161, 242, 0.15) !important; border-left: 4px solid #1da1f2; }}
        .base-row td {{ color: #1da1f2 !important; }}
        .base-row .adjusted-price, .base-row .percent-diff, .base-row .actual-price {{ color: #1da1f2 !important; }}
    </style>
</head>
<body>

<div class="card">
    <h2>Neo-Cloud & Infra: The Share Count Illusion</h2>
    <p class="subtitle">
        Isolating the impact of dilution. What if every company had exactly the same number of shares as <span id="baseTickerName" class="highlight-text">$WYFI (38.61M)</span>?<br>
        <span class="date-badge">* Data as of market close on {current_date} (Click Ticker to change Base / Click Header to sort)</span>
    </p>
    
    <table id="stockTable">
        <thead>
            <tr>
                <th onclick="sortTable(0, false)">Ticker ↕</th>
                <th onclick="sortTable(1, true)">Current Shares ↕</th>
                <th onclick="sortTable(2, true)">Actual Price ($) ↕</th>
                <th id="marketCapHeader" onclick="sortTable(3, true)">Market Cap ($) ↕</th>
                <th id="adjustedHeader" onclick="sortTable(4, true)">Adjusted Price ($) ↕</th>
                <th id="ratioHeader" onclick="sortTable(5, true)">WYFI / Ticker (%) ↕</th>
            </tr>
        </thead>
        <tbody>
{table_rows}        </tbody>
    </table>
</div>

<script>
let currentBaseShares = 38614216;
let currentBaseTicker = "WYFI";
let sortDirections = [false, false, false, true, false, false];

const formatCurrency = (num) => "$" + num.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
const formatPercent = (num) => num.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) + "%";

function updateCalculations(baseShares, baseTicker, skipSort = false) {{
    currentBaseShares = baseShares;
    currentBaseTicker = baseTicker;
    document.getElementById("baseTickerName").innerText = `$${{baseTicker}} (${{(baseShares/1000000).toFixed(2)}}M)`;
    document.getElementById("ratioHeader").innerText = `${{baseTicker}} / Ticker (%) ↕`;

    const rows = document.querySelectorAll("#stockTable tbody tr");
    rows.forEach(row => {{
        const targetShares = parseFloat(row.getAttribute("data-shares"));
        const marketCap = parseFloat(row.getAttribute("data-marketcap"));
        const adjustedPrice = marketCap / currentBaseShares;
        const ratioPercent = (currentBaseShares / targetShares) * 100;
        
        row.querySelector(".adjusted-price").innerText = formatCurrency(adjustedPrice);
        row.querySelector(".percent-diff").innerText = formatPercent(ratioPercent);
        
        if (row.getAttribute("data-ticker") === baseTicker) {{
            row.className = "base-row";
        }} else {{
            row.className = "";
        }}
    }});

    if (!skipSort) {{
        initMarketCapSort();
    }}
}}

document.querySelectorAll("#stockTable tbody tr").forEach(row => {{
    row.cells[0].addEventListener("click", () => {{
        const baseShares = parseFloat(row.getAttribute("data-shares"));
        const baseTicker = row.getAttribute("data-ticker");
        updateCalculations(baseShares, baseTicker, true);
    }});
}});

function initMarketCapSort() {{
    const table = document.getElementById("stockTable");
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    
    table.querySelectorAll("th")[3].innerText = "Market Cap ($) ▼";

    rows.sort((rowA, rowB) => {{
        let cellA = rowA.cells[3].innerText;
        let cellB = rowB.cells[3].innerText;
        let numA = parseFloat(cellA.replace(/[\\$,%,]/g, ''));
        let numB = parseFloat(cellB.replace(/[\\$,%,]/g, ''));
        return numB - numA;
    }});
    rows.forEach(row => tbody.appendChild(row));
}}

function sortTable(columnIndex, isNumeric) {{
    const table = document.getElementById("stockTable");
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    sortDirections[columnIndex] = !sortDirections[columnIndex];
    const ascending = sortDirections[columnIndex];
    
    const headers = table.querySelectorAll("th");
    headers.forEach((th, idx) => {{
        let baseText = th.innerText.replace(/[▲▼↕]/g, "").trim();
        if (idx === columnIndex) {{
            th.innerText = baseText + (ascending ? " ▲" : " ▼");
        }} else {{
            th.innerText = baseText + " ↕";
        }}
    }});

    rows.sort((rowA, rowB) => {{
        let cellA = rowA.cells[columnIndex].innerText;
        let cellB = rowB.cells[columnIndex].inskyText; // Fixed typings
        let cellRawA = rowA.cells[columnIndex].innerText;
        let cellRawB = rowB.cells[columnIndex].innerText;
        if (isNumeric) {{
            let numA = parseFloat(cellRawA.replace(/[\\$,%,]/g, ''));
            let numB = parseFloat(cellRawB.replace(/[\\$,%,]/g, ''));
            return ascending ? numA - numB : numB - numA;
        }} else {{
            return ascending ? cellRawA.localeCompare(cellRawB) : cellRawB.localeCompare(cellRawA);
        }}
    }});
    rows.forEach(row => tbody.appendChild(row));
}}

// WYFI 자동 탐색 후 초기화 로직 (없을 시 첫번째 데이터 주식수 백업용)
let defaultShares = 38614216;
let defaultTicker = "WYFI";
const rows = document.querySelectorAll("#stockTable tbody tr");
rows.forEach(row => {{
    if(row.getAttribute("data-ticker") === "WYFI") {{
        defaultShares = parseFloat(row.getAttribute("data-shares"));
    }}
}});

updateCalculations(defaultShares, defaultTicker);
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
print("🎉 index.html이 실시간 마켓 데이터를 반영하여 빌드되었습니다.")
