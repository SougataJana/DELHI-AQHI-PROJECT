import pandas as pd
import numpy as np
import re

# 1. THE HINGLISH MINING CLASS
class BioSignalMiner:
    def __init__(self):
        # The Hinglish Symptom Dictionary
        self.symptom_lexicon = {
            'RESPIRATORY': [
                'breath', 'breathe', 'breathing', 'asthma', 'wheezing', 'choking', 'cough', 'lungs',
                'saans', 'khasi', 'dam', 'ghutan', 'chest', 'sine', 'nebulizer'
            ],
            'OCULAR': [
                'eye', 'eyes', 'burning', 'watery', 'vision', 'blur', 'blind',
                'aankh', 'jalan', 'sujan', 'laal', 'tears'
            ],
            'GENERAL': [
                'headache', 'dizzy', 'fever', 'nausea', 'vomit', 'sick',
                'sar', 'dard', 'bukhar', 'chakkar', 'ulti', 'tabiyat'
            ]
        }
        # Noise words to ignore
        self.stopwords = set(['the', 'is', 'in', 'hai', 'me', 'ka', 'ko', 'se', 'aur', 'toh'])

    def clean_text(self, text):
        if not isinstance(text, str): return ""
        text = text.lower()
        text = re.sub(r'http\S+|www\S+|@\w+|[^\w\s]', '', text)
        return " ".join([w for w in text.split() if w not in self.stopwords])

    def extract_signal(self, text):
        clean_txt = self.clean_text(text)
        detected = []
        severity = 0
        
        for category, keywords in self.symptom_lexicon.items():
            for word in keywords:
                if word in clean_txt:
                    detected.append(category)
                    severity += 2 # Score increases with keyword matches
                    
        if not detected:
            return "NONE", 0
        
        # Pick most common symptom and cap severity at 10
        primary = max(set(detected), key=detected.count)
        return primary, min(severity + 3, 10)

# 2. THE PIPELINE FUNCTION
def run_pipeline():
    print("STARTING MINING PIPELINE")
    
    # A. LOAD DATA
    try:
        social_df = pd.read_csv("social_data_raw.csv")
        env_df = pd.read_csv("cpcb_raw.csv") # Your converted CPCB file
        print(f" Loaded {len(social_df)} Tweets & {len(env_df)} Environmental Records.")
    except FileNotFoundError:
        print("CRITICAL ERROR: CSV files missing. Run 'social_miner.py' first!")
        return

    # B. PROCESS CPCB DATA (Align Dates)
    # Create a cleaner date column from CPCB data
    env_df['datetime'] = pd.to_datetime(env_df[['Year', 'Month', 'Date']].astype(str).agg('-'.join, axis=1), errors='coerce')
    env_df = env_df.dropna(subset=['datetime'])
    
    # SHIFT CPCB DATA TO DEC 2025 (To match our simulation)
    # We map the day of the month (1st, 2nd..) to Dec 2025 dates
    env_df['day_num'] = env_df['datetime'].dt.day
    env_df['project_date'] = env_df['day_num'].apply(lambda d: pd.Timestamp(f"2025-12-{d:02d}"))
    
    # Clean up Environmental Data
    clean_env = env_df[['project_date', 'AQI', 'PM2.5']].groupby('project_date').mean().reset_index()
    clean_env.columns = ['date', 'official_aqi', 'pm25']

    # C. MINE SOCIAL DATA
    miner = BioSignalMiner()
    print("Mining Bio-Signals from Text (This may take a moment)...")
    
    # Run the miner on every tweet
    social_df['timestamp'] = pd.to_datetime(social_df['timestamp'])
    social_df['date'] = social_df['timestamp'].dt.normalize()
    
    mining_results = social_df['raw_text'].apply(miner.extract_signal)
    
    # Unpack results into columns
    social_df['detected_symptom'] = [x[0] for x in mining_results]
    social_df['severity_score'] = [x[1] for x in mining_results]
    
    # Filter out noise (Keep only relevant posts)
    valid_signals = social_df[social_df['detected_symptom'] != 'NONE'].copy()
    print(f"Extracted {len(valid_signals)} Valid Health Signals.")

    # D. MERGE EVERYTHING
    final_df = pd.merge(valid_signals, clean_env, on='date', how='left')
    
    # Fill missing AQI values (Forward Fill)
    final_df['official_aqi'] = final_df['official_aqi'].fillna(method='ffill').fillna(350)
    
    # E. SAVE
    final_df.to_csv("final_project_data.csv", index=False)
    print("SUCCESS 'final_project_data.csv' created.")

if __name__ == "__main__":
    run_pipeline()
