# 🗂 Data Sources — 데이터, 어디서 구하나

분석 도구는 다들 쓸 줄 아는데, 정작 **"어디서 어떤 데이터를 가져오지?"** 에서 막히는 경우가 많습니다.
이 문서는 실제 분석 프로젝트에서 검증한 데이터 수집처를 용도별로 정리한 가이드입니다. 이 플레이북의 모든 레시피는 여기 나온 출처의 데이터로 만들어졌습니다.

## 국내 공공 데이터 | Korean Public Data

| 출처 | 무엇이 있나 | 이럴 때 |
|------|-------------|---------|
| [공공데이터포털](https://www.data.go.kr) | 국내 공공 데이터의 관문. 날씨, 교통, 부동산, 인구, 의료 등 | 국내 데이터가 필요하면 무조건 여기부터 |
| [서울 열린데이터광장](https://data.seoul.go.kr) | 서울시 한정, 지하철 승하차·따릉이·상권 등 도시 데이터 | 서울 관련 분석은 포털보다 여기가 빠름 |
| [국토교통부 실거래가](https://rt.molit.go.kr) | 아파트·주택·토지 실거래 내역 | 부동산 분석 ([케이스스터디](../02-case-studies/seoul-apt-trends/) 참고) |
| [KOSIS 국가통계포털](https://kosis.kr) | 통계청 공식 통계. 인구·고용·물가 시계열 | "공식 수치"가 필요한 리포트·기사 검증 |
| [AI Hub](https://www.aihub.or.kr) | 한국어 음성·이미지·텍스트 AI 학습 데이터 | ML/AI 모델 학습용 한국어 데이터 |

## 국내 경제·금융 | Korean Economy & Finance

| 출처 | 무엇이 있나 | 이럴 때 |
|------|-------------|---------|
| [한국은행 ECOS](https://ecos.bok.or.kr) | 금리·환율·통화량 등 경제 통계 API | 거시경제 지표가 필요한 분석 |
| [Open DART](https://opendart.fss.or.kr) | 상장사 공시·재무제표 API | 기업 재무 분석, 종목 스크리닝 |

## API 모음 | API Collections

| 출처 | 무엇이 있나 | 이럴 때 |
|------|-------------|---------|
| [open-apis-korea](https://github.com/dl0312/open-apis-korea) | 한국 서비스 API 큐레이션 (⭐3.8k) | 국내 서비스 API 찾을 때 여기부터 |
| [public-apis](https://github.com/public-apis/public-apis) | 무료 공개 API 모음 (⭐440k+) | 글로벌 데이터가 필요할 때 |
| [RapidAPI](https://rapidapi.com) | 유료 API 마켓플레이스 | 무료로 안 되는 데이터를 돈 주고 살 때 |

## 글로벌 데이터셋 | Global Datasets

| 출처 | 무엇이 있나 | 이럴 때 |
|------|-------------|---------|
| [Kaggle Datasets](https://www.kaggle.com/datasets) | 분석 대회·커뮤니티 데이터셋. 노트북 예제 풍부 | 연습·포트폴리오용 데이터 + 남의 분석 참고 |
| [Hugging Face Datasets](https://huggingface.co/datasets) | ML 학습용 데이터셋 허브 | NLP·비전 모델 학습 데이터 |
| [UCI ML Repository](https://archive.ics.uci.edu) | 고전 ML 벤치마크 데이터셋 | 알고리즘 연습·교육용 정제 데이터 |
| [Google Dataset Search](https://datasetsearch.research.google.com) | 데이터셋 전용 검색엔진 | "이런 데이터가 세상에 있긴 한가?" 확인 |
| [Our World in Data](https://ourworldindata.org) | 국가별 시계열 (인구·에너지·보건 등) | 국가 비교·장기 추세 시각화 |

## 트렌드·검색 데이터 | Trends & Search

| 출처 | 무엇이 있나 | 이럴 때 |
|------|-------------|---------|
| [네이버 데이터랩](https://datalab.naver.com) | 네이버 검색어 트렌드, 쇼핑 인사이트 | 국내 소비자 관심사 추이 |
| [Google Trends](https://trends.google.com) | 구글 검색어 트렌드 | 글로벌·국내 관심사 비교 |

## 💡 꿀팁 — AI에게 목록을 통째로 넘기기

이 목록을 Claude 같은 AI에게 던지고 이렇게 물어보세요:

> "나는 ○○를 분석하려고 해. 위 출처 중에 맞는 API를 찾고,
> 무료인지 / 호출 제한은 얼마인지 / 어떤 필드를 주는지 정리해줘."

API 문서를 직접 뒤지지 않아도 후보 비교표가 나옵니다. 이 플레이북의 레시피들도 같은 방식으로 데이터 출처를 골랐습니다.

## 어떤 출처를 언제 쓰나 — 요약

- **국내 생활·도시·부동산** → 공공데이터포털, 서울 열린데이터광장, 실거래가
- **공식 통계 인용** → KOSIS, ECOS
- **기업·금융** → Open DART, ECOS
- **연습·포트폴리오** → Kaggle, UCI
- **ML 학습 데이터** → Hugging Face, AI Hub
- **"이런 데이터 있나?"** → Google Dataset Search → 없으면 API 모음 2곳

---

새 출처 추가 제안은 PR로 환영합니다. 기준: ①무료 티어 존재 ②문서화된 접근 방법 ③실제 분석에 써본 경험담 1줄.
