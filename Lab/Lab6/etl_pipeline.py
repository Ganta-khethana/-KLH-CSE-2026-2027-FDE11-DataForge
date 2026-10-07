import pandas as pd
import sqlite3
import requests

# =================================
# EXTRACT
# =================================

# 1. CSV DATA

csv_data = """id,name,age
1,John,25
2,Alice,30
3,Bob,22
"""

with open("people.csv", "w") as file:
    file.write(csv_data)

df_csv = pd.read_csv("people.csv")

print("📄 CSV Data:")
print(df_csv)


# 2. SQL DATA

conn = sqlite3.connect("people.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS salaries (
    id INTEGER,
    salary INTEGER
)
""")

cursor.execute("DELETE FROM salaries")

cursor.executemany(
    "INSERT INTO salaries VALUES (?, ?)",
    [
        (1, 50000),
        (2, 60000),
        (3, 45000)
    ]
)

conn.commit()

df_sql = pd.read_sql(
    "SELECT * FROM salaries",
    conn
)

print("\n💰 SQL Data:")
print(df_sql)


# 3. API DATA

url = "https://jsonplaceholder.typicode.com/users"

response = requests.get(url)

api_data = response.json()

df_api = pd.DataFrame(api_data)[
    ["id", "username", "email"]
]

print("\n🌐 API Data:")
print(df_api.head(3))


# =================================
# TRANSFORM
# =================================

df_unified = (
    df_csv
    .merge(df_sql, on="id", how="left")
    .merge(df_api, on="id", how="left")
)

# Convert column names to lowercase

df_unified.columns = (
    df_unified.columns.str.lower()
)

# Select required columns

df_unified = df_unified[
    [
        "id",
        "name",
        "age",
        "salary",
        "username",
        "email"
    ]
]

print("\n🧩 Unified Data:")
print(df_unified)


# =================================
# LOAD
# =================================

df_unified.to_csv(
    "unified_data.csv",
    index=False
)

print(
    "\n✅ Unified data saved as unified_data.csv"
)


# Verify output

print("\n📁 Final Output:")

print(
    pd.read_csv("unified_data.csv")
)


# Close database

conn.close()