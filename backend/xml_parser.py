import xml.etree.ElementTree as ET
import pandas as pd
import os

# Paths for processed data
PROCESSED_DIR = 'processed_data'
os.makedirs(PROCESSED_DIR, exist_ok=True)
RECORDS_CSV = os.path.join(PROCESSED_DIR, 'max_records.csv')
WORKOUTS_CSV = os.path.join(PROCESSED_DIR, 'workouts.csv')

def parse_and_summarize(xml_file_path):
    """
    Parses the XML file and saves to CSVs. Returns simple stats.
    """
    # 1. Parse Records (Simplified for MVP - focusing on HeartRate and Mass)
    records = []
    
    context = ET.iterparse(xml_file_path, events=("end",))
    
    # We will limit what we keep in memory or write to CSV to keep it fast
    # For a full app, we'd stream to CSV directly like the original script.
    # Here, let's stick to the streaming to CSV approach to handle large files.
    
    with open(RECORDS_CSV, 'w') as f:
        f.write("type,date,value,unit\n") # Header
        
        for event, elem in context:
            if elem.tag == 'Record':
                record_type = elem.attrib.get('type')
                if record_type in ["HKQuantityTypeIdentifierHeartRate", "HKQuantityTypeIdentifierBodyMass"]:
                    date = elem.attrib.get('startDate')
                    value = elem.attrib.get('value')
                    unit = elem.attrib.get('unit')
                    f.write(f"{record_type},{date},{value},{unit}\n")
                
                elem.clear()
            
            elif elem.tag == 'Workout':
                # Handle workouts separately or in a second pass/check
                pass

    # 2. Parse Workouts (if needed, or do it in the same pass)
    # For simplicity, let's do a quick separate pass or just handle it if we see it.
    # The structure suggests Workouts might be siblings or children depending on export version.
    # Let's do a dedicated pass for Workouts to be safe and clean.
    
    workouts = []
    context = ET.iterparse(xml_file_path, events=("end",))
    for event, elem in context:
        if elem.tag == 'Workout':
            w_type = elem.attrib.get('workoutActivityType')
            duration = elem.attrib.get('duration') # usually mins or secs
            date = elem.attrib.get('startDate')
            kcal = elem.attrib.get('totalEnergyBurned')
            
            workouts.append({
                'type': w_type,
                'duration': duration,
                'date': date,
                'calories': kcal
            })
            elem.clear()
            
    workouts_df = pd.DataFrame(workouts)
    if not workouts_df.empty:
        workouts_df.to_csv(WORKOUTS_CSV, index=False)
        
    return {
        'records_processed': 'See CSV', 
        'workouts_found': len(workouts)
    }

def get_latest_metrics():
    """
    Reads the processed CSVs and returns JSON for the frontend.
    """
    data = {}
    
    # Heart Rate
    if os.path.exists(RECORDS_CSV):
        df = pd.read_csv(RECORDS_CSV)
        
        # Filter for Heart Rate
        hr_df = df[df['type'] == 'HKQuantityTypeIdentifierHeartRate'].copy()
        if not hr_df.empty:
            hr_df['date'] = pd.to_datetime(hr_df['date'])
            # Resample to daily average
            daily_hr = hr_df.set_index('date').resample('D')['value'].mean().reset_index()
            daily_hr['value'] = daily_hr['value'].round(1)
            # Format for Recharts: { date: 'YYYY-MM-DD', value: 72 }
            daily_hr['date_str'] = daily_hr['date'].dt.strftime('%Y-%m-%d')
            data['heartRate'] = daily_hr[['date_str', 'value']].rename(columns={'date_str': 'date'}).to_dict(orient='records')
            
        # Body Mass
        weight_df = df[df['type'] == 'HKQuantityTypeIdentifierBodyMass'].copy()
        if not weight_df.empty:
            weight_df['date'] = pd.to_datetime(weight_df['date'])
            daily_weight = weight_df.set_index('date').resample('D')['value'].mean().reset_index()
            daily_weight['value'] = daily_weight['value'].round(1)
            daily_weight['date_str'] = daily_weight['date'].dt.strftime('%Y-%m-%d')
            data['weight'] = daily_weight[['date_str', 'value']].rename(columns={'date_str': 'date'}).to_dict(orient='records')

    # Workouts
    if os.path.exists(WORKOUTS_CSV):
        w_df = pd.read_csv(WORKOUTS_CSV)
        if not w_df.empty:
            # Count by type
            counts = w_df['type'].value_counts().reset_index()
            counts.columns = ['name', 'value'] # Recharts format
            # Clean names
            counts['name'] = counts['name'].apply(lambda x: x.replace('HKWorkoutActivityType', ''))
            data['workouts'] = counts.to_dict(orient='records')

    return data
