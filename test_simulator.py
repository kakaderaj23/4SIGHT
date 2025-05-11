import os
import random
from threading import Thread
from pymongo import MongoClient
from datetime import datetime
import time

# Configuration
TEST_DB_NAME = "TestLatheDB"
SIMULATION_DURATION = 10  # minutes per simulation
MATERIALS = ["Mild Steel", "Aluminum", "Wood"]
JOB_TYPES = ["turning", "facing", "threading", "drilling", "boring", "knurling"]

client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))

def run_test_simulation(lathe_id, material, job_type):
    try:
        db = client[TEST_DB_NAME]
        
        # Generate unique job ID
        job_id = f"TEST_{material[:3]}_{job_type[:3]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create test job record
        job_data = {
            'JobID': job_id,
            'JobType': job_type,
            'Material': material,
            'ToolNo': random.randint(1, 10),
            'StartTime': datetime.now(),
            'EstimatedTime': SIMULATION_DURATION,
            'Status': 'Started'
        }
        db.JobDetails.insert_one(job_data)
        
        # Start simulation with test database
        from app.simulator import generate_sensor_data
        generate_sensor_data(
            db=db,
            lathe_id=lathe_id,
            job_id=job_id,
            duration=SIMULATION_DURATION,
            material=material,
            job_type=job_type,
            tool_no=random.randint(1, 10)
        )
        
    except Exception as e:
        print(f"Error in simulation {job_id}: {str(e)}")

if __name__ == "__main__":
    # Clear previous test data
    client.drop_database(TEST_DB_NAME)
    
    # Create test simulations
    simulations = []
    for _ in range(10):
        material = random.choice(MATERIALS)
        job_type = random.choice(JOB_TYPES)
        t = Thread(target=run_test_simulation, args=(1, material, job_type))
        t.start()
        simulations.append(t)
    
    print(f"Generating test data with {len(simulations)} simulations...")
    
    # Wait for all threads to complete
    [t.join() for t in simulations]
    print("Test data generation complete!")
    
    # Verification
    test_db = client[TEST_DB_NAME]
    print("\n=== Verification ===")
    print("Collections:", test_db.list_collection_names())
    print("SensoryData count:", test_db.SensoryData.count_documents({}))
    print("JobDetails count:", test_db.JobDetails.count_documents({}))
