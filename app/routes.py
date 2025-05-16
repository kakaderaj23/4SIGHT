from app import app
from flask import Flask, flash, render_template, redirect, url_for, Response, request, g
from app.forms import JobForm, AlertForm
from app.simulator import start_simulation
from pymongo import MongoClient
import os
from datetime import datetime
import json
import time
import uuid

def get_collections(machine_id):
    """Get collections for specific machine"""
    machine_num = int(machine_id.split('-')[1])  # Extract numeric part from LATHE-01
    return {
        'jobs': g.db['Jobs'][f'lathe{machine_num}_job_detail'],
        'sensor': g.db['SensorData'][f'lathe{machine_num}_sensory_data'],
        'alerts': g.db['Alerts'][f'lathe{machine_num}_alerts']
    }

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = MongoClient(os.getenv('MONGO_URI'))
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    if 'db' in g:
        g.db.close()

@app.route('/')
def dashboard():
    db = get_db()
    active_machines = []
    
    # Check each lathe's job collection
    for machine_num in range(1, 21):
        collection = db['Jobs'][f'lathe{machine_num}_job_detail']
        if collection.find_one({"status": "ongoing"}):
            active_machines.append(f"LATHE-{machine_num:02d}")

    total_lathes = 20
    on_count = len(active_machines)
    off_count = total_lathes - on_count

    lathe_statuses = [{
        'id': f"LATHE-{num:02d}",
        'is_on': f"LATHE-{num:02d}" in active_machines
    } for num in range(1, 21)]

    return render_template(
        'dashboard.html',
        lathe_statuses=lathe_statuses,
        total_lathes=total_lathes,
        on_count=on_count,
        off_count=off_count
    )

@app.route('/lathe/<machine_id>', methods=['GET', 'POST'])
def lathe_detail(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    alert_form = AlertForm()
    
    if alert_form.validate_on_submit():
        collections['alerts'].insert_one({
            "machineId": machine_id,
            "timestamp": datetime.utcnow(),
            "message": alert_form.message.data,
            "status": "active"
        })
        flash('Alert created successfully!', 'success')
        return redirect(url_for('lathe_detail', machine_id=machine_id))
    
    current_job = collections['jobs'].find_one({"status": "ongoing"})
    sensor_data = collections['sensor'].find_one(sort=[("timestamp", -1)])
    
    return render_template('lathe_detail.html',
                         machine_id=machine_id,
                         current_job=current_job,
                         sensor_data=sensor_data,
                         alert_form=alert_form)

@app.route('/lathe/<machine_id>/start', methods=['GET', 'POST'])
def start_simulator(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    form = JobForm()
    
    if form.validate_on_submit():
        job_id = str(uuid.uuid4())
        job_data = {
            "_id": job_id,
            "machineId": machine_id,
            "operatorId": form.operator_name.data,
            "jobId": job_id,
            "jobType": form.job_type.data,
            "jobDescription": form.job_description.data,
            "startTime": datetime.utcnow(),
            "status": "ongoing",
            "estimatedTime": form.estimated_time.data,
            "actualDuration": 0
        }
        
        collections['jobs'].insert_one(job_data)
        start_simulation(
            machine_id=machine_id,
            job_id=job_id,
            duration=form.estimated_time.data,
            material=form.material.data,
            job_type=form.job_type.data,
            tool_no=form.tool_no.data
        )
        flash('Simulation started successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('simulator_form.html', 
                         form=form, 
                         machine_id=machine_id)

@app.route('/lathe/<machine_id>/jobs')
def job_history(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    jobs = list(collections['jobs'].find(sort=[("startTime", -1)]))
    return render_template('jobs.html', jobs=jobs, machine_id=machine_id)

@app.route('/lathe/<machine_id>/alerts')
def alert_history(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    alerts = list(collections['alerts'].find(sort=[("timestamp", -1)]))
    return render_template('alerts.html', alerts=alerts, machine_id=machine_id)

@app.route('/lathe/<machine_id>/status')
def current_status(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    current_job = collections['jobs'].find_one({"status": "ongoing"})
    sensor_data = collections['sensor'].find_one(sort=[("timestamp", -1)])
    
    return render_template('status.html',
                         current_job=current_job,
                         sensor_data=sensor_data,
                         machine_id=machine_id)

@app.route('/simulation/status/<machine_id>')
def simulation_status(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    
    def generate():
        while True:
            last_data = collections['sensor'].find_one(sort=[("timestamp", -1)])
            current_job = collections['jobs'].find_one({"status": "ongoing"})
            
            data = {"status": "completed"}
            if last_data and current_job:
                data.update({
                    "temperature": last_data.get("temperature", 0),
                    "vibration": last_data.get("vibration", 0),
                    "rpm": last_data.get("rpm", 0),
                    "powerConsumption": last_data.get("powerConsumption", 0),
                    "status": "running"
                })
            
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/lathe/<machine_id>/add_alert', methods=['GET'])
def add_alert(machine_id):
    alert_form = AlertForm()
    return render_template('alert_form.html',
                         alert_form=alert_form,
                         machine_id=machine_id)

@app.route('/lathe/<machine_id>/alerts', methods=['POST'])
def handle_alert(machine_id):
    db = get_db()
    collections = get_collections(machine_id)
    alert_form = AlertForm()
    
    if alert_form.validate_on_submit():
        collections['alerts'].insert_one({
            "machineId": machine_id,
            "timestamp": datetime.utcnow(),
            "alertType": "General",
            "severity": 3,
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
                         machine_id=machine_id)
