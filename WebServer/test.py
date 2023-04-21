import mysql.connector

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="ImageOnlineRecognitionSystem",
    auth_plugin='mysql_native_password'
)
mycursor = mydb.cursor()

mycursor.execute("SHOW TABLES")