import pandas as pd

# 단순 데이터 9개
data = [
    # 맑은 날 - 여유로움
    {
        "weather": "Sunny",
        "staff": 0,
        "calls": 1000,
        "answered": 950,
        "rate": 95,
        "grade": "S",
    },
    {
        "weather": "Sunny",
        "staff": 3,
        "calls": 1000,
        "answered": 980,
        "rate": 98,
        "grade": "S",
    },
    {
        "weather": "Sunny",
        "staff": 5,
        "calls": 1000,
        "answered": 990,
        "rate": 99,
        "grade": "S",
    },
    # 비 오는 날 - 약간 바쁨
    {
        "weather": "Rain",
        "staff": 0,
        "calls": 1200,
        "answered": 1020,
        "rate": 85,
        "grade": "B",
    },
    {
        "weather": "Rain",
        "staff": 5,
        "calls": 1200,
        "answered": 1080,
        "rate": 90,
        "grade": "A",
    },
    {
        "weather": "Rain",
        "staff": 10,
        "calls": 1200,
        "answered": 1140,
        "rate": 95,
        "grade": "S",
    },
    # 눈 오는 날 - 매우 바쁨
    {
        "weather": "Snow",
        "staff": 0,
        "calls": 1500,
        "answered": 900,
        "rate": 60,
        "grade": "D",
    },
    {
        "weather": "Snow",
        "staff": 10,
        "calls": 1500,
        "answered": 1125,
        "rate": 75,
        "grade": "C",
    },
    {
        "weather": "Snow",
        "staff": 20,
        "calls": 1500,
        "answered": 1425,
        "rate": 95,
        "grade": "S",
    },
]

df = pd.DataFrame(data)
df.to_csv("simple_data.csv", index=False)
print("✅ simple_data.csv 생성 완료!")
print(df)
