from database import connection

def register(email, password):
    cursor = connection.cursor()
    cursor.execute("""Insert into users (email,password,created_at, updated_at) 
    Values (%s,%s, NOW(),
    NOW())""", (email,password))
    connection.commit()

def login(email,password):

    cursor = connection.cursor()
    cursor.execute("SELECT id, email, password FROM users where email=%s and password=%s", (email,password))

    user = cursor.fetchone()
    return user

def validateUserPassword(userId: int, password: str):
    cursor = connection.cursor()
    cursor.execute("SELECT count(id) as matches FROM users where id=%s and password=%s", (userId,password))
    result= cursor.fetchone()
    return result["matches"]==1

def updateUserPassword(userId: int, password: str):
    cursor= connection.cursor()
    cursor.execute("""UPDATE users 
    SET password = %s
    where id= %s """, (password, userId))
    connection.commit()

def create_file_record(owner_id, filename, storage_key):
    cursor=connection.cursor()
    cursor.execute("""INSERT INTO files (owner_id, filename, storage_key)
    VALUES (%s, %s, %s); """, (owner_id, filename, storage_key))
    connection.commit()

def get_file(file_id):
   cursor=connection.cursor()
   cursor.execute("""select * from files where id=%s""")
   fileDetails= cursor.fetchone() 
   return fileDetails

def list_files_for_user(owner_id):
    cursor= connection.cursor()
    cursor.execute("""select id,filename from files where owner_id=%s """)
    fileslist= cursor.fetchone()
    return fileslist