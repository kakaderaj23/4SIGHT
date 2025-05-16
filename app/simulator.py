from threading import Thread
from pymongo import MongoClient
import random
import time
import os
from datetime import datetime

# Material properties database (typical values)
MATERIAL_PROFILES = {
    'Mild Steel': {
        'hardness': 120,  # HB
        'thermal_conductivity': 50,  # W/m-K
        'specific_heat': 460  # J/kg-K
    },
    'Aluminum': {
        'hardness': 35,
        'thermal_conductivity': 237,
        'specific_heat': 900
    },
    'Wood': {
        'hardness': 2,
        'thermal_conductivity': 0.12,
        'specific_heat': 1700
    }
}

TOOL_WEAR_RATES = {
    'Mild Steel': 0.15,  # % per minute
    'Aluminum': 0.08,
    'Wood': 0.02
}

def calculate_machine_parameters(material, job_type, tool_diameter):
    """Calculate base parameters based on material and operation"""
    base_rpm = {
        'Mild Steel': random.randint(800, 1200),
        'Aluminum': random.randint(1500, 2500),
        'Wood': random.randint(2800, 3500)
    }[material]

    base_power = {
        'turning': 3.5,
        'facing': 4.0,
        'threading': 2.8,
        'drilling': 5.0,
        'boring': 3.0,
        'knurling': 2.5
    }[job_type] * (tool_diameter/10)  # kW/mm

    return base_rpm, base_power

def generate_sensor_data(machine_id, job_id, duration, material, job_type, tool_no):
    client = None
    try:
        client = MongoClient(os.getenv('MONGO_URI'))
        
        # Extract machine number from ID (e.g., "LATHE-01" -> 1)
        machine_number = int(machine_id.split('-')[1])
        
        # Get collection references
        jobs_collection = client['Jobs'][f'lathe{machine_number}_job_detail']
        sensor_collection = client['SensorData'][f'lathe{machine_number}_sensory_data']

        # Calculate initial parameters
        tool_diameter = 10 + tool_no * 2  # mm
        base_rpm, base_power = calculate_machine_parameters(material, job_type, tool_diameter)
        ambient_temp = 25  # Initial ambient temperature
        cooling_efficiency = 0.7  # Cooling system effectiveness

        # Convert duration to seconds and calculate end time
        duration_seconds = duration * 60
        start_time = time.time()
        end_time = start_time + duration_seconds

        # Initialize job document
        jobs_collection.update_one(
            {"_id": job_id},
            {"$set": {
                "machineId": machine_id,
                "jobId": job_id,
                "jobType": job_type,
                "startTime": datetime.utcnow(),
                "status": "ongoing",
                "estimatedTime": duration
            }},
            upsert=True
        )

        # Main simulation loop
        while time.time() < end_time:
            elapsed = (time.time() - start_time) / 60  # minutes
            
            # Tool wear calculation
            tool_wear = min(100, TOOL_WEAR_RATES[material] * elapsed)
            
            # RPM simulation
            current_rpm = base_rpm * (1 - tool_wear/500) * random.normalvariate(1, 0.03)
            
            # Power consumption
            power_factor = 1 + (tool_wear/100) * 0.5
            current_power = base_power * power_factor * random.normalvariate(1, 0.05)
            
            # Temperature modeling
            heat_generation = current_power * 1000 * 0.8
            material_props = MATERIAL_PROFILES[material]
            temp_increase = (heat_generation * elapsed * 60) / \
                          (material_props['specific_heat'] * material_props['hardness'])
            workpiece_temp = ambient_temp + temp_increase * (1 - cooling_efficiency)
            
            # Vibration modeling
            vibration_base = {
                'Mild Steel': 2.5,
                'Aluminum': 1.8,
                'Wood': 0.8
            }[material]
            vibration = vibration_base * (current_rpm/1000) * (1 + tool_wear/50) * random.normalvariate(1, 0.1)

            # Create sensor document
            sensor_data = {
                "machineId": machine_id,
                "jobId": job_id,
                "timestamp": datetime.utcnow(),
                "temperature": max(ambient_temp, min(workpiece_temp + random.gauss(0, 2), 300)),
                "vibration": max(0, vibration),
                "rpm": max(100, current_rpm),
                "powerConsumption": max(0.5, current_power),
                "toolWear": tool_wear
            }
            
            sensor_collection.insert_one(sensor_data)
            
            # Dynamic sleep to prevent overshooting duration
            remaining = end_time - time.time()
            if remaining > 0:
                time.sleep(min(5, remaining))

    except Exception as e:
        print(f"Simulation error: {str(e)}")
        # Update job status to failed
        if client:
            jobs_collection.update_one(
                {"_id": job_id},
                {"$set": {"status": "failed", "error": str(e)}}
            )
    finally:
        # Ensure job completion even if errors occur
        if client:
            try:
                jobs_collection.update_one(
                    {"_id": job_id},
                    {"$set": {
                        "status": "completed",
                        "endTime": datetime.utcnow(),
                        "actualDuration": round(time.time() - start_time, 2)
                    }}
                )
            except Exception as e:
                print(f"Failed to update job status: {str(e)}")
            finally:
                client.close()

def start_simulation(machine_id, job_id, duration, material, job_type, tool_no):
    thread = Thread(target=generate_sensor_data, 
                   args=(machine_id, job_id, duration, material, job_type, tool_no))
    thread.daemon = True  # Allow thread to exit with main program
    thread.start()
