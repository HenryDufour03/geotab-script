"""
Fetch OSS Trip Data from GeoTab API
Fetches OSS trips with zone matching (no driver CSV output)
"""

import mygeotab
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

def calculate_bounding_box(polygon_points):
    """Calculate bounding box (min/max x,y) for a polygon"""
    if not polygon_points:
        return None
    
    x_coords = [p['x'] for p in polygon_points]
    y_coords = [p['y'] for p in polygon_points]
    
    return {
        'min_x': min(x_coords),
        'max_x': max(x_coords),
        'min_y': min(y_coords),
        'max_y': max(y_coords)
    }

def point_in_bounding_box(point, bbox):
    """Quick check if point is within bounding box"""
    if not bbox:
        return False
    
    x, y = point['x'], point['y']
    return (bbox['min_x'] <= x <= bbox['max_x'] and 
            bbox['min_y'] <= y <= bbox['max_y'])

def point_in_polygon(point, polygon_points):
    """Check if a point is inside a polygon using ray casting algorithm"""
    x, y = point['x'], point['y']
    n = len(polygon_points)
    inside = False
    
    p1x, p1y = polygon_points[0]['x'], polygon_points[0]['y']
    for i in range(1, n + 1):
        p2x, p2y = polygon_points[i % n]['x'], polygon_points[i % n]['y']
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def fetch_oss_trips():
    """Fetch OSS trips from GeoTab API with zone matching"""
    
    # Load credentials from .env file
    load_dotenv()
    DATABASE = os.getenv('GEO_DATABASE')
    USERNAME = os.getenv('GEO_USER')
    PASSWORD = os.getenv('GEO_PASSWORD')
    
    print("🔐 Connecting to GeoTab API...")
    print(f"   Database: {DATABASE}")
    print(f"   User: {USERNAME}\n")
    
    try:
        # Connect to GeoTab
        api = mygeotab.API(username=USERNAME, password=PASSWORD, database=DATABASE)
        api.authenticate()
        print("✅ Connected successfully!\n")
        
        # Fetch all groups first
        print("📥 Fetching group data...")
        all_groups = api.call("Get", typeName="Group")
        group_map = {group['id']: group.get('name', '') for group in all_groups}
        print(f"✅ Found {len(all_groups)} groups\n")
        
        # Find OSS group ID
        oss_group_id = None
        for group_id, group_name in group_map.items():
            if group_name == 'OSS':
                oss_group_id = group_id
                print(f"✅ Found OSS group (ID: {oss_group_id})\n")
                break
        
        if not oss_group_id:
            print("❌ OSS group not found!")
            return None
        
        # ============= FETCH OSS TRIPS =============
        print("=" * 80)
        print("FETCHING OSS TRIPS")
        print("=" * 80)
        
        # Fetch zones for customer matching
        print("\n📥 Fetching zones for customer matching...")
        all_zones = api.call("Get", typeName="Zone")
        print(f"✅ Found {len(all_zones)} total zones")
        
        # Filter to only Customer Zones for better performance
        # Handles both old format ("Customer Zone") and new format ("Customer")
        print("   Filtering to Customer Zones only...")
        customer_zones = []
        for zone in all_zones:
            zone_types = zone.get('zoneTypes', [])
            is_customer = False
            
            for zt in zone_types:
                zone_type_name = ''
                if isinstance(zt, dict):
                    zone_type_name = zt.get('name', '').lower().strip()
                elif isinstance(zt, str):
                    zone_type_name = zt.lower().strip()
                
                # Match exact "customer zone" (old) or "customer" (new)
                if zone_type_name in ['customer zone', 'customer']:
                    is_customer = True
                    break
            
            if is_customer:
                customer_zones.append(zone)
        
        print(f"   ✅ Filtered to {len(customer_zones)} Customer Zones ({len(customer_zones)/len(all_zones)*100:.1f}% of total)")
        print(f"   ⚡ Reduced search space by {len(all_zones) - len(customer_zones)} zones\n")
        
        # Pre-calculate bounding boxes for all customer zones
        print("   Pre-calculating bounding boxes for faster matching...")
        zone_bboxes = {}
        for zone in customer_zones:
            if zone.get('geometryType') == 'Polygon':
                points = zone.get('points', [])
                if points:
                    zone_id = zone.get('id')
                    zone_bboxes[zone_id] = calculate_bounding_box(points)
        print(f"   ✅ Calculated {len(zone_bboxes)} bounding boxes\n")
        
        # Fetch all drivers/users to get their driver groups and names
        print("📥 Fetching all users for driver info mapping...")
        all_users = api.call("Get", typeName="User")
        driver_info_map = {}
        for user in all_users:
            user_id = user.get('id')
            driver_groups = user.get('driverGroups', [])
            group_names = []
            if driver_groups:
                for g in driver_groups:
                    if isinstance(g, dict):
                        group_id = g.get('id', '')
                        group_name = group_map.get(group_id, '')
                        if group_name:
                            group_names.append(group_name)
                    elif isinstance(g, str):
                        group_name = group_map.get(g, g)
                        group_names.append(group_name)
            driver_info_map[user_id] = {
                'driver_groups': ', '.join(group_names) if group_names else '',
                'first_name': user.get('firstName', ''),
                'last_name': user.get('lastName', ''),
                'email': user.get('name', '')
            }
        print(f"✅ Built driver info mapping for {len(all_users)} users\n")
        
        # Fetch all devices to get device groups 
        print("📥 Fetching all devices for device group mapping...")
        all_devices = api.call("Get", typeName="Device")
        device_info_map = {}
        for device in all_devices:
            device_id = device.get('id')
            device_name = device.get('name', '')
            device_groups_list = device.get('groups', [])
            device_group_names = []
            if device_groups_list:
                for g in device_groups_list:
                    if isinstance(g, dict):
                        group_id = g.get('id', '')
                        group_name = group_map.get(group_id, '')
                        if group_name:
                            device_group_names.append(group_name)
                    elif isinstance(g, str):
                        group_name = group_map.get(g, g)
                        device_group_names.append(group_name)
            device_info_map[device_id] = {
                'device_name': device_name,
                'device_groups': ', '.join(device_group_names) if device_group_names else ''
            }
        print(f"✅ Built device info mapping for {len(all_devices)} devices\n")
        
        # Set up date range for this month
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Get first day of next month
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)
        
        print(f"📅 Fetching trips for this month: {month_start.strftime('%B %Y')}")
        print(f"   From: {month_start}")
        print(f"   To: {month_end}\n")
        
        # Fetch trips for OSS group
        print("📥 Fetching OSS trips...")
        trips = api.call("Get",
                        typeName="Trip",
                        search={
                            "groups": [{"id": oss_group_id}],
                            "fromDate": month_start.isoformat(),
                            "toDate": month_end.isoformat()
                        })
        
        print(f"✅ Found {len(trips)} trips for OSS group this month\n")
        
        if len(trips) == 0:
            print("ℹ️  No trips found for this month")
            return None
        
        # Process trip data
        print("📋 Processing trip data and matching to customer zones...")
        trip_list = []
        matched_count = 0
        bbox_skipped = 0
        progress_interval = max(1, len(trips) // 10)  # Show progress every 10%
        
        for idx, trip in enumerate(trips, 1):
            # Show progress
            if idx % progress_interval == 0:
                print(f"   Processed {idx}/{len(trips)} trips ({idx/len(trips)*100:.0f}%)...")
            
            # Parse device info and lookup device details
            device = trip.get('device', {})
            device_id = device.get('id', '') if isinstance(device, dict) else str(device)
            device_info = device_info_map.get(device_id, {})
            device_name = device_info.get('device_name', '')
            device_groups = device_info.get('device_groups', '')
        
            # Parse driver info and lookup driver details
            driver = trip.get('driver', {})
            if isinstance(driver, dict):
                driver_id = driver.get('id', '')
            else:
                driver_id = str(driver)

            # Look up driver info from the pre-built mapping
            driver_info = driver_info_map.get(driver_id, {})
            first_name = driver_info.get('first_name', '')
            last_name = driver_info.get('last_name', '')
            driver_email = driver_info.get('email', '')
            driver_groups = driver_info.get('driver_groups', '')
            
            # Get stop point and match to zones
            stop_point = trip.get('stopPoint', {})
            customer_name = ''
            customer_number = ''
            zone_name = ''
            zone_types = ''
            
            if stop_point and 'x' in stop_point and 'y' in stop_point:
                # Check each customer zone to see if stop point is inside
                for zone in customer_zones:
                    if zone.get('geometryType') == 'Polygon':
                        zone_id = zone.get('id')
                        
                        # Quick bounding box check first
                        bbox = zone_bboxes.get(zone_id)
                        if bbox and not point_in_bounding_box(stop_point, bbox):
                            bbox_skipped += 1
                            continue  # Skip expensive polygon check
                        
                        points = zone.get('points', [])
                        if points and point_in_polygon(stop_point, points):
                            zone_name = zone.get('name', '')
                            customer_number = zone.get('comment', '')
                            customer_name = f"{customer_number} - {zone_name}" if customer_number else zone_name
                            
                            # Get zone types
                            zone_type_list = zone.get('zoneTypes', [])
                            zone_type_names = []
                            for zt in zone_type_list:
                                if isinstance(zt, dict):
                                    zone_type_names.append(zt.get('name', ''))
                                elif isinstance(zt, str):
                                    # Map zone type IDs to readable names
                                    type_name_map = {
                                        'ZoneTypeCustomerId': 'Customer Zone',
                                        'ZoneTypeHomeId': 'Home',
                                        'ZoneTypeOfficeId': 'Office',
                                        'ZoneTypeCustomerZoneTypeId': 'Customer Zone'
                                    }
                                    zone_type_names.append(type_name_map.get(zt, zt))
                            zone_types = ', '.join(zone_type_names) if zone_type_names else ''
                            
                            matched_count += 1
                            break

            # Build destination string
            destination = customer_name if customer_name else ''
            origin = ''
            
            # Convert distance from meters to km
            distance_km = trip.get('distance', 0) / 1000
            
            trip_list.append({
                'Device': device_name,
                'Device Group': device_groups,
                'DriverId': driver_id,
                'First Name': first_name,
                'Last Name': last_name,
                'Driver': driver_email,
                'Driver Group': driver_groups,
                'Start Date': trip.get('start', ''),
                'Driving Duration': trip.get('drivingDuration', ''),
                'Stop Date': trip.get('stop', ''),
                'Distance': distance_km,
                'Stop Duration': trip.get('stopDuration', ''),
                'Origin': origin,
                'Destination': destination,
                'Stop Zone Types': zone_types,
                'Idling Duration': trip.get('idlingDuration', '')
            })
        
        # Convert to DataFrame
        trips_df = pd.DataFrame(trip_list)
        
        print(f"\n⚡ Performance Stats:")
        print(f"   Bounding box checks skipped: {bbox_skipped:,}")
        print(f"   Customer zones matched: {matched_count:,}")
        
        # Filter for Customer Zone stops and OSS driver groups
        print(f"\n📋 Filtering trips...")
        print(f"   Before filtering: {len(trips_df)} trips")
        
        # Filter for Stop Zone Types containing "Customer Zone"
        trips_df = trips_df[trips_df['Stop Zone Types'].str.contains('Customer Zone', case=False, na=False)].copy()
        print(f"   After Customer Zone filter: {len(trips_df)} trips")
        
        # Filter for Device Groups containing "OSS"
        trips_df = trips_df[trips_df['Device Group'].str.contains('OSS', case=False, na=False)].copy()
        print(f"   After OSS Device Group filter: {len(trips_df)} trips")
        
        # Save to CSV
        trips_output = 'data/oss_trips.csv'
        trips_df.to_csv(trips_output, index=False)
        print(f"\n💾 Saved {len(trips_df)} filtered trips to {trips_output}\n")
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ OSS Trips (filtered): {len(trips_df)}")
        print(f"   - Unique devices: {trips_df['Device'].nunique()}")
        print(f"   - Unique drivers: {trips_df['Driver'].nunique()}")
        print(f"   - Unique destinations: {trips_df['Destination'].nunique()}")
        print(f"   - Total distance: {trips_df['Distance'].sum():.2f} km")
        
        return trips_df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    fetch_oss_trips()
