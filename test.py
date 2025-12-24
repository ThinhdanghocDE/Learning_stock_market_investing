from vnstock import Quote
q = Quote(symbol="HPG", source="VCI")
df = q.history(interval="1m")
print(df.head())
