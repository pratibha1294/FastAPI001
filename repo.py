from database import connection

def register(email, password):
    cursor = connection.cursor()
    cursor.execute("""Insert into users (email,password,created_at, updated_at) 
    Values (%s,%s, NOW(),
    NOW())""", (email,password))
    connection.commit()

def login(email,password):

    cursor = connection.cursor()
    cursor.execute("SELECT id, email, password FROM users where email= %s and password=%s", (email,password))

    user = cursor.fetchone()
    return user

def validateUserPassword(userId: int, password: str):
    cursor = connection.cursor()
    cursor.execute("SELECT count(userId) as matches FROM users where userId= %d and password= %s", (userId,password))
    result= cursor.fetchone()
    return result["matches"]==1
