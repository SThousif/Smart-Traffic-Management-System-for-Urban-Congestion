from flask import *
from flask import send_from_directory
from werkzeug.utils import secure_filename
import mysql.connector
import pandas as pd

# Try to connect to MySQL; if it fails, defer connection
db = None
cur = None
try:
    db = mysql.connector.connect(host='localhost',user='root',password='0786',port=3306,database='parkingreservation')
    cur = db.cursor()
    print("✓ MySQL connection established")
except mysql.connector.Error as e:
    print(f"⚠ MySQL connection failed: {e}")
    print("  Database-dependent routes will fail until MySQL is configured.")
    print("  To set up MySQL:")
    print("    1. Start MySQL Server")
    print("    2. Create database: mysql -u root -h localhost < Newdatabase.sql")
    print("    3. Restart this app")
from flask_mail import *
from shutil import copyfile
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Heavy ML / optional imports: guard so the app still starts when packages or model files
# are not installed. Endpoints that need ML should check these symbols and return
# a friendly error if the runtime is not available.
ML_AVAILABLE = True
try:
    from detecto.core import Model
    import cv2
    import torch
    import tempfile
    from ultralytics import YOLO
    from norfair import Detection, Tracker
    import numpy as np
except Exception as e:
    print(f"⚠ Optional ML imports failed: {e}")
    # Mark ML unavailable and set placeholders
    ML_AVAILABLE = False
    Model = None
    cv2 = None
    torch = None
    tempfile = None
    YOLO = None
    Detection = None
    Tracker = None
    import types
    np = types.SimpleNamespace(array=lambda *a, **k: None)

# Import the local show helper only if ML dependencies are present
show = None
if ML_AVAILABLE:
    try:
        from deep_learning import show
    except Exception as e:
        print(f"⚠ Could not import deep_learning.show: {e}")
        show = None

app = Flask(__name__)
app.secret_key="fcb384r23823872380237r89irw78eduwsf78we4y"

# Base directory of this script — use for file paths so running from project root works
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Helper to check if database is available
def ensure_db():
    """Ensure `db` and `cur` are connected. Reconnect if needed."""
    global db, cur
    try:
        if db is None:
            db = mysql.connector.connect(host='localhost', user='root', password='0786', port=3306, database='parkingreservation')
            cur = db.cursor()
            return True
        # mysql.connector connection has is_connected()
        try:
            if hasattr(db, 'is_connected') and not db.is_connected():
                db = mysql.connector.connect(host='localhost', user='root', password='0786', port=3306, database='parkingreservation')
                cur = db.cursor()
        except Exception:
            # fallback: attempt reconnect
            db = mysql.connector.connect(host='localhost', user='root', password='0786', port=3306, database='parkingreservation')
            cur = db.cursor()
        return True
    except mysql.connector.Error:
        db = None
        cur = None
        return False


def db_available():
    return ensure_db()

# home page
@app.route("/")
def index():
    return render_template("index.html")

# admin login page
@app.route("/admin",methods=["POST","GET"])
def admin():
    if request.method=='POST':
        form = request.form
        adminname =  form['adminname']
        password = form['adminpassword']
        if adminname =='admin' and password == 'admin':
            return render_template('adminhome.html',admin=adminname)
        else:
            return render_template('admin.html',msg="invalid Credentials")
    return render_template("admin.html")


# adding parking Details
@app.route("/addparking",methods=["POST","GET"])
def addparking():
    if not db_available():
        return render_template("addparking.html", msg="Database not configured. Please set up MySQL first.")
    if request.method=="POST":
        form = request.form
        form1= request.files
        parkingslot = form['parkingslot']
        Cost = form['Cost']
        address = request.form['address']
        nameofimage = form1['nameofimage']
        # imagename = nameofimage.filename
        nameofimage.save(f'static/projectimages/{secure_filename(nameofimage.filename)}')
        sql="insert into parkingslots(parkingslot,Cost,Address,Imagename)values(%s,%s,%s,%s)"
        val = (parkingslot, Cost, address, nameofimage.filename)
        cur.execute(sql, val)
        db.commit()
    return render_template("addparking.html")

# customer login
@app.route("/customer",methods=["POST","GET"])
def customer():
    if not db_available():
        return render_template("customer.html", msg="Database not configured. Please set up MySQL first.")
    if request.method=="POST":
        form = request.form
        customeremail = form['customeremail']
        customerpassword = form['customerpassword']
        sql="select * from customerreg where customeremail='%s' and customerpassword='%s'"%(customeremail,customerpassword)
        cur.execute(sql)
        dc = cur.fetchall()
        if dc !=[]:
            session['useremail']=customeremail
            # if the user was in the middle of reserving a slot, return them to that reserve page
            c = session.get('c')
            if c:
                return redirect(url_for('reserveslot', c=c))
            return redirect('customerhome')
        else:
            return render_template("customer.html",msg="invalid Credentials")

    return render_template("customer.html")

@app.route("/customerhome",methods=["POST","GET"])
def customerhome():
    return render_template("customerhome.html")



# customerreg
@app.route("/customerreg",methods=["POST","GET"])
def customerreg():
    if not db_available():
        return render_template("customerreg.html", msg="Database not configured. Please set up MySQL first.")
    if request.method=="POST":
        form = request.form
        customername = form['customername']
        customeremail = form['customeremail']
        customerpassword = form['customerpassword']
        confirmpassword = form['confirmpassword']
        customercontact = form['customercontact']
        customeraddress = form['customeraddress']
        if customerpassword == confirmpassword:
            sql="select * from customerreg where customeremail='%s' and customerpassword='%s'"%(customeremail,customerpassword)
            cur.execute(sql)
            d = cur.fetchall()
            if d ==[]:
                sql="insert into customerreg(customername,customeremail,customerpassword,customercontact,customeraddress)values(%s,%s,%s,%s,%s)"
                val=(customername,customeremail,customerpassword,customercontact,customeraddress)
                cur.execute(sql,val)
                db.commit()
                return render_template("customer.html")
            else:
                return render_template("customerreg.html",msg="Password not matched")
        else:
            return render_template("customerreg.html",msg="Password not matched")

    return render_template("customerreg.html")


# Parking details for user

@app.route('/view_parking')
def view_parking():
    if not db_available():
        return render_template("viewparking.html", msg="Database not configured. Please set up MySQL first.")
    sql="select * from parkingslots"
    data = pd.read_sql_query(sql,db)
    return render_template("viewparking.html",cols=data.columns.values,rows=data.astype(str).values.tolist())


@app.route("/reserveslot/<c>")
def reserveslot(c=0):
    if not db_available():
        return render_template("reserveslot.html", msg="Database not configured. Please set up MySQL first.")
    session['c'] = c
    sql = "select * from parkingslots where parkingslot='%s'"%(c)
    cur.execute(sql)
    dc = cur.fetchall()[0]
    return render_template("reserveslot.html",dc=dc)

@app.route("/bookslot",methods=["POST","GET"])
def bookslot():
    if not db_available():
        return render_template("reserveslot.html", msg="Database not configured. Please set up MySQL first.")
    c =session['c']
    # print(c,'uvsfbsfinsadfinsafiuwbfiuasdfbwsdiufbsiufbiusdb')
    # print("123456789")
    sql = "select * from parkingslots where parkingslot='%s'"%(c)
    cur.execute(sql)
    dc = cur.fetchall()[0]
    if request.method=="POST":
        # Debug: record incoming form and session to a file for diagnosis
        try:
            import json
            debug = {'form': dict(request.form), 'session': dict(session)}
            open('last_booking_debug.json', 'w', encoding='utf-8').write(json.dumps(debug))
        except Exception as _:
            pass
        # Require user to be logged in
        if 'useremail' not in session:
            # redirect to login so the user can return and submit after logging in
            return redirect(url_for('customer'))
        # print('0000000000000000000000000000000000000000000000')
        c = session['c']
        slotid = request.form['slotid']
        hourcost = int(request.form['hourcost'])
        nameoncard = request.form['nameoncard']
        cvv = request.form['cvv']
        expiredate = request.form['expiredate']
        totalhours = int(request.form['totalhours'])
        totalamount = request.form['totalamount']

        total_amount = int(hourcost)*int(totalhours)
        status = 'locked'
        # Check whether this specific slot is already booked (locked or accepted)
        try:
            cur.execute("select id from bookslot where slotid=%s and status in ('locked','accepted')", (slotid,))
            existing = cur.fetchone()
        except Exception:
            existing = None

        if existing:
            # Slot already booked
            return render_template("reserveslot.html", dc=dc, msg="That slot is already booked")

        # Insert booking
        sql="insert into bookslot(slotid,hourcost,nameoncard,cvv,expiredate,totalhours,totalamount,status,useremail)values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        val = (slotid,hourcost,nameoncard,cvv,expiredate,totalhours,total_amount,status,session['useremail'])
        cur.execute(sql,val)
        db.commit()
        try:
            with open('last_booking_debug.json', 'r', encoding='utf-8') as f:
                d = f.read()
        except Exception:
            d = ''
        try:
            import json
            extra = {'inserted': True, 'last_debug': d, 'lastrowid': cur.lastrowid}
            open('last_booking_debug.json', 'w', encoding='utf-8').write(json.dumps({**debug, **extra}))
        except Exception:
            pass
        cur.execute("update parkingslots set status='locked' where parkingslot=%s", (c,))
        db.commit()
        return redirect(url_for('booking_submitted'))
    return render_template("reserveslot.html",dc=dc)


@app.route("/userbookedslots")
def userbookedslots():
    if not db_available():
        return render_template("userbookedslots.html", msg="Database not configured. Please set up MySQL first.")
    # Show both pending (locked) and accepted bookings so admin can review
    sql="select id,slotid,hourcost,nameoncard,totalhours,totalamount,status,useremail from bookslot where status in ('locked','accepted')"
    data=pd.read_sql_query(sql,db)
    # Ensure all values are strings to avoid rendering issues in templates
    return render_template("userbookedslots.html",cols=data.columns.values,rows=data.astype(str).values.tolist())


@app.route("/acceptrequest/<x>")
def acceptrequest(x=0):
    if not db_available():
        return render_template("userbookedslots.html", msg="Database not configured. Please set up MySQL first.")
    sender_address = 'sannidhinc.2003@gmail.com'
    sender_pass = 'ssyghhuvrmoplcer'
    content = "Your Request Is Accepted by the Admin, You Can Login Now"
    # Determine receiver email: prefer session, otherwise lookup from booking record
    receiver_address = session.get('useremail')
    if not receiver_address:
        try:
            sql_lookup = "select useremail from bookslot where id=%s"
            cur.execute(sql_lookup, (x,))
            res = cur.fetchone()
            if res:
                receiver_address = res[0]
        except Exception:
            receiver_address = None

    # Send email only if we have an address
    if receiver_address:
        try:
            message = MIMEMultipart()
            message['From'] = sender_address
            message['To'] = receiver_address
            message['Subject'] = "Online Parking Reservation System"
            message.attach(MIMEText(content, 'plain'))
            ss = smtplib.SMTP('smtp.gmail.com', 587)
            ss.starttls()
            ss.login(sender_address, sender_pass)
            text = message.as_string()
            ss.sendmail(sender_address, receiver_address, text)
            ss.quit()
        except Exception:
            # Don't fail the request just because email send failed
            pass

    sql="update bookslot set status='accepted' where id=%s"
    cur.execute(sql, (x,))
    db.commit()
    return redirect(url_for('userbookedslots'))

@app.route("/viewresponse")
def viewresponse():
    if not db_available():
        return render_template("viewresponse.html", msg="Database not configured. Please set up MySQL first.")
    # require login to view your accepted bookings
    if 'useremail' not in session:
        return redirect(url_for('customer'))
    sql = "select slotid,hourcost,totalhours,totalamount,status,useremail from bookslot where status='accepted' and useremail=%s"
    data = pd.read_sql_query(sql, db, params=(session['useremail'],))
    return render_template("viewresponse.html",cols=data.columns.values,rows=data.astype(str).values.tolist())


@app.route('/booking_submitted')
def booking_submitted():
    if not db_available():
        return render_template("booking_submitted.html", msg="Database not configured. Please set up MySQL first.")
    if 'useremail' not in session:
        return redirect(url_for('customer'))
    sql = "select id,slotid,hourcost,totalhours,totalamount,status from bookslot where useremail=%s"
    data = pd.read_sql_query(sql, db, params=(session['useremail'],))
    return render_template("booking_submitted.html", cols=data.columns.values, rows=data.astype(str).values.tolist())


# Debug route to show current session user and accepted bookings (temporary)
@app.route('/debug_session')
def debug_session():
    if not db_available():
        return jsonify({'error':'Database not configured'})
    user = session.get('useremail')
    try:
        sql = "select slotid,hourcost,totalhours,totalamount,status,useremail from bookslot where status='accepted' and useremail='%s'"% (user if user else '')
        data = pd.read_sql_query(sql, db)
        rows = data.astype(str).values.tolist()
    except Exception as e:
        return jsonify({'user': user, 'error': str(e)})
    return jsonify({'user': user, 'accepted_bookings': rows})


@app.route("/rejectrequest/<x>")
def rejectrequest(x=0):
    if not db_available():
        return render_template("userbookedslots.html", msg="Database not configured. Please set up MySQL first.")
    sender_address = 'sannidhinc.2003@gmail.com'
    sender_pass = 'ssyghhuvrmoplcer'
    content = "Your Request Is Rejected by the Admin because of no parking slots reservation"
    receiver_address = session.get('useremail')
    if not receiver_address:
        try:
            sql_lookup = "select useremail, slotid from bookslot where id=%s"
            cur.execute(sql_lookup, (x,))
            res = cur.fetchone()
            if res:
                receiver_address = res[0]
                slotid_lookup = res[1]
            else:
                slotid_lookup = None
        except Exception:
            receiver_address = None
            slotid_lookup = None

    if receiver_address:
        try:
            message = MIMEMultipart()
            message['From'] = sender_address
            message['To'] = receiver_address
            message['Subject'] = "Online Parking Reservation System"
            message.attach(MIMEText(content, 'plain'))
            ss = smtplib.SMTP('smtp.gmail.com', 587)
            ss.starttls()
            ss.login(sender_address, sender_pass)
            text = message.as_string()
            ss.sendmail(sender_address, receiver_address, text)
            ss.quit()
        except Exception:
            pass

    sql="update bookslot set status='rejected' where id=%s"
    cur.execute(sql, (x,))
    db.commit()
    # If we have the slotid, unlock that parking slot; otherwise try to unlock by bookslot's slotid
    try:
        if slotid_lookup:
            cur.execute("update parkingslots set status='unlocked' where parkingslot=%s", (slotid_lookup,))
        else:
            # fallback: find slotid for this booking id and unlock
            cur.execute("select slotid from bookslot where id=%s", (x,))
            r = cur.fetchone()
            if r:
                cur.execute("update parkingslots set status='unlocked' where parkingslot=%s", (r[0],))
        db.commit()
    except Exception:
        pass
    return redirect(url_for('userbookedslots'))


@app.route("/unlock_slot/<slotid>")
def unlock_slot(slotid=None):
    if not db_available():
        return render_template("userbookedslots.html", msg="Database not configured. Please set up MySQL first.")
    try:
        cur.execute("update parkingslots set status='unlocked' where parkingslot=%s", (slotid,))
        db.commit()
    except Exception:
        pass
    return redirect(url_for('userbookedslots'))


@app.route("/lock_slot/<slotid>")
def lock_slot(slotid=None):
    if not db_available():
        return render_template("userbookedslots.html", msg="Database not configured. Please set up MySQL first.")
    try:
        cur.execute("update parkingslots set status='locked' where parkingslot=%s", (slotid,))
        db.commit()
    except Exception:
        pass
    return redirect(url_for('userbookedslots'))

@app.route("/prediction",methods=["POST","GET"])
def prediction():
    if request.method == 'POST':
        video = request.files["upload"]
        file = open("video.mp4", 'wb')
        file.write(video.read())
        file.close()
        print("Working")
        # Ensure ML runtime and helper are available
        if not ML_AVAILABLE or show is None or Model is None:
            return render_template("prediction.html", msg="ML runtime not available on server.")
        model = Model.load('Objmodel1.h5', ['occupied', 'unoccupied'])
        # call the helper which now expects (model, input_file, output_file)
        show.detect(model, 'video.mp4', 'output.avi')
        copyfile('output.avi', 'static/video/output.avi')
        return redirect('/static/video/output.avi')
    return render_template("prediction.html")



from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import pandas as pd
import joblib
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns
from sklearn.preprocessing import LabelEncoder
import numpy as np
import random
from flask import jsonify
from statsmodels.tsa.statespace.sarimax import SARIMAX

try:
    sarima_path = os.path.join(BASE_DIR, 'sarima_model_3h.pkl')
    sarima_fit = joblib.load(sarima_path)
except Exception as e:
    print(f"⚠ SARIMA model load failed: {e}")
    sarima_fit = None
# Define a mapping for days of the week
day_of_week_mapping = {
    'Monday': 0,
    'Tuesday': 1,
    'Wednesday': 2,
    'Thursday': 3,
    'Friday': 4,
    'Saturday': 5,
    'Sunday': 6
}
bcrypt = Bcrypt(app)



# Load and preprocess data
data_path = os.path.join(BASE_DIR, 'TrafficTwoMonth.csv')
data = pd.read_csv(data_path)  # Replace with your actual data file path
# Convert Date and Time to datetime
data['Time'] = pd.to_datetime(data['Time'], format='%I:%M:%S %p').dt.time
# Encode categorical variables
label_encoder = LabelEncoder()
data['Day of the week'] = label_encoder.fit_transform(data['Day of the week'])
data['Traffic Situation'] = label_encoder.fit_transform(data['Traffic Situation'])
# Drop any remaining non-numeric columns if any
data = data.select_dtypes(include=[np.number])
data=data.drop(["Date","Total"],axis=1)
print(data.columns)
# Define features and target variable
X = data.drop(['Traffic Situation'], axis=1)
y = data['Traffic Situation']
feature_names = X.columns.tolist()

# Apply SMOTE to balance the dataset
smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X, y)

# Normalize the resampled features
scaler = StandardScaler()  # or MinMaxScaler()
X_resampled_normalized = scaler.fit_transform(X_resampled)

# Split the balanced and normalized dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_resampled_normalized, y_resampled, test_size=0.2, random_state=42)

# Initialize and train the Decision Tree Classifier
decision_tree = DecisionTreeClassifier()
# Ensure that the model is trained with DataFrames having feature names
X_train_df = pd.DataFrame(X_train, columns=feature_names)
decision_tree.fit(X_train_df, y_train)




@app.route('/predict1', methods=['GET', 'POST'])
def predict1():
    if request.method == 'POST':
        forecast_hours = int(request.form.get('forecast_hours', 24))

        print(f"Starting forecast for {forecast_hours} hours.")
        # Load the data
        file_path = os.path.join(BASE_DIR, 'traffic.csv')
        data = pd.read_csv(file_path)

        # Parse the DateTime column to datetime objects and set it as the index
        data['DateTime'] = pd.to_datetime(data['DateTime'])
        data.set_index('DateTime', inplace=True)

        # Downsample the data to hourly frequency (use lowercase 'h' to avoid pandas frequency parsing errors)
        data_3h = data.resample('h').sum()

        # Select the 'Vehicles' column for forecasting
        if 'Vehicles' not in data_3h.columns:
            return "Error: 'Vehicles' column not found in the dataset."

        series = data_3h['Vehicles']

        # # Define and fit the SARIMA model on the selected column
        # sarima_model = SARIMAX(series, 
        #                        order=(1, 1, 1), 
        #                        seasonal_order=(1, 1, 1, 24)) 
        # sarima_fit = sarima_model.fit(disp=False)
        sarima_model = SARIMAX(series, 
                               order=(1, 1, 1), 
                               seasonal_order=(1, 0, 0, 24))  # Simplified seasonal order
        sarima_fit = sarima_model.fit(disp=False, maxiter=50) 

        # Forecast
        steps = forecast_hours
        arima_forecast = sarima_fit.forecast(steps=steps)

        decimal_places = 0
        arima_forecast = [str(round(i, decimal_places)) for i in arima_forecast]

        time_list = {
            "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
            "9": 9, "10": 10, "11": 11, "12": 12, "13": 13, "14": 14, "15": 15, "16": 16,
            "17": 17, "18": 18, "19": 19, "20": 20, "21": 21, "22": 22, "23": 23, "24": 24
        }

        time = time_list.get(str(forecast_hours), 0)
        print(time)
        print(f"SARIMA Forecast for next {forecast_hours} hours:\n{arima_forecast}\n")

        return render_template('predict1.html', forecast=f'Forecasting Completed for {forecast_hours} hours', arima_forecast=arima_forecast, time=time)
    return render_template('predict1.html')

@app.route('/predict2', methods=['GET', 'POST'])
def predict2():
    if request.method == 'POST':
        car_count = int(request.form.get('car_count', 0))
        bike_count = int(request.form.get('bike_count', 0))
        bus_count = int(request.form.get('bus_count', 0))
        truck_count = int(request.form.get('truck_count', 0))
        day_of_week = request.form.get('day_of_week', '')

        day_of_week_encoded = day_of_week_mapping[day_of_week]

        # Prepare the input data with the correct order of features
        input_data = {
            'Day of the week': day_of_week_encoded,  # Use mapped value
            'CarCount': car_count,
            'BikeCount': bike_count,
            'BusCount': bus_count,
            'TruckCount': truck_count
        }

        # Create DataFrame with feature names matching the training data
        input_df = pd.DataFrame([input_data])  # Input data needs to be passed as a list of dictionaries
        
        # Ensure the DataFrame columns match the training features
        input_df = input_df[feature_names]  # Select only the columns in feature_names and in the correct order
        
        # Apply the same scaling
        input_df_scaled = scaler.transform(input_df)

        # Convert back to DataFrame to keep feature names
        input_df_scaled = pd.DataFrame(input_df_scaled, columns=feature_names)

        # Predict using the Decision Tree model
        prediction = decision_tree.predict(input_df_scaled)
        print("prediction----", prediction)
        class_name = label_encoder.inverse_transform(prediction)[0]  # Use inverse transform to get original class name
        probabilities = decision_tree.predict_proba(input_df_scaled)[0]
        print("probabilities: ", probabilities)
        return render_template('predict2.html', class_name = class_name, probabilities = probabilities)
    return render_template('predict2.html')




@app.route('/get_traffic/<float:lat>/<float:lon>')
def get_traffic(lat, lon):
    # Randomly select a traffic condition
    traffic_conditions = ['Heavy', 'Low', 'High', 'Normal']
    traffic_condition = random.choice(traffic_conditions)
    
    # Return the selected traffic condition as JSON
    return jsonify({'traffic_condition': traffic_condition})


@app.route('/map_view')
def map_view():
    return render_template('map.html')
# YOLOv5 Model

@app.route("/video", methods=["GET", "POST"])
def video():
    import os, subprocess
    # Start Streamlit app in the background using the virtualenv's streamlit if available
    venv_streamlit = os.path.join('.venv', 'Scripts', 'streamlit.exe')
    if os.path.exists(venv_streamlit):
        subprocess.Popen([venv_streamlit, 'run', 'streamlit_app.py'], cwd=os.getcwd())
    else:
        # Fallback to system streamlit if virtualenv one isn't present
        try:
            subprocess.Popen(['streamlit', 'run', 'streamlit_app.py'], cwd=os.getcwd())
        except Exception:
            pass
    return render_template("video.html")




if __name__ =="__main__":
    app.run(debug=True, port=3000)
