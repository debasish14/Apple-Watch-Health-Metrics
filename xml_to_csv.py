import xml.etree.ElementTree as ET
import csv
import os

XML_FILE = 'apple_health_export/export.xml'
RECORDS_CSV = 'health_records.csv'
WORKOUTS_CSV = 'workouts.csv'

def xml_to_csv():
    if not os.path.exists(XML_FILE):
        print(f"Error: {XML_FILE} not found.")
        return

    print("Starting XML parsing (this may take a while)...")
    
    # Iterate for Records
    with open(RECORDS_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['type', 'sourceName', 'sourceVersion', 'unit', 'creationDate', 'startDate', 'endDate', 'value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        context = ET.iterparse(XML_FILE, events=("start", "end"))
        context = iter(context)
        event, root = next(context) # Get root

        count = 0
        for event, elem in context:
            if event == "end" and elem.tag == "Record":
                row = {
                    'type': elem.attrib.get('type'),
                    'sourceName': elem.attrib.get('sourceName'),
                    'sourceVersion': elem.attrib.get('sourceVersion'),
                    'unit': elem.attrib.get('unit'),
                    'creationDate': elem.attrib.get('creationDate'),
                    'startDate': elem.attrib.get('startDate'),
                    'endDate': elem.attrib.get('endDate'),
                    'value': elem.attrib.get('value'),
                }
                writer.writerow(row)
                count += 1
                elem.clear() # clear memory
                if count % 100000 == 0:
                    print(f"Processed {count} records...")
                    
    print(f"Finished writing {count} records to {RECORDS_CSV}")

    # Reset for Workouts - simple re-parse for simplicity or could handle both in one pass but they are nested differently sometimes
    # Actually Workouts are usually top level children of HealthData like Records.
    
    # For efficiency, let's try to grab Workouts in the same pass if possible, or just do another pass.
    # Given the file size (~300MB), a second pass is acceptable for simplicity to keep code clean.
    
    print("Extracting Workouts...")
    with open(WORKOUTS_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['workoutActivityType', 'duration', 'durationUnit', 'totalDistance', 'totalDistanceUnit', 
                      'totalEnergyBurned', 'totalEnergyBurnedUnit', 'sourceName', 'startDate', 'endDate']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        context = ET.iterparse(XML_FILE, events=("end",))
        count = 0
        for event, elem in context:
            if elem.tag == "Workout":
                row = {
                    'workoutActivityType': elem.attrib.get('workoutActivityType'),
                    'duration': elem.attrib.get('duration'),
                    'durationUnit': elem.attrib.get('durationUnit'),
                    'totalDistance': elem.attrib.get('totalDistance'),
                    'totalDistanceUnit': elem.attrib.get('totalDistanceUnit'),
                    'totalEnergyBurned': elem.attrib.get('totalEnergyBurned'),
                    'totalEnergyBurnedUnit': elem.attrib.get('totalEnergyBurnedUnit'),
                    'sourceName': elem.attrib.get('sourceName'),
                    'startDate': elem.attrib.get('startDate'),
                    'endDate': elem.attrib.get('endDate'),
                }
                writer.writerow(row)
                count += 1
                elem.clear()
        
    print(f"Finished writing {count} workouts to {WORKOUTS_CSV}")

if __name__ == "__main__":
    xml_to_csv()
