import mysql.connector

def main():
    try:
        db = mysql.connector.connect(host='localhost', user='root', password='0786', database='parkingreservation')
    except Exception as e:
        print('DB connection failed:', e)
        return
    cur = db.cursor()
    cur.execute("SELECT id,parkingslot,status,Address FROM parkingslots ORDER BY id")
    rows = cur.fetchall()
    if not rows:
        print('No rows found in parkingslots')
    else:
        print('parkingslots rows:')
        for r in rows:
            print(r)
    cur.close()
    db.close()

if __name__ == '__main__':
    main()
