import mysql.connector

def main():
    try:
        cnx = mysql.connector.connect(host='localhost', user='root', password='0786', database='parkingreservation', port=3306)
        cur = cnx.cursor()
        sql = "INSERT INTO bookslot (slotid,hourcost,nameoncard,cvv,expiredate,totalhours,totalamount,status,useremail) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        val = ('A1', '50', 'Test', '123', '2026-12-31', 2, 100, 'locked', 'testuser@example.com')
        cur.execute(sql, val)
        cnx.commit()
        print({'inserted_id': cur.lastrowid})
    except Exception as e:
        print({'error': str(e)})

if __name__ == '__main__':
    main()
