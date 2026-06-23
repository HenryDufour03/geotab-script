# GeoTab Trip Data Processing

Python scripts for fetching and processing GeoTab trip data.

## Setup

1. Install required packages:
```bash
pip install pandas mygeotab python-dotenv openpyxl
```

2. Create a `.env` file with your GeoTab credentials:
```
GEO_DATABASE=your_database
GEO_USER=your_email@company.com
GEO_PASSWORD=your_password
```

## Scripts

- **simple_combine_trips.py** - Combines Excel trip files from `trip-data-real/` folder and merges with customer data from `example-data/PCU3.csv`
- **verify_output.py** - Verification script to check combined data quality
- **fetch_oss_trips.py** - Fetches OSS trip data from GeoTab API (optional)

## Usage

Run the batch file to combine trips:
```bash
run_combine_trips.bat
```

Or run the Python script directly:
```bash
python simple_combine_trips.py
```

## Output

Combined trip data is saved to `data/all_trips_combined.csv`
