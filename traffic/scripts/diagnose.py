import os
import sys
import importlib
import socket

ROOT = os.path.dirname(os.path.dirname(__file__))

def check_files():
    print('== File inventory ==')
    targets = [
        'app.py', 'final.py', 'streamlit_app.py', 'requirements.txt',
        'TrafficTwoMonth.csv', 'traffic.csv', 'Objmodel1.h5', 'sarima_model_3h.pkl',
        'yolov5s.pt', 'templates', 'static'
    ]
    for t in targets:
        p = os.path.join(ROOT, t)
        print(f"{t}:", 'FOUND' if os.path.exists(p) else 'MISSING')

def check_imports():
    print('\n== Import checks ==')
    modules = ['flask', 'streamlit', 'mysql.connector', 'pandas', 'sklearn', 'torch', 'ultralytics', 'requests']
    for m in modules:
        try:
            importlib.import_module(m)
            print(f'{m}: OK')
        except Exception as e:
            print(f'{m}: MISSING or failed to import ({e.__class__.__name__})')

def check_mysql():
    print('\n== MySQL connectivity ==')
    try:
        import mysql.connector
    except Exception as e:
        print('mysql.connector not available:', e)
        return
    try:
        db = mysql.connector.connect(host='localhost', user='root', password='0786', port=3306, database='parkingreservation')
        cur = db.cursor()
        cur.execute('SHOW TABLES')
        tables = [r[0] for r in cur.fetchall()]
        print('Connected to parkingreservation, tables:', tables)
        # sample counts
        for t in ('parkingslots','bookslot','customerreg'):
            if t in tables:
                cur.execute(f'SELECT COUNT(*) FROM {t}')
                print(f'{t} rows:', cur.fetchone()[0])
            else:
                print(f'{t}: not present')
        cur.close()
        db.close()
    except Exception as e:
        print('DB connect/query failed:', type(e).__name__, e)

def check_http():
    print('\n== HTTP checks ==')
    # endpoints to check (Flask should be running)
    endpoints = ['http://127.0.0.1:3000/', 'http://127.0.0.1:3000/customer', 'http://127.0.0.1:3000/admin', 'http://127.0.0.1:3000/view_parking', 'http://127.0.0.1:3000/viewresponse']
    try:
        import requests
    except Exception:
        requests = None
    for url in endpoints:
        try:
            if requests:
                r = requests.get(url, timeout=5)
                print(f'{url} -> {r.status_code}')
            else:
                import urllib.request
                with urllib.request.urlopen(url, timeout=5) as resp:
                    print(f'{url} -> {resp.getcode()}')
        except Exception as e:
            print(f'{url} -> FAILED ({type(e).__name__}: {e})')

def main():
    print('Project root:', ROOT)
    check_files()
    check_imports()
    check_mysql()
    check_http()

if __name__ == '__main__':
    main()
