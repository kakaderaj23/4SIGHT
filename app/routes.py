from app import app  # Use existing app from __init__.py
from flask import Flask, flash, render_template, redirect, url_for, Response, request
from app.forms import JobForm  # Absolute import kept as requested
from app.simulator import start_simulation  # Absolute import
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import User, auth_db
from app.forms import LoginForm
from functools import wraps
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

def operator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.userType != 'operator':
            flash("Access denied for non-operators", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.userType != 'manager':
            flash("Access denied for non-managers", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        record = auth_db.users.find_one({"userID": form.userID.data})
        if record and check_password_hash(record['passwordHash'], form.password.data):
            user = User(record['_id'], record['employeeId'], record['userID'], record['userType'])
            login_user(user)
            auth_db.users.update_one({'_id': record['_id']}, {'$set': {'lastLogin': datetime.now()}})
            if user.userType == "manager":
                return redirect(url_for('manager_landing'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/dashboard')
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

@app.route('/manager')
@login_required
@manager_required
def manager_landing():
    return render_template('manager_landing.html')

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
@login_required
@operator_required
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

@app.route('/analytics')
@login_required
@manager_required
def analytics_dashboard():
    lathe_jobs = []
    lathe_rpm = []
    lathe_temp = []
    lathe_power = []

    total_jobs = 0
    active_jobs = 0

    for lathe_id in range(1, 21):
        db = client[f'Lathe{lathe_id}']

        jobs_count = db.JobDetails.count_documents({})
        lathe_jobs.append(jobs_count)
        total_jobs += jobs_count

        active_count = db.JobDetails.count_documents({'Status': 'Started'})
        active_jobs += active_count

        rpm = db.SensoryData.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$RPM"}}}])
        temp = db.SensoryData.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$Temperature"}}}])
        power = db.SensoryData.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$Power"}}}])

        lathe_rpm.append(round(next(rpm, {}).get('avg', 0), 2))
        lathe_temp.append(round(next(temp, {}).get('avg', 0), 2))
        lathe_power.append(round(next(power, {}).get('avg', 0), 2))

    return render_template(
        'analytics_dashboard.html',
        lathe_jobs=lathe_jobs,
        lathe_rpm=lathe_rpm,
        lathe_temp=lathe_temp,
        lathe_power=lathe_power,
        total_jobs=total_jobs,
        active_jobs=active_jobs
    )

@app.route('/home')
@login_required
def home_redirect():
    if current_user.userType == 'manager':
        return redirect(url_for('manager_landing'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
