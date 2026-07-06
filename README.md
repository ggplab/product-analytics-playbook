# 📊 Data Analysis Playbook

**바로 실행되는 데이터분석 레시피 모음.**
모든 레시피는 `README(따라하기) + 실행 코드 + 결과 차트 + 재현 가능한 데이터`로 구성됩니다. 클론해서 30분 안에 같은 결과가 나오는 것만 올립니다.

> 이론서가 아닙니다. "이 분석, 당장 어떻게 하지?"에 대한 실전 답안지입니다.
> 🇰🇷 한국어 우선 · 시리즈: [n8n-playbook](https://github.com/ggplab/n8n-playbook)의 데이터분석 편

## 🗂 Start Here — 데이터, 어디서 구하나

분석의 첫 관문은 데이터 구하기입니다. 용도별 수집처 가이드부터 보세요.

| 문서 | 내용 |
|------|------|
| [Data Sources](00-data-sources/) | 공공데이터포털부터 Kaggle까지 — 검증된 데이터 수집처 총정리 + AI에게 API 찾게 하는 법 |

## 📐 Recipes — 도메인별 레시피

짧고 재사용 가능한 분석 패턴. 폴더째 가져다 쓸 수 있게 설계했습니다.

| # | 레시피 | 도메인 | 스택 |
|---|--------|--------|------|
| 1 | [Cohort Retention Analysis](01-recipes/product-analytics/cohort-retention/) — 코호트 리텐션 분석 | Product Analytics | pandas · SQL |
| 2 | [Statistics Essentials](01-recipes/statistics/) — 실무자를 위한 통계분석 이론 (기술통계 → 가설검정 → 인과추론) | Statistics | 이론 가이드 |
| 3 | [ML Fundamentals](01-recipes/machine-learning/) — 머신러닝 기초 개념 (전처리 → 분류 → 회귀 → 군집) | Machine Learning | 이론 가이드 |

**Coming soon**: Funnel Analysis, A/B Test 판정, Weekly Active 지표 설계 (Product Analytics) · 차트 고르기 가이드 (Visualization)

## 🔬 Case Studies — 실데이터 엔드투엔드

공개 데이터로 처음부터 끝까지. 수집 → 전처리 → 분석 → 시각화 전 과정을 담았습니다.

| # | 케이스 | 데이터 | 한 줄 요약 |
|---|--------|--------|-----------|
| 1 | [Seoul Apartment Trends](02-case-studies/seoul-apt-trends/) — 서울 아파트 실거래 분석 | 국토부 실거래가 API | 내 집 마련 전에 데이터부터 |
| 2 | [Equipment Sensor Analysis](02-case-studies/equipment-sensor-analysis/) — 장비 센서 이상탐지 | 공공 센서 데이터 | ML 없이 groupby만으로 하는 이상탐지 |

## 🖼 Analysis Gallery — 실전 프로젝트 갤러리

지난 3년 멘토링·심사에서 나온 실전 분석 49건을 익명화해 정리했습니다. "잘 만든 분석은 어떤 구조인가"를 실제 사례로 보는 섹션입니다.

| 문서 | 내용 |
|------|------|
| [Analysis Gallery](03-analysis-gallery/) | 심층 카드 17건 (질문→접근→핵심 결과→배울 점, 수치 실측 발췌) + 주제 아이디어 뱅크 32건 |

## 🗺 Roadmap

- [x] 데이터 수집처 가이드
- [x] 첫 레시피 3종 (코호트 리텐션 · 아파트 실거래 · 센서 이상탐지)
- [x] 통계·ML 이론 가이드
- [x] 실전 프로젝트 갤러리 (심층 카드 17 + 아이디어 뱅크 32)
- [ ] Product Analytics 레시피 확장 — 퍼널, A/B 테스트, 지표 설계
- [ ] Age of Steam 웹 보드게임 유저 분석 케이스스터디 (자체 서비스 실측 데이터)
- [ ] 공정·엔지니어링 심층 카드 (반도체·페니실린·수질 등)
- [ ] Visualization 섹션 채우기
- [ ] 도메인별 하위집합 — 커머스 분석, 콘텐츠 서비스 분석, 헬스케어 분석
- [ ] 레시피의 Claude Code 스킬/플러그인화 — 폴더째 떼어 플러그인으로

## 📚 References — 함께 보면 좋은 것들

이 플레이북이 다루지 않는 영역은 이미 훌륭한 자료들이 있습니다.

| 자료 | 무엇 | 왜 |
|------|------|-----|
| [pandas-cookbook](https://github.com/jvns/pandas-cookbook) | pandas 레시피 노트북 (⭐7k) | pandas 문법 자체가 막힐 때 |
| [Python Data Science Handbook](https://github.com/jakevdp/PythonDataScienceHandbook) | 데이터과학 정석 교재 (⭐48k) | 기초 이론을 체계적으로 |
| [Scientific Visualization Book](https://github.com/rougier/scientific-visualization-book) | matplotlib 시각화의 끝 (⭐11k) | 차트 품질을 한 단계 올릴 때 |
| [awesome-data-analysis](https://github.com/PavelGrigoryevDS/awesome-data-analysis) | 데이터분석 리소스 큐레이션 | 영어권 자료 탐색 |
| [awesome-datascience](https://github.com/academic/awesome-datascience) | 데이터과학 메가 큐레이션 (⭐29k) | 로드맵·커리어 자료 |

## 🤝 Contributing

레시피 추가 PR을 환영합니다. 규칙은 하나 — **클론 직후 실행이 되어야 합니다.**

```
your-recipe/
├── README.md          # 개요 → 데이터 출처 → 실행 방법 → 분석 단계 → 결과 → 해석 → 한계
├── analysis.py        # 실행하면 assets/에 차트 저장
├── requirements.txt   # 버전 고정
├── data/              # 1MB 미만 샘플 (초과분은 fetch 스크립트로)
└── assets/            # 결과 차트
```

## ✍️ Author

**BuildnWrite** (빌드앤라이트) — 시행착오를 먼저 겪은 데이터 분석가. 정답이 아니라 관점을 나눕니다.

- Threads: [@buildnwrite](https://www.threads.com/@buildnwrite)
- LinkedIn: [jayjunglim](https://www.linkedin.com/in/jayjunglim/)

## License

[MIT](LICENSE) — 코드·문서 모두 자유롭게 쓰되, 출처 한 줄이면 충분합니다.
