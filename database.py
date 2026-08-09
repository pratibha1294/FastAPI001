import pymysql

connection = pymysql.connect(
    host="localhost",
    user="fastapi001",
    password="changeme",
    database="fastapi001",
    port=3307,
    cursorclass=pymysql.cursors.DictCursor
)