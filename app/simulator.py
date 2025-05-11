
from threading import Thread
from pymongo import MongoClient
import random
import time
import os
import math
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

# Tool wear parameters
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

def generate_sensor_data(lathe_id, job_id, duration, material, job_type, tool_no):
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client[f'Lathe{lathe_id}']
    
    # Simulation parameters
    start_time = time.time()
    tool_diameter = 10 + tool_no * 2  # mm (example relationship)
    base_rpm, base_power = calculate_machine_parameters(material, job_type, tool_diameter)
    tool_wear = 0
    cooling_efficiency = 0.7  # 0-1 (coolant effectiveness)
    
    # Initial thermal conditions
    ambient_temp = 25
    workpiece_temp = ambient_temp
    
    while time.time() - start_time < duration * 60:
        elapsed = (time.time() - start_time) / 60  # minutes
        
        # Dynamic tool wear simulation
        tool_wear = min(100, TOOL_WEAR_RATES[material] * elapsed)
        
        # RPM variation (±10% with tool wear impact)
        current_rpm = base_rpm * (1 - tool_wear/500) * random.normalvariate(1, 0.03)
        
        # Power consumption (increases with tool wear)
        power_factor = 1 + (tool_wear/100) * 0.5
        current_power = base_power * power_factor * random.normalvariate(1, 0.05)
        
        # Temperature modeling (simplified thermal dynamics)
        heat_generation = current_power * 1000 * 0.8  # 80% of energy converts to heat
        material_props = MATERIAL_PROFILES[material]
        temp_increase = (heat_generation * elapsed * 60) / \
                      (material_props['specific_heat'] * material_props['hardness'])
        workpiece_temp = ambient_temp + temp_increase * (1 - cooling_efficiency)
        
        # Vibration modeling (increases with tool wear and RPM)
        vibration_base = {
            'Mild Steel': 2.5,
            'Aluminum': 1.8,
            'Wood': 0.8
        }[material]
        vibration = vibration_base * (current_rpm/1000) * (1 + tool_wear/50) * random.normalvariate(1, 0.1)
        
        sensor_data = {
            'timestamp': datetime.now(),
            'JobID': job_id,
            'Temperature': max(ambient_temp, min(workpiece_temp + random.gauss(0, 2), 300)),
            'Vibration': max(0, vibration),
            'RPM': max(100, current_rpm),
            'Power': max(0.5, current_power),
            'ToolWear': tool_wear,
            'Material': material,
            'JobType': job_type
        }
        
        db.SensoryData.insert_one(sensor_data)
        time.sleep(5)
    
    # Final status update
    db.JobDetails.update_one(
        {'JobID': job_id},
        {'$set': {'Status': 'Completed', 'FinalToolWear': tool_wear}}
    )

def start_simulation(lathe_id, job_id, duration, material, job_type, tool_no):
    thread = Thread(target=generate_sensor_data, 
                   args=(lathe_id, job_id, duration, material, job_type, tool_no))
    thread.start()

 

# from threading import Thread
# import random
# import time
# from datetime import datetime

# def generate_sensor_data(db, lathe_id, job_id, duration, material, job_type, tool_no):
#     """Generate sensor data using provided database connection"""
#     start_time = time.time()
    
#     try:
#         while time.time() - start_time < duration * 60:
#             # Realistic data generation logic
#             sensor_data = {
#                 'timestamp': datetime.now(),
#                 'JobID': job_id,
#                 'LatheID': lathe_id,
#                 'Material': material,
#                 'JobType': job_type,
#                 'ToolNo': tool_no,
#                 'Temperature': random.uniform(20, 100),
#                 'Vibration': random.uniform(0, 10),
#                 'RPM': random.randint(500, 3000),
#                 'Power': random.uniform(1, 15)
#             }
#             db.SensoryData.insert_one(sensor_data)
#             time.sleep(5)
        
#         # Final update
#         db.JobDetails.update_one(
#             {'JobID': job_id},
#             {'$set': {'Status': 'Completed'}}
#         )
        
#     except Exception as e:
#         print(f"Error in sensor data generation: {str(e)}")

# def start_simulation(db, lathe_id, job_id, duration, material, job_type, tool_no):
#     """Start simulation thread with database context"""
#     thread = Thread(
#         target=generate_sensor_data,
#         args=(db, lathe_id, job_id, duration, material, job_type, tool_no)
#     )
#     thread.start()
