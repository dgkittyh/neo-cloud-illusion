name: Neo-Cloud Illusion Live Update

on:
  schedule:
    # 매일 미국 장 마감 이후 자동으로 돌도록 스케줄링
    - cron: '0 23 * * 1-5'
  workflow_dispatch: # 웹에서 'Run workflow' 버튼으로 수동 즉시 실행 가능

jobs:
  update-dashboard:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/with-python@v4
      with:
        python-version: '3.10'

    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install requests beautifulsoup4 yfinance

    - name: Run Python Script
      run: python update_table.py

    # 🎯 순서를 완벽하게 정렬하여 128 에러를 원천 차단하는 최종 깃 루틴
    - name: Commit and Push Changes
      run: |
        git config --global user.name "github-actions[bot]"
        git config --global user.email "github-actions[bot]@users.noreply.github.com"
        
        # 1. 파이썬이 새로 구워낸 history.json과 index.html을 장바구니에 먼저 담습니다.
        git add history.json index.html
        
        # 2. 장바구니에 담은 상태에서 깃허브 원격 서버의 최신 상태와 순서를 맞춥니다.
        git pull origin main --rebase
        
        # 3. 변경 사항이 확실히 있을 때만 안전하게 최종 커밋 및 푸시를 날립니다.
        if ! git diff --cached --quiet; then
          git commit -m "📡 라이브 데이터 및 타임스탬프 자동 동기화 완결"
          git push origin main
        else
          echo "변동 사항이 없으므로 빌드를 스킵합니다."
        fi
