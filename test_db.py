from src.db_utils import get_tables, get_schema_text


print("=" * 60)
print("NORTHWIND DATABASE TEST")
print("=" * 60)


print("\nTABLES")
print("-" * 60)

tables = get_tables()

for table in tables:
    print("-", table)


print("\nSCHEMA")
print("-" * 60)

print(get_schema_text())


print("\n✅ DATABASE TEST PASSED")