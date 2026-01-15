from flask import Flask
import pymysql
import os

app = Flask(__name__)

DB_HOST = "rds-mysql-private.cp2gocew6omt.ap-south-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "kaviyapazhanivel"
DB_NAME = "devopsdb"

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route("/")
def home():
    return "Flask + RDS is working"

@app.route("/users")
def users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    data = cursor.fetchall()
    conn.close()
    return {"users": data}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
