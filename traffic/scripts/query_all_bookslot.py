import mysql.connector
import json

def main():
    try:
        cnx = mysql.connector.connect(host='localhost', user='root', password='0786', database='parkingreservation', port=3306)
        cur = cnx.cursor()
        cur.execute("SELECT id,slotid,hourcost,nameoncard,totalhours,totalamount,status,useremail FROM bookslot")
        rows = cur.fetchall()
        print(json.dumps(rows, default=str))
    except Exception as e:
        print(json.dumps({'error': str(e)}))

if __name__ == '__main__':
    main()
