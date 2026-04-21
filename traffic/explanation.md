# Project Overview

This repository implements an "Online Parking Reservation System" with additional traffic/vision utilities and a Streamlit-based traffic video analysis UI. It is designed as a small web application (Flask) backed by a MySQL database and augmented with optional machine-learning components for video / object detection.

Audience: this document explains the project for a fresher or new developer so you can run, understand, and modify the system.

# System Architecture

- Frontend: HTML templates in the `templates/` folder served by Flask routes. Static assets (CSS, JS, images, video) are under `static/`.
- Backend: single Flask app in `app.py` that exposes routes for admin/customer flows, booking/reserving slots, and a `/prediction` endpoint that invokes local ML helpers for video processing.
- Machine Learning (optional): detection code under `deep_learning/` and a Streamlit app (`final.py` / `streamlit_app.py`) that run vision models (Detecto, YOLO) to analyze videos.
- Database: MySQL (database `parkingreservation`) storing parking slots, bookings and customer registrations. SQL schema available in `Newdatabase.sql`.

# Folder Structure (high level)

- `app.py` — Main Flask application and routes (backend).
- `final.py`, `streamlit_app.py` — Streamlit UIs for video/ML features.
- `deep_learning/` — helper code for detection (`show.py`, `car_detection.py`).
- `static/` — CSS, JS, images, videos.
- `templates/` — HTML templates used by Flask (`index.html`, `admin.html`, `customer.html`, etc.).
- `scripts/` — helper scripts for diagnostics and DB operations.
- `requirements.txt` — Python dependencies.
- `Newdatabase.sql` — SQL statements to create the database and tables.

# Core Components (files explained step-by-step)

- `app.py`
  - Entry point for the web server. It creates the Flask app, attempts to connect to MySQL, and defines all routes used by the application (admin/customer login, parking CRUD, booking flow, prediction route, and some utility routes).
  - Key concepts inside `app.py`:
    - Database connection helpers: `ensure_db()` and `db_available()` — reconnect or detect when DB is unavailable.
    - Authentication: very simple session-based login for customers. `session['useremail']` holds the logged-in user.
    - Booking lifecycle: `reserveslot()` → `bookslot()` → booking stored in `bookslot` table with `status` ('locked' initially). Admin routes `acceptrequest()` and `rejectrequest()` change booking `status` and update `parkingslots.status` accordingly.
    - Prediction route: `/prediction` accepts a video upload, saves it to `video.mp4`, loads a detection model, and calls a helper in `deep_learning.show` to run detection and produce an output video.

  - Example: booking insert (simplified)

  ```python
  sql = "insert into bookslot(slotid,hourcost,nameoncard,cvv,expiredate,totalhours,totalamount,status,useremail)values(%s,%s,%s,%s,%s,%s,%s,%s,%s)"
  val = (slotid, hourcost, nameoncard, cvv, expiredate, totalhours, total_amount, status, session['useremail'])
  cur.execute(sql, val)
  db.commit()
  ```

- `deep_learning/show.py`
  - Contains `detect(model, input_file, output_file, ...)` which reads input video frames, runs model predictions, draws bounding boxes, and writes an output video file.
  - The file should not execute heavy code on import; demo code is guarded by `if __name__ == '__main__':` so Flask can import it safely.

- `final.py` and `streamlit_app.py`
  - Streamlit apps that provide a browser-based interface for uploading videos and running detection/tracking pipelines (YOLO/different trackers). They load models (YOLOv5 via `torch.hub` or `ultralytics`) and present visual results and summaries in a web UI.

- `templates/` + `static/`
  - `templates/` contains HTML pages for login, admin, booking, viewing parking slots, prediction page and more. They are rendered by Flask routes via `render_template()`.
  - `static/` holds CSS and JavaScript files used by the templates, and a `video/` folder where processed video outputs are saved.

- `scripts/`
  - Utility scripts (e.g., `diagnose.py`, `check_db.py`) used to inspect DB contents and runtime environment — helpful for debugging and quick verification.

# Database Design

The project uses MySQL with (at least) the following tables (see `Newdatabase.sql`):

- `parkingslots` — stores parking slot metadata (e.g., `parkingslot` id/string, `Cost`, `Address`, `Imagename`, `status` (locked/unlocked)).
- `bookslot` — stores booking records: `id`, `slotid`, `hourcost`, `nameoncard`, `cvv`, `expiredate`, `totalhours`, `totalamount`, `status` (locked/accepted/rejected), `useremail`.
- `customerreg` — stores customer registrations: `customername`, `customeremail`, `customerpassword`, `customercontact`, `customeraddress`.

Typical SQL operations:

- Read parking slots: `SELECT * FROM parkingslots` (used in `/view_parking`).
- Insert booking: insert into `bookslot` and set parking slot `status='locked'`.
- Accept / reject booking: update `bookslot.status` and unlock the parking slot when rejecting.

# Machine Learning Components

This project contains two parallel ML flows:

1. Parking occupancy detection (Detecto):
   - `deep_learning/show.py` uses a Detecto Model (`Objmodel1.h5`) trained to predict `occupied` / `unoccupied` boxes. The `detect()` function iterates video frames, runs `model.predict(...)`, draws boxes, and writes output video.

2. Traffic video analytics (Streamlit + YOLO):
   - `final.py` (Streamlit) loads a YOLO model (via `torch.hub` or `ultralytics`) to detect vehicles, converts detections to `norfair.Detection` objects and tracks them to estimate vehicle counts and provide a clearance-time heuristic.

Notes for maintainers:
- ML code is optional — the Flask app guards imports so the server starts even without ML packages or model files. The `/prediction` route checks `ML_AVAILABLE` and whether `deep_learning.show` imported successfully.
- Large model files are present in the repo (`Objmodel1.h5`, `yolov5s.pt`), so ensure you have disk space and compatible GPU/CPU setup for running them.

# Backend Logic and API Routes (summary)

- `GET /` — `index()` – renders home page.
- `GET|POST /admin` — admin login page.
- `GET|POST /customer` — customer login (sets `session['useremail']`).
- `GET|POST /customerreg` — customer registration.
- `GET /view_parking` — shows all parking slots (reads `parkingslots`).
- `GET /reserveslot/<c>` — page to reserve a specific slot `c`.
- `GET|POST /bookslot` — submit booking form; inserts `bookslot`, sets slot status to `locked`.
- `GET /userbookedslots` — lists bookings for admin review.
- `GET /acceptrequest/<id>` — admin accepts a booking (updates `bookslot.status='accepted'` and optionally sends email).
- `GET /rejectrequest/<id>` — admin rejects and unlocks slot.
- `POST /prediction` — accepts video file, runs ML detection through `deep_learning.show.detect()`, stores the output under `static/video/`, and redirects to the result.

# Frontend Workflow (UI interaction)

1. User lands on the home page (`/`).
2. Customer registers (`/customerreg`) or logs in (`/customer`).
3. Customer views available slots via `/view_parking` and clicks a slot to reserve; they are redirected to `/reserveslot/<slotid>`.
4. On reserve page they submit payment details (note: payment handling is simulated — card fields are saved directly into DB in this demo app).
5. Booking is inserted into `bookslot` with `status='locked'` and the parking slot is also set to locked.
6. Admin reviews bookings at `/userbookedslots` and may accept or reject a booking. Accept sets `status='accepted'`; reject sets `status='rejected'` and unlocks the slot.
7. Customer can view responses at `/viewresponse` (only shows `accepted` bookings for the logged-in user).

# Data Flow — From User Input to Output (sequence)

1. User submits a form (login, registration, booking, upload video).
2. Flask route receives the request; if DB is required, `ensure_db()` reconnects if necessary.
3. Input is validated or used directly to build SQL statements.
4. DB write: `cur.execute(sql, params)` followed by `db.commit()`.
5. For video prediction: uploaded file is saved to disk, model is loaded (`Model.load('Objmodel1.h5', ...)`), `deep_learning.show.detect()` is called to process frames and produce `output.avi`.
6. Output is copied to `static/` and the client is redirected to view the processed video.

# Runtime Flow (start to finish)

1. Start the app: activate virtual environment and run:

```powershell
Set-Location -Path .\traffic
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe app.py
```

2. Flask attempts to connect to MySQL using credentials in `app.py` (`user='root'`, `password='0786'`, database `parkingreservation`). If DB is missing, routes that require DB return a friendly message instructing how to set up the SQL schema using `Newdatabase.sql`.

3. User visits pages and interacts as described in Frontend Workflow; admin and customer flows use simple templated pages.

4. ML endpoints (prediction/video) load models from `Objmodel1.h5` or YOLO weights and perform processing.

# How to Run the Project Locally (step-by-step)

Prerequisites:

- Python 3.10+ (the `requirements.txt` expects modern Python packages). Ensure you have a matching Python version.
- MySQL server running and accessible on `localhost:3306`.
- (Optional) GPU drivers and CUDA if you plan to run Torch/YOLO on GPU.

Install dependencies (recommended inside a virtual environment):

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

Database setup:

1. Start MySQL server.
2. From project root run:

```sql
mysql -u root -p < Newdatabase.sql
-- or run the SQL statements inside Newdatabase.sql with your MySQL client
```

3. (Optional) Insert sample parking slots if table is empty. Example SQL:

```sql
USE parkingreservation;
INSERT INTO parkingslots (parkingslot, Cost, Address, Imagename, status)
VALUES ('A1','40','Near Yehlanka','', 'unlocked');
COMMIT;
```

Run the Flask web server:

```powershell
Set-Location -Path .\traffic
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe app.py
```

Open the main UI in a browser: http://127.0.0.1:3000/

Run the Streamlit app (optional):

```powershell
Set-Location -Path .\traffic
.\.venv\Scripts\Activate.ps1
streamlit run final.py
```

# Sequence-style Explanation (compact)

1. Developer starts server (Flask) from `traffic/app.py`.
2. Flask imports guarded ML modules and attempts DB connection.
3. User visits `/` and uses templates for actions.
4. Booking flow: view slots → reserve → submit booking → DB insert → slot locked.
5. Admin flow: view queued bookings → accept/reject → update booking status and slot status.
6. Prediction flow: user uploads video to `/prediction` → Flask saves file → loads `Objmodel1.h5` → calls `deep_learning.show.detect()` → outputs video saved and served from `static/video/`.

# Important Implementation Notes & Tips

- The app stores sensitive fields (card details) in plain DB columns — **this is only acceptable for a demo**. Do NOT store real credit card details in plaintext in production.
- `app.py` uses string interpolation in some SQL statements (unsafe). Prefer parameterized queries everywhere to avoid SQL injection.
- The ML model loading (`Model.load('Objmodel1.h5', ...)`) may be slow; consider loading the model once on app start and reusing it rather than reloading per request.
- Use a production WSGI server (gunicorn/uvicorn + reverse proxy) for deployment rather than Flask's development server.

# Where to Look Next (developer pointers)

- `templates/` — review the HTML pages to understand what fields are submitted by users.
- `app.py` — primary place to change business logic, session handling, and route behavior.
- `deep_learning/show.py` and `final.py` — modify detection logic and model usage.
- `Newdatabase.sql` — modify table schema or seed data.

# Conclusion

This project is a Flask-based prototype for parking reservation enriched with video analytics. It is structured so a newcomer can find the core web logic in `app.py`, view templates in `templates/`, and ML helpers in `deep_learning/`. Follow the steps under "How to Run the Project" to set up a local environment, and inspect the `scripts/` tools for debugging database or runtime issues.

If you want, I can now:

- run a security pass to parameterize all SQL queries,
- refactor model loading so models load once on app start,
- or add safe test data insertion scripts to populate the `parkingslots` table.
