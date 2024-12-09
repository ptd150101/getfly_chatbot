import pandas as pd
df = pd.read_csv("/home/datpt/project/VPBank/Sacombank.csv")
# Giả sử df là DataFrame của bạn
df['archived'] = False
df['language'] = "vi"
df['customer_id'] = "Sacombank"
# Drop column 'chunk_id'
df = df.drop(columns=['chunk_id'])
df.to_csv("/home/datpt/project/VPBank/Sacombank.csv", index=False)