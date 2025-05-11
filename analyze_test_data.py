import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
import os

def analyze_test_data():
    client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
    db = client["TestLatheDB"]
    sensory_data = list(db.SensoryData.find())
    if not sensory_data:
        print("No test data found!")
        return

    df = pd.DataFrame(sensory_data)
    # Ensure timestamps are datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        print("No 'timestamp' column in data!")
        return

    sensor_columns = ['Temperature', 'Vibration', 'RPM', 'Power']

    plt.figure(figsize=(16, 12))
    for i, sensor in enumerate(sensor_columns, 1):
        plt.subplot(2, 2, i)
        sns.lineplot(data=df, x='timestamp', y=sensor, hue='JobID', legend='full')
        plt.title(f'{sensor} over Time by JobID')
        plt.xlabel('Timestamp')
        plt.ylabel(sensor)
        plt.xticks(rotation=45)
        plt.legend(title='JobID', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    analyze_test_data()
