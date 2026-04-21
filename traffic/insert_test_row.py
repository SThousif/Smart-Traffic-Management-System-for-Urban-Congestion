import mysql.connector
import sys

try:
    conn = mysql.connector.connect(host='localhost', user='root', password='0786', port=3306, database='parkingreservation')
    cur = conn.cursor()
    sql = "INSERT INTO parkingslots (parkingslot, Cost, Address, Imagename, status) VALUES (%s, %s, %s, %s, %s)"
    val = ('A1', '50', 'Test Address', 'test.jpg', 'unlocked')
    cur.execute(sql, val)
    conn.commit()
    print('Inserted parkingslot id=', cur.lastrowid)
    cur.close()
    conn.close()
except Exception as e:
    print('ERROR:', e)
    sys.exit(1)
