import intake
import sys

try:
    cat = intake.open_catalog("catalogs/era5_intake_catalog.yaml")
    print("Keys found in catalog:", list(cat))
except Exception as e:
    print("Error opening catalog:", e)
