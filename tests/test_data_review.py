import numpy as np
import pandas as pd

df = pd.read_csv("data/yesterday_calls.csv")

print(df)


income_call = df["인입콜"].sum()
answer_call = df["응답콜"].sum()

print(income_call)
print(answer_call)

division_result = answer_call / income_call

SLA = np.round(division_result, decimals=2) * 100

print(SLA)


print(round(df["응답콜"].sum() / df["인입콜"].sum(), 2))
