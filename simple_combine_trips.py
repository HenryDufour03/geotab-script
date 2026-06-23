"""
Simple Trip Data Combiner
Combines all Excel trip files into one master CSV file
"""

import pandas as pd
import os
from datetime import datetime

def extract_name_from_device(device_name):
    """
    Extract name after second dash, or use whole device name if only 1 dash
    Examples:
    '3713-FW-JUSTIN GLASS' -> 'JUSTIN GLASS'
    '2483-LOU-JON WALRAVEN' -> 'JON WALRAVEN'
    '2390-BEING SOLD' -> '2390-BEING SOLD' (only 1 dash, use whole name)
    """
    if pd.isna(device_name):
        return None
    
    device_str = str(device_name).strip()
    parts = device_str.split('-')
    
    # If there are at least 3 parts (2 dashes), take everything after the 2nd dash
    if len(parts) >= 3:
        name = '-'.join(parts[2:]).strip()
        return name if name else device_str
    
    # If only 1 dash or no dashes, return the whole device name
    return device_str

def extract_location_from_device(device_name):
    """
    Extract middle part between first and second dash
    Examples:
    '2655-LOU-ALICIA FRANZELL' -> 'LOU'
    '3713-FW-JUSTIN GLASS' -> 'FW'
    '2390-BEING SOLD' -> None (only 1 dash)
    """
    if pd.isna(device_name):
        return None
    
    device_str = str(device_name).strip()
    parts = device_str.split('-')
    
    # If there are at least 3 parts (2 dashes), take the middle part
    if len(parts) >= 3:
        return parts[1].strip()
    
    return None

def extract_address_from_location(location_text):
    """
    Extract address after the last colon
    Examples:
    'DAYTON FREIGHT ^66212: 2811 E Crescentville Rd, Cincinnati, OH 45241, USA' -> '2811 E Crescentville Rd, Cincinnati, OH 45241, USA'
    'Valley Truck Parts Inc ^V1001FR:F: 2206 Research Dr, Fort Wayne, IN 46808, USA' -> '2206 Research Dr, Fort Wayne, IN 46808, USA'
    """
    if pd.isna(location_text):
        return None
    
    location_str = str(location_text)
    
    # Find the last colon
    if ':' in location_str:
        # Split by colon and take everything after the last one
        address = location_str.rsplit(':', 1)[-1].strip()
        return address if address else None
    
    return None

def extract_location_code(location_text):
    """
    Extract all customer account numbers from trip detail location text
    
    Examples:
    'S&H TRUCKING INC ^s0275I, S&H Trucking,Inc ppte ^S0275I: 5411 Layton Rd...' -> 's0275I,S0275I'
    'Red Classic Transit 0ff3 ^352328, Kirk national Lease ^f410999:I: 4530 Albert...' -> '352328,f410999:I'
    'AJI ^A0173E, JJ'S CONCRETE ^J0078E, JJ's Concrete Construction ^J0728E: 9147 County...' -> 'A0173E,J0078E,J0728E'
    'CUSTOMER NAME ^A1234B:X: Address...' -> 'A1234B:X'  (colon with letter)
    'CUSTOMER NAME ^f410999:4: Address...' -> 'f410999:4'  (colon with number)
    """
    if pd.isna(location_text) or '^' not in str(location_text):
        return None
    
    try:
        location_str = str(location_text)
        customer_codes = []
        
        # Split by ^ to find all occurrences
        parts = location_str.split('^')[1:]  # Skip the first part (before first ^)
        
        for part in parts:
            # Skip any leading spaces after the ^
            part = part.lstrip(' ')
            
            # Extract code after ^ - need to handle colon accounts specially
            code = ''
            i = 0
            
            while i < len(part):
                char = part[i]
                
                if char in [' ', ',', '\t', '\n']:
                    break
                elif char == ':':
                    # Check if this is a colon account (letter or number after colon)
                    if i + 1 < len(part) and part[i + 1].isalnum():
                        # This is a colon account - include colon and next alphanumeric(s)
                        code += char  # Add the colon
                        i += 1
                        # Add 1-2 alphanumeric characters after the colon
                        char_count = 0
                        while i < len(part) and part[i].isalnum() and char_count < 2:
                            code += part[i]
                            i += 1
                            char_count += 1
                        break  # Stop here for colon accounts
                    else:
                        # Regular colon (like address separator) - stop here
                        break
                else:
                    code += char
                    i += 1
            
            if code.strip():  # Only add non-empty codes
                customer_codes.append(code.strip())
        
        return ','.join(customer_codes) if customer_codes else None
            
    except Exception:
        return None

def combine_trip_files():
    """Combine all trip Excel files into one CSV"""
    
    print("🚛 Palmer Trucks - Combining All Trip Data")
    print("=" * 50)
    
    # Get list of all trip files
    trip_files = []
    
    # Check trip-data-real folder (new format)
    if os.path.exists("trip-data-real"):
        for file in os.listdir("trip-data-real"):
            if file.endswith(".xlsx"):
                trip_files.append(("trip-data-real", file, "Data", 10))
    
    trip_files.sort(key=lambda x: x[1])  # Sort by filename
    print(f"Found {len(trip_files)} trip files to combine from trip-data-real")
    print()
    
    all_data = []
    total_trips = 0
    
    # Process each file
    for i, (folder, filename, sheet_name, skiprows) in enumerate(trip_files, 1):
        print(f"Processing {i}/{len(trip_files)}: {filename} ({folder})")
        
        try:
            file_path = f"{folder}/{filename}"
            
            # Read Excel file with appropriate sheet name and skiprows
            df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=skiprows)
            
            # Add which file this data came from
            df['SourceFile'] = filename
            df['SourceFolder'] = folder
            
            trips_in_file = len(df)
            total_trips += trips_in_file
            
            print(f"  ✅ Loaded {trips_in_file:,} trips")
            
            all_data.append(df)
            
        except Exception as e:
            print(f"  ❌ Error loading {filename}: {str(e)}")
            continue
    
    if not all_data:
        print("❌ No files could be loaded!")
        return
    
    print()
    print("📋 Combining all trip data...")
    
    # Combine everything into one big dataframe
    combined_trips = pd.concat(all_data, ignore_index=True)
    
    print("🧹 Cleaning data...")
    
    # Remove specific exception rule columns
    exception_columns = [
        'TripDetailExceptionRule1Duration', 'TripDetailExceptionRule1Count', 'TripDetailExceptionRule1Distance',
        'TripDetailExceptionRule2Duration', 'TripDetailExceptionRule2Count', 'TripDetailExceptionRule2Distance',
        'TripDetailExceptionRule3Duration', 'TripDetailExceptionRule3Count', 'TripDetailExceptionRule3Distance',
        'TripDetailExceptionRule4Duration', 'TripDetailExceptionRule4Count', 'TripDetailExceptionRule4Distance',
        'TripDetailExceptionRule5Duration', 'TripDetailExceptionRule5Count', 'TripDetailExceptionRule5Distance',
        'TripDetailExceptionRule6Duration', 'TripDetailExceptionRule6Count', 'TripDetailExceptionRule6Distance',
        'TripDetailExceptionRule7Duration', 'TripDetailExceptionRule7Count', 'TripDetailExceptionRule7Distance',
        'TripDetailExceptionRule8Duration', 'TripDetailExceptionRule8Count', 'TripDetailExceptionRule8Distance'
    ]
    
    # Remove exception columns that exist
    columns_to_remove = [col for col in exception_columns if col in combined_trips.columns]
    if columns_to_remove:
        combined_trips = combined_trips.drop(columns=columns_to_remove)
        print(f"   Removed {len(columns_to_remove)} exception rule columns")
    
    # Remove any columns that are completely blank (all NaN or empty)
    blank_columns = []
    for col in combined_trips.columns:
        if combined_trips[col].isna().all() or (combined_trips[col] == '').all():
            blank_columns.append(col)
    
    if blank_columns:
        combined_trips = combined_trips.drop(columns=blank_columns)
        print(f"   Removed {len(blank_columns)} completely blank columns")
    
    # Convert date columns to proper format
    date_columns = ['TripDetailStartDateTime', 'TripDetailStopDateTime']
    for col in date_columns:
        if col in combined_trips.columns:
            combined_trips[col] = pd.to_datetime(combined_trips[col], errors='coerce')
    
    # Remove unnecessary columns (keep TripDetailStopDateTime for sales matching)
    print("   Removing unnecessary columns...")
    columns_to_remove = [
        'UserComment',
        'DriverGroup', 'DriverGroup|Company Group', 'TripDetailStartDateTime',
        'TripDetailDrivingDuraion',
        'Location.ZoneExternalReference', 'TripDetailPrivateTrip',
        'TripDetailIdlingDuration', 'TripDetailSpeedRange1', 'TripDetailSpeedRange1Duration',
        'TripDetailSpeedRange2', 'TripDetailSpeedRange2Duration', 'TripDetailSpeedRange3',
        'TripDetailSpeedRange3Duration', 'TripDetailIsStartDriveWorkHours',
        'TripDetailIsStopDriveWorkHours',
        'TripDetailWorkHoursTripTime', 'TripDetailWorkHoursStopTime', 'TripDetailFuelConsumed'
    ]
    existing_columns_to_remove = [col for col in columns_to_remove if col in combined_trips.columns]
    if existing_columns_to_remove:
        combined_trips = combined_trips.drop(columns=existing_columns_to_remove)
        print(f"   Removed {len(existing_columns_to_remove)} unnecessary columns")
    
    # Extract Name from DeviceName
    if 'DeviceName' in combined_trips.columns:
        print("   Extracting Name from DeviceName...")
        combined_trips['Name'] = combined_trips['DeviceName'].apply(extract_name_from_device)
        names_found = combined_trips['Name'].notna().sum()
        print(f"   Extracted {names_found:,} names")
    
    # Extract Location code from DeviceName
    if 'DeviceName' in combined_trips.columns:
        print("   Extracting Location code from DeviceName...")
        combined_trips['Location'] = combined_trips['DeviceName'].apply(extract_location_from_device)
        locations_found = combined_trips['Location'].notna().sum()
        unique_locations = combined_trips['Location'].nunique()
        print(f"   Extracted {locations_found:,} location codes ({unique_locations} unique)")
    
    # Extract Address from TripDetailLocation
    if 'TripDetailLocation' in combined_trips.columns:
        print("   Extracting Address from TripDetailLocation...")
        combined_trips['Address'] = combined_trips['TripDetailLocation'].apply(extract_address_from_location)
        addresses_found = combined_trips['Address'].notna().sum()
        print(f"   Extracted {addresses_found:,} addresses")
    
    # Extract customer account codes from TripDetailLocation
    if 'TripDetailLocation' in combined_trips.columns:
        print("   Extracting customer account numbers from TripDetailLocation...")
        combined_trips['CustomerAccounts'] = combined_trips['TripDetailLocation'].apply(extract_location_code)
        
        # Show some examples of extracted codes
        extracted_samples = combined_trips[combined_trips['CustomerAccounts'].notna()]['CustomerAccounts'].head(5).tolist()
        if extracted_samples:
            print(f"   Sample customer accounts: {extracted_samples}")
            
        # Count how many have multiple accounts
        multi_account_count = combined_trips[combined_trips['CustomerAccounts'].str.contains(',', na=False)].shape[0]
        if multi_account_count > 0:
            print(f"   Found {multi_account_count:,} trips with multiple customer accounts")
    else:
        print("   TripDetailLocation column not found")
    
    # Filter to only Customer Zone rows (check both possible column names)
    zone_column = None
    if 'TripDetail' in combined_trips.columns:
        zone_column = 'TripDetail'
    elif 'Location.ZoneZoneTypes' in combined_trips.columns:
        zone_column = 'Location.ZoneZoneTypes'
    
    if zone_column:
        print(f"   Filtering to only 'Customer' zone rows (using {zone_column})...")
        before_filter = len(combined_trips)
        # Match both old format ("Customer Zone") and new format ("Customer")
        # Uses word boundaries to avoid partial matches
        has_customer_zone = combined_trips[zone_column].str.contains(r'\b(customer zone|customer)\b', case=False, na=False, regex=True)
        combined_trips = combined_trips[has_customer_zone].copy()
        print(f"   Kept {len(combined_trips):,} Customer zone rows (removed {before_filter - len(combined_trips):,})")
    else:
        print("   ⚠️  Warning: No zone type column found (TripDetail or Location.ZoneZoneTypes)")
    
    # Expand rows with multiple customer accounts
    if 'CustomerAccounts' in combined_trips.columns:
        multi_account_rows = combined_trips['CustomerAccounts'].str.contains(',', na=False).sum()
        if multi_account_rows > 0:
            print(f"   Expanding {multi_account_rows:,} rows with multiple accounts...")
            before_expansion = len(combined_trips)
            
            # Store original account list before splitting
            combined_trips['OriginalAccounts'] = combined_trips['CustomerAccounts']
            combined_trips['Split'] = combined_trips['CustomerAccounts'].str.contains(',', na=False)
            
            # Now split the accounts
            combined_trips['CustomerAccounts'] = combined_trips['CustomerAccounts'].str.split(',')
            combined_trips = combined_trips.explode('CustomerAccounts')
            combined_trips['CustomerAccounts'] = combined_trips['CustomerAccounts'].str.strip()
            # Keep rows with empty customer accounts - they need to be tracked/resolved
            # combined_trips = combined_trips[combined_trips['CustomerAccounts'].notna()]
            # combined_trips = combined_trips[combined_trips['CustomerAccounts'] != '']
            print(f"   Expanded to {len(combined_trips):,} rows (+{len(combined_trips) - before_expansion:,} rows)")
            print(f"   Added 'OriginalAccounts' column (shows all accounts from original trip)")
            print(f"   Added 'Split' column (True if row was split from multi-account trip)")
    
    # Merge with PCU3 customer data
    print()
    print("🔗 Merging with PCU3 customer data...")
    if os.path.exists("example-data/PCU3.csv"):
        try:
            # Uppercase CustomerAccounts for matching
            if 'CustomerAccounts' in combined_trips.columns:
                combined_trips['CustomerAccounts'] = combined_trips['CustomerAccounts'].str.upper()
            
            # Load PCU3
            pcu3 = pd.read_csv('example-data/PCU3.csv', encoding='latin1', skiprows=2, on_bad_lines='skip', low_memory=False)
            print(f"   Loaded {len(pcu3):,} customer records from PCU3")
            
            # Prepare PCU3 data
            pcu3_subset = pcu3[['Customer Number', 'Name', 'Address', 'City', 'State', 'Zip Code']].copy()
            pcu3_subset = pcu3_subset.rename(columns={
                'Name': 'CustomerName',
                'Address': 'CustomerAddress',
                'City': 'CustomerCity',
                'State': 'CustomerState',
                'Zip Code': 'CustomerZip'
            })
            
            # Merge
            combined_trips = combined_trips.merge(
                pcu3_subset,
                left_on='CustomerAccounts',
                right_on='Customer Number',
                how='left'
            )
            
            # Drop duplicate Customer Number column
            combined_trips = combined_trips.drop('Customer Number', axis=1)
            
            # Check match rate
            total_with_accounts = combined_trips['CustomerAccounts'].notna().sum()
            matched = combined_trips['CustomerName'].notna().sum()
            match_rate = (matched / total_with_accounts * 100) if total_with_accounts > 0 else 0
            
            print(f"   ✅ Matched {matched:,} of {total_with_accounts:,} trips ({match_rate:.1f}%)")
            print(f"   Added columns: CustomerName, CustomerAddress, CustomerCity, CustomerState, CustomerZip")
        except Exception as e:
            print(f"   ⚠️ Warning: Could not merge with PCU3: {e}")
    else:
        print("   ⚠️ PCU3.csv not found in example-data folder - skipping customer merge")
    
    # Add TripDate column for Power BI sales matching
    print()
    print("📅 Adding TripDate column...")
    combined_trips['TripDetailStopDateTime'] = pd.to_datetime(combined_trips['TripDetailStopDateTime'], errors='coerce')
    combined_trips['TripDate'] = combined_trips['TripDetailStopDateTime'].dt.date
    print(f"   ✅ Added TripDate column (extracted from TripDetailStopDateTime)")
    
    # Create output filename
    output_file = "data/all_trips_combined.csv"
    
    print()
    print("💾 Saving master CSV file...")
    combined_trips.to_csv(output_file, index=False)
    
    # Calculate some quick stats
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print()
    print("🎉 SUCCESS!")
    print("=" * 50)
    print(f"📁 Combined {len(trip_files)} files")
    print(f"🚛 Total trips: {total_trips:,}")
    print(f"📊 Final dataset: {combined_trips.shape[0]:,} rows × {combined_trips.shape[1]} columns")
    print(f"💾 Output file: {output_file}")
    print(f"📏 File size: {file_size_mb:.1f} MB")
    
    # Show date range
    if 'TripDetailStartDateTime' in combined_trips.columns:
        start_date = combined_trips['TripDetailStartDateTime'].min()
        end_date = combined_trips['TripDetailStartDateTime'].max()
        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Show top vehicles by trip count
    if 'DeviceName' in combined_trips.columns:
        top_vehicles = combined_trips['DeviceName'].value_counts().head(5)
        print()
        print("🚚 Top 5 vehicles by trip count:")
        for vehicle, count in top_vehicles.items():
            print(f"   {vehicle}: {count:,} trips")
    
    print()
    print("✅ Ready for Power BI! Just import the CSV file.")
    
    return output_file

if __name__ == "__main__":
    combine_trip_files()