| 카테고리               | 용어          | 정식 명칭 (Full Name)                         | 수식 및 정의 (Logic)                             | 🛠 개발자 체크포인트 (Check Point)                                         |
| ------------------ | ----------- | ----------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------ |
| 계약 및 목표(Agreement) | SLA         | Service Level Agreement(서비스 수준 계약)        | 문서/규정"월간 SL 90% 달성 실패 시 페널티 부과" 등 계약 조건의 집합 | 단순 수치가 아님. 빌링(정산) 시스템과 연동되는 핵심 조건값(Threshold)으로 관리해야 함. centrical​ |
|                    | SL          | Service Level(서비스 레벨)                     | 실적 수치(목표시간 내 응답 콜) / (총 인입 콜 - 예외 콜)        | SLA의 기준을 충족하는지 보여주는 실시간 성적표. 모니터링 대시보드의 메인 지표. cisco​              |
| 생산성(Productivity)  | AHT         | Average Handling Time(평균 처리 시간)           | (Talk + Hold + ACW) / 처리 건수                 | 비용 산정의 핵심. Hold Time이 Talk Time 컬럼에 포함되었는지, 별도인지 확인 필수. nice​      |
|                    | ATT         | Average Talk Time(평균 통화 시간)               | Pure Talk Time / 처리 건수                      | 대기(Hold)와 후처리(ACW)를 뺀 순수 발화 시간만 추출. go4customer​                   |
|                    | ACW         | After Call Work(후처리 시간)                   | After Call Work Time / 처리 건수                | 상담사가 전화를 끊고 다음 콜 대기(Ready)를 누르기 전까지의 시간.                           |
|                    | CPH         | Calls Per Hour(시간당 처리 건수)                 | 처리 건수 / 로그인 시간                              | 분모를 '로그인 시간'으로 할지 '실제 업무 시간'으로 할지에 따라 생산성 해석이 달라짐.                 |
| 접근성(Accessibility) | ASA         | Average Speed of Answer(평균 응답 속도)         | 총 대기 시간 / 응답 콜 수                            | IVR 안내 멘트 시간은 제외하고, 큐(Queue) 진입 후 대기 시간만 계산하는 것이 표준.               |
|                    | Aband. Rate | Abandonment Rate(포기율)                     | (포기 콜 수 / 총 인입 콜 수) * 100                   | 포기 시점이 IVR 단계인지, 대기 큐 단계인지 구분하여 로그를 남겨야 함.                         |
| 품질(Quality)        | FCR         | First Call Resolution(1차 처리율)             | (재인입 없는 처리 콜) / 총 처리 콜                      | "재인입" 기준 정의 필수 (예: 24시간 내 동일 번호 재신고 없음). 로직 구현 난이도가 높음. upbe​      |
|                    | CSAT        | Customer Satisfaction Score(고객 만족도)       | (만족 응답 수 / 총 설문 응답 수) * 100                 | 통화 데이터(PBX)와 설문 데이터(Survey)를 Call ID나 전화번호로 매핑해야 함.                |
|                    | QA          | Quality Assurance(통화 품질 평가)               | 평가 점수 합계 / 평가 건수                            | 정량 데이터가 아닌 관리자의 평가 점수이므로 별도 테이블로 관리됨.                              |
| 시스템(System)        | IVR         | Interactive Voice Response(자동 응답 시스템)     | ARS 메뉴 트리                                   | 고객이 어떤 메뉴(Node)를 눌렀는지 추적하는 Trace Log 적재가 중요.                       |
|                    | ACD         | Automatic Call Distributor(자동 호 분배)       | 라우팅 엔진                                      | 상담사 스킬(Skill) 기반 분배 로직이 작동하는 핵심 엔진.                                |
|                    | CTI         | Computer Telephony Integration(컴퓨터 전화 통합) | 전화-PC 연동 미들웨어                               | 전화 수신 시 PC 팝업(Screen Pop)을 띄워주는 기술.                                |
