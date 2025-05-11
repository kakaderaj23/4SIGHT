# from app import app
# from flask import Flask, render_template, redirect, url_for
# from app.forms import JobForm  # Absolute import
# # OR
# from .forms import JobForm     # Relative import

# from .simulator import start_simulation  # Relative import
# # OR
# from app.simulator import start_simulation  # Absolute import

# from pymongo import MongoClient
# import os
# from datetime import datetime
# from flask import Response
# import json
# import time
# # app = Flask(__name__)
# # app.config.from_pyfile('config.py')

# # MongoDB Connection
# client = MongoClient(os.getenv('MONGO_URI'))

# @app.route('/')
# def dashboard():
#     return render_template('dashboard.html', lathes=range(1,21))

# @app.route('/lathe/<int:lathe_id>', methods=['GET', 'POST'])
# def lathe_detail(lathe_id):
#     form = JobForm()
#     db_name = f'Lathe{lathe_id}'
    
#     if form.validate_on_submit():
#         # Generate Job ID
#         db = client[db_name]
#         last_job = db.JobDetails.find_one(sort=[("_id", -1)])
#         job_id = f"{int(last_job['JobID'])+1:03d}" if last_job else '001'
        
#         # Save Job Details
#         job_data = {
#             'JobID': job_id,
#             'JobType': form.job_type.data,
#             'JobDescription': form.job_description.data,
#             'Material': form.material.data,
#             'ToolNo': form.tool_no.data,
#             'StartTime': datetime.now(),
#             'EstimatedTime': form.estimated_time.data,
#             'OperatorName': form.operator_name.data,
#             'Status': 'Started'
#         }
#         db.JobDetails.insert_one(job_data)
        
#         # Start Simulator
#         start_simulation(lathe_id, job_id, form.estimated_time.data)
        
#         return redirect(url_for('dashboard'))
    
#     return render_template('lathe_detail.html', form=form, lathe_id=lathe_id)


# @app.route('/simulation/status/<int:lathe_id>')
# def simulation_status(lathe_id):
#     def generate():
#         client = MongoClient(os.getenv('MONGO_URI'))
#         db = client[f'Lathe{lathe_id}']
        
#         while True:
#             last_data = db.SensoryData.find_one(
#                 sort=[("_id", -1)]
#             )
#             job_status = db.JobDetails.find_one(
#                 {"Status": "Started"},
#                 sort=[("_id", -1)]
#             )
            
#             if last_data and job_status:
#                 data = {
#                     "temperature": last_data["Temperature"],
#                     "vibration": last_data["Vibration"],
#                     "rpm": last_data["RPM"],
#                     "power": last_data["Power"],
#                     "status": "running"
#                 }
#             else:
#                 data = {"status": "completed"}
            
#             yield f"data: {json.dumps(data)}\n\n"
#             time.sleep(1)
    
#     return Response(generate(), mimetype="text/event-stream")

from app import app  # Use existing app from __init__.py
from flask import Flask, flash, render_template, redirect, url_for, Response, request
from app.forms import JobForm  # Absolute import kept as requested
from app.simulator import start_simulation  # Absolute import
# Add this import at the top
from app.forms import AlertForm  # Absolute import
# OR
from .forms import AlertForm     # Relative import

from pymongo import MongoClient
import os
from datetime import datetime
import json
import time

# Use existing client from __init__.py or create if needed
client = MongoClient(os.getenv('MONGO_URI')) 

@app.route('/')
def dashboard():
    lathe_statuses = []
    on_count = 0
    off_count = 0
    total_lathes = 20

    for lathe_id in range(1, 21):
        db = client[f'Lathe{lathe_id}']
        job = db.JobDetails.find_one({'Status': 'Started'})
        is_on = bool(job)
        lathe_statuses.append({'id': lathe_id, 'is_on': is_on})
        if is_on:
            on_count += 1
        else:
            off_count += 1

    return render_template(
        'dashboard.html',
        lathe_statuses=lathe_statuses,
        total_lathes=total_lathes,
        on_count=on_count,
        off_count=off_count
    )

@app.route('/lathe/<int:lathe_id>', methods=['GET', 'POST'])
def lathe_detail(lathe_id):
    alert_form = AlertForm()
    db = client[f'Lathe{lathe_id}']
    
    if alert_form.validate_on_submit():
        db.Alerts.insert_one({
            "timestamp": datetime.now(),
            "message": alert_form.message.data,
            "status": "active"
        })
        flash('Alert created successfully!', 'success')
        return redirect(url_for('lathe_detail', lathe_id=lathe_id))
    
    current_job = db.JobDetails.find_one({"Status": "Started"})
    sensor_data = db.SensoryData.find_one(sort=[("_id", -1)])
    
    return render_template('lathe_detail.html',
                         lathe_id=lathe_id,
                         current_job=current_job,
                         sensor_data=sensor_data,
                         alert_form=alert_form)

@app.route('/lathe/<int:lathe_id>/add_alert')
def add_alert(lathe_id):
    alert_form = AlertForm()
    return render_template('alert_form.html', 
                         alert_form=alert_form,
                         lathe_id=lathe_id)

@app.route('/lathe/<int:lathe_id>/alerts', methods=['POST'])
def handle_alert(lathe_id):
    alert_form = AlertForm()
    if alert_form.validate_on_submit():
        db = client[f'Lathe{lathe_id}']
        db.Alerts.insert_one({
            "timestamp": datetime.now(),
            "message": alert_form.message.data,
            "status": "active"
        })
        return '''
        <script>
            window.close();
            if(window.opener && !window.opener.closed) {
                window.opener.location.reload();
            }
        </script>
        '''
    return render_template('alert_form.html',
                         alert_form=alert_form,
                         lathe_id=lathe_id)


@app.route('/lathe/<int:lathe_id>/start', methods=['GET', 'POST'])
def start_simulator(lathe_id):
    form = JobForm()
    db = client[f'Lathe{lathe_id}']
    
    if form.validate_on_submit():
        # Handle custom material
        material = form.material.data
        if material == "Custom":
            material = request.form.get("custom_material", "")

        # Generate Job ID
        last_job = db.JobDetails.find_one(sort=[("JobID", -1)])
        job_id = f"{int(last_job['JobID'])+1:03d}" if last_job else '001'

        # Create job record
        job_data = {
            'JobID': job_id,
            'JobType': form.job_type.data,
            'JobDescription': form.job_description.data,
            'Material': material,
            'ToolNo': form.tool_no.data,
            'StartTime': datetime.now(),
            'EstimatedTime': form.estimated_time.data,
            'OperatorName': form.operator_name.data,
            'Status': 'Started'
        }
        db.JobDetails.insert_one(job_data)
        
        # Start simulation with all parameters
        start_simulation(
            lathe_id=lathe_id,
            job_id=job_id,
            duration=form.estimated_time.data,
            material=material,
            job_type=form.job_type.data,
            tool_no=form.tool_no.data
        )
        flash('Simulation started successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('simulator_form.html', 
                         form=form, 
                         lathe_id=lathe_id)

@app.route('/lathe/<int:lathe_id>/jobs')  # ✔️ Correct route
def job_history(lathe_id):
    db = client[f'Lathe{lathe_id}']
    jobs = list(db.JobDetails.find().sort("StartTime", -1))
    return render_template('jobs.html', jobs=jobs, lathe_id=lathe_id)

@app.route('/lathe/<int:lathe_id>/alerts')
def alert_history(lathe_id):
    db = client[f'Lathe{lathe_id}']
    alerts = list(db.Alerts.find().sort("timestamp", -1))
    return render_template('alerts.html', alerts=alerts, lathe_id=lathe_id)

@app.route('/lathe/<int:lathe_id>/status')
def current_status(lathe_id):
    db = client[f'Lathe{lathe_id}']
    current_job = db.JobDetails.find_one({"Status": "Started"})
    sensor_data = db.SensoryData.find_one(sort=[("_id", -1)])
    return render_template('status.html',
                         current_job=current_job,
                         sensor_data=sensor_data,
                         lathe_id=lathe_id)


@app.route('/simulation/status/<int:lathe_id>')
def simulation_status(lathe_id):
    def generate():
        # Use existing client connection
        db = client[f'Lathe{lathe_id}']  
        while True:
            last_data = db.SensoryData.find_one(sort=[("_id", -1)])
            job_status = db.JobDetails.find_one(
                {"Status": "Started"},
                sort=[("JobID", -1)]  # Sort by JobID
            )
            
            data = {"status": "completed"}
            if last_data and job_status:
                data.update({
                    "temperature": last_data["Temperature"],
                    "vibration": last_data["Vibration"],
                    "rpm": last_data["RPM"],
                    "power": last_data["Power"],
                    "status": "running"
                })
            
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype="text/event-stream")
