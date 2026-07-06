#!/usr/bin/env python3
"""공공데이터포털 국토교통부 아파트 매매 실거래가 API에서 서울 실거래 데이터를 받아
data/apt_trades_raw.csv 로 저장한다.

API 키 발급 절차:
  1. https://www.data.go.kr/data/15126469/openapi.do 접속 (국토교통부_아파트 매매 실거래 자료)
  2. 우측 상단 "활용신청" 클릭 → 활용 목적 작성 후 제출 (승인까지 보통 몇 분~몇 시간)
  3. 마이페이지 > 개발계정에서 "일반 인증키 (Decoding)" 복사
  4. 환경변수로 등록:  export MOLIT_API_KEY="<발급받은 키>"

실행:
  python fetch_data.py 2024           # 2024년 1~12월, 서울 25개 자치구 전체
  python fetch_data.py 2024 --gu 강남구  # 특정 구만 (빠른 테스트용)
  python fetch_data.py 2024 --months 1 3  # 특정 개월만 (1~3월)

주의: 25개 구 x 12개월 = 최대 300회 API 호출이 발생한다.
빠르게 테스트하려면 --gu, --months 옵션으로 범위를 좁히는 것을 권장한다.
(레시피 번들에는 이미 샘플 CSV가 있으므로, API 키가 없어도 analysis.py는 바로 실행 가능하다.)
"""
import argparse
import csv
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

API = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
OUT = Path(__file__).resolve().parent / "data" / "apt_trades_raw.csv"

# 서울 25개 자치구 법정동코드(앞 5자리) — API는 구 이름이 아닌 이 코드로 조회한다
SEOUL_LAWD = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200",
    "광진구": "11215", "동대문구": "11230", "중랑구": "11260", "성북구": "11290",
    "강북구": "11305", "도봉구": "11320", "노원구": "11350", "은평구": "11380",
    "서대문구": "11410", "마포구": "11440", "양천구": "11470", "강서구": "11500",
    "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "송파구": "11680", "강동구": "11710",
    "강남구": "11740",
}

FIELDNAMES = ["구", "동", "단지명", "전용면적(㎡)", "계약년월", "계약일",
              "거래금액(만원)", "층", "건축년도"]


def fetch_month(key: str, lawd: str, ymd: str) -> list:
    """한 자치구(lawd코드) x 한 달(ymd) 실거래 목록을 페이지네이션하며 전부 받아온다."""
    items, page = [], 1
    while True:
        r = requests.get(API, params={
            "serviceKey": key, "LAWD_CD": lawd, "DEAL_YMD": ymd,
            "pageNo": page, "numOfRows": 1000,
        }, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        code = root.findtext(".//resultCode", "")
        if code not in ("00", "000"):
            raise RuntimeError(f"API error {code}: {root.findtext('.//resultMsg')}")
        batch = root.findall(".//item")
        items.extend(batch)
        total = int(root.findtext(".//totalCount", "0"))
        if page * 1000 >= total:
            return items
        page += 1


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("year", help="조회 연도 (예: 2024)")
    p.add_argument("--gu", help="특정 자치구 하나만 (예: 강남구). 미지정 시 서울 전체 25개 구")
    p.add_argument("--months", nargs=2, type=int, metavar=("START", "END"), default=[1, 12],
                    help="조회할 월 범위 (기본: 1 12 = 1~12월 전체)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    key = os.environ.get("MOLIT_API_KEY")
    if not key:
        sys.exit("MOLIT_API_KEY 환경변수에 공공데이터포털 서비스키를 설정하세요. "
                  "(스크립트 상단 docstring의 발급 절차 참고)")

    targets = {args.gu: SEOUL_LAWD[args.gu]} if args.gu else SEOUL_LAWD
    if args.gu and args.gu not in SEOUL_LAWD:
        sys.exit(f"알 수 없는 자치구: {args.gu}")

    rows, dropped = [], 0
    for gu, lawd in targets.items():
        for m in range(args.months[0], args.months[1] + 1):
            ymd = f"{args.year}{m:02d}"
            for it in fetch_month(key, lawd, ymd):
                price_raw = (it.findtext("dealAmount") or "").replace(",", "").strip()
                if not price_raw:
                    dropped += 1
                    continue
                rows.append({
                    "구": gu,
                    "동": (it.findtext("umdNm") or "").strip(),
                    "단지명": (it.findtext("aptNm") or "").strip(),
                    "전용면적(㎡)": it.findtext("excluUseAr") or "",
                    "계약년월": f"{it.findtext('dealYear')}{int(it.findtext('dealMonth')):02d}",
                    "계약일": it.findtext("dealDay") or "",
                    "거래금액(만원)": price_raw,
                    "층": it.findtext("floor") or "",
                    "건축년도": it.findtext("buildYear") or "",
                })
            time.sleep(0.2)  # API rate limit 배려
        print(f"{gu} 완료 — 누적 {len(rows)}건")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    print(f"저장: {OUT} ({len(rows)}건, 거래금액 결측 제외 {dropped}건)")
    print("다음 단계: python analysis.py")


if __name__ == "__main__":
    main()
