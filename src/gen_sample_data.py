import random

import pandas as pd

# 시간대별 샘플 데이터 생성
data = []

# 09시 ~ 익일 02시 (09, 10, ... 23, 00, 01, 02)
hours = list(range(9, 24)) + list(range(0, 3))

for hour in hours:
    # 시간대별 인입콜
    if hour in [12, 13, 14]:  # 점심시간 피크
        inbound = random.randint(80, 120)
    elif hour in [19, 20, 21]:  # 저녁 피크
        inbound = random.randint(70, 100)
    elif hour in [0, 1, 2]:  # 새벽 한산
        inbound = random.randint(10, 25)
    elif hour in [22, 23]:  # 밤
        inbound = random.randint(20, 40)
    else:
        inbound = random.randint(50, 80)

    # 응답콜 (인입의 75~98%)
    answer_rate = random.uniform(0.75, 0.98)
    answered = int(inbound * answer_rate)

    # 투입인원 (시간대별 다르게)
    if hour in [0, 1, 2]:
        staff = random.randint(3, 5)
    elif hour in [22, 23]:
        staff = random.randint(5, 8)
    else:
        staff = random.randint(10, 15)

    # 통화시간 (평균 3~5분, 초 단위)
    talk_time = random.randint(180, 300)

    # 후처리시간 (평균 1~2분, 초 단위)
    after_work = random.randint(60, 120)

    # 휴식시간 (평균 5~10분, 초 단위)
    break_time = random.randint(300, 600)

    data.append(
        {
            "시간": hour,
            "인입콜": inbound,
            "응답콜": answered,
            "투입인원": staff,
            "통화시간": talk_time,
            "후처리시간": after_work,
            "휴식시간": break_time,
        }
    )

df = pd.DataFrame(data)
df.to_csv("yesterday_calls.csv", index=False, encoding="utf-8-sig")

print(df)
print(f"\n총 인입: {df['인입콜'].sum()}")
print(f"총 응답: {df['응답콜'].sum()}")
print(f"응답률: {df['응답콜'].sum() / df['인입콜'].sum() * 100:.1f}%")
