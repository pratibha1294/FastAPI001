from database import connection

def register(email, password):
    cursor = connection.cursor()
    cursor.execute("""Insert into users (email,password,created_at, updated_at) 
    Values (%s,%s, NOW(), NOW())""", (email,password))
    connection.commit()