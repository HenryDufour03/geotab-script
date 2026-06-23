# Setup Guide for Trip Data Combiner

## Prerequisites

### 1. Install Python
- Download and install Python 3.8 or newer from [python.org](https://www.python.org/downloads/)
- During installation, **check the box** that says "Add Python to PATH"

### 2. Install Required Packages
Open Command Prompt or PowerShell and run:
```bash
pip install -r requirements.txt
```

Or install packages individually:
```bash
pip install pandas openpyxl
```

## Required Files & Folders

Your project folder should have this structure:
```
GEOTAB/
├── simple_combine_trips.py     ✓ (from GitHub)
├── run_combine_trips.bat       ✓ (from GitHub)
├── requirements.txt            ✓ (from GitHub)
├── trip-data-real/             ← PUT YOUR EXCEL FILES HERE
│   ├── 05.26.xlsx
│   ├── 04.26.xlsx
│   └── ... (all your trip Excel files)
├── example-data/               ← CUSTOMER DATA
│   └── PCU3.csv
└── data/                       ← OUTPUT FOLDER (auto-created)
    └── all_trips_combined.csv  (generated output)
```

### Important Files You Need:

1. **trip-data-real/** folder with Excel trip files (.xlsx)
2. **example-data/PCU3.csv** - Customer matching data

## How to Run

### Option 1: Double-click the batch file
Just double-click `run_combine_trips.bat`

### Option 2: Run from command line
Open Command Prompt or PowerShell in the project folder and run:
```bash
python simple_combine_trips.py
```

## Output

The combined data will be saved to: **data/all_trips_combined.csv**

## Troubleshooting

**Error: "Python is not recognized"**
- Python not installed or not added to PATH. Reinstall Python and check "Add to PATH"

**Error: "No module named 'pandas'"**
- Packages not installed. Run: `pip install pandas openpyxl`

**Error: "No Excel files found"**
- Make sure your .xlsx files are in the `trip-data-real/` folder

**Error about PCU3.csv**
- Make sure `example-data/PCU3.csv` exists for customer matching
