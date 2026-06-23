import pandas as pd

df = pd.read_csv('data/all_trips_combined.csv')

print('✅ FINAL DATA VERIFICATION:')
print('=' * 50)
print(f'Total rows in combined file: {len(df):,}')
print(f'Date range: {df["TripDate"].min()} to {df["TripDate"].max()}')
print()

print('Breakdown by format:')
old_format = df[df['Location.ZoneZoneTypes'].str.contains('Customer Zone', na=False)]
new_format = df[df['Location.ZoneZoneTypes'].str.contains(r'^Customer$', regex=True, na=False)]
print(f'  Old format ("Customer Zone"): {len(old_format):,} rows')
print(f'  New format ("Customer"): {len(new_format):,} rows')
print(f'  Total: {len(old_format) + len(new_format):,} rows')
print()

print('Customer matching:')
print(f'  Rows with CustomerAccounts: {df["CustomerAccounts"].notna().sum():,}')
print(f'  Rows matched to PCU3: {df["CustomerName"].notna().sum():,}')
print(f'  Match rate: {df["CustomerName"].notna().sum() / len(df) * 100:.1f}%')
print()

print('Sample of recent May 2026 data:')
may26 = df[df['SourceFile'] == '05.26.xlsx'].head(3)
print(may26[['DeviceName', 'TripDate', 'Location.ZoneZoneTypes', 'CustomerAccounts', 'CustomerName']].to_string())
