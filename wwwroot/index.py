#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "login")
dbuser = form.getvalue("dbuser", "")
dbpass = form.getvalue("dbpass", "")
login_fail = False
logged_in = False
user_exists = False

if action == "login":
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="enrollmentsystem"
        )
        
        logged_in = True
        cursor = conn.cursor()
        
        cursor.execute("SHOW DATABASES LIKE '%_sy____\_____'") 
        school_year_dbs = [row[0] for row in cursor.fetchall()]      
        accessible_dbs = []          
        
        if dbuser and dbpass:
            try:
                test_conn = mysql.connector.connect(
                    host="localhost",
                    user=dbuser,
                    password=dbpass
                )
                user_exists = True
                
                for db in school_year_dbs:
                    try:
                        test_db_conn = mysql.connector.connect(
                            host="localhost",
                            user=dbuser,
                            password=dbpass,
                            database=db
                        )
                        accessible_dbs.append(db)
                        test_db_conn.close()
                    except mysql.connector.Error:
                        pass
                    
                test_conn.close()
                
            except mysql.connector.Error:
                logged_in = False
                login_fail = True
                tb = traceback.format_exc()
                print("<h2>Error</h2>")
                print(f"<pre>{tb}</pre>")
                
        if user_exists:
            display_dbs = accessible_dbs
            
        print(f"<h3>DEBUG</h3>")
        print(f"user_exists: {user_exists}<br>")
        print(f"accessible_dbs: {accessible_dbs}<br>")
         
        print("""
        <html>
        <head>
            <style>
            body {
                background-color: #1f1f1f;
                color: white;
            }
            input, select {
                background-color: #000000;
                color: white;
            }
            table { 
                border-collapse:collapse; 
            }
            th, td{ 
                padding:15px; 
            }
            .header {
                display: flex;
                padding: 10px;
                text-align: left;
                background: #0a68f5;
                color: white;
                font-size: 18px;
                border:2px solid white; 
            }
            .header img {
                height: 100px;
                width: 100px;
            }
            .header-text {
                padding: 10px;
                display: flex;
                flex-direction: column;
            }
            .header-text h1 {
                margin: 0;
            }
            .header-text span {
                font-size: 16px;
            }
            input:user-invalid {
                border-color: #c51244;
            }
            #error-message {
                color: #ff4444;
                display: """ + ('block' if login_fail else 'none') + """;
                margin-top: 10px;
            }
            #sydiv {
                display: """ + ('block' if user_exists else 'none') + """;
            }
            </style>
        </head>
        <body>
        <table width="100%" cellpadding="10">
            <div class="header">
                <img src="catgulp.jpg">
                <div class="header-text">
                    <h1>STUDENT INFORMATION SYSTEM</h1>
                    <span>UNIVERSITY NAME</span>
                </div>
            </div>

            <tr>
                <td width="30%" valign="top">
                    <h3>Login</h3>
                    <!-- submit dbuser and dbpass to students.py -->
                    <form action="students.py" method="post" id="loginform">
                    
                        <input type="hidden" name="action" id="action" value="login">
                        <input type="hidden" name="dbuser" value=""" + html.escape(dbuser) + """>
                        <input type="hidden" name="dbpass" value=""" + html.escape(dbpass) + """>
  
                        Username:<br>
                        <input type="text" name="dbuser" value=""><br>
                        Password:<br>
                        <input type="password" name="dbpass"><br><br>
                        
                        <div id="sydiv"> 
                            School Year:<br> 
                            <select name="schoolyearcombo">
        """)
            
        # populate school year dropdown with available databases
        for db in school_year_dbs:
            print(f'<option value="{db}">{db}</option>')
            
        print("""                                
                            </select><br><br>    
                        </div>
                        
                        <button type="submit" id="loginbtn">Login</button>

                    </form>
                </td>

                <td width="70%" valign="top">
                    <h1>Welcome to the Student Information System</h1>
                    <h3>Please log in to continue.</h3>
                    
                    <div id="error-message">
                        Invalid username or password. Please try again.
                    </div>
                </td>
            </tr>
        </body>
        <script>
            var userExists = """ + ('true' if user_exists else 'false') + """;
            var loginForm = document.getElementById('loginform');
            var loginbtn = document.getElementById('loginbtn');
            var action = document.getElementById('action');
            
            if (userExists){
                loginbtn.textContent = 'Continue';
                action.value = 'continue';
            }
            
            loginForm.addEventListener('submit', function(){
                if (!userExists) {
                    loginForm.action = 'index.py';
                    action.value = 'login';
                } else {
                    loginForm.action = 'students.py';
                    action.value = 'continue';
                }
            });
        </script>
        </html>
        """)

    # displays database/runtime errors if there are any, shows line number of error
    except Exception:
        logged_in = False
        tb = traceback.format_exc()
        print("<h2>Error</h2>")
        print(f"<pre>{tb}</pre>")

    # ensure database connection is closed
    finally:
        if 'conn' in locals():
            conn.close()
            
elif action == "continue":
    print("Content-Type: text/html\n")
    print("""
    <html>
    <head>
        <meta http-equiv="refresh" content="0;url=students.py">
    </head>
    <body>
        <p>Redirecting...</p>
    </body>
    </html>
    """)
