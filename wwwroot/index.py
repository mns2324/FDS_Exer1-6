#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback
import http.cookies

form = cgi.FieldStorage()
action = form.getvalue("action", "login")
dbuser = form.getvalue("dbuser", "")
dbpass = form.getvalue("dbpass", "")
login_fail = False
user_exists = False

cookie = http.cookies.SimpleCookie()
cookie["dbuser"] = dbuser
cookie["dbpass"] = dbpass
cookie["schoolyearcombo"] = form.getvalue("schoolyearcombo", "")

# expire in 2 hours
for key in cookie:
    cookie[key]["max-age"] = 7200
    cookie[key]["path"] = "/"
    
### place these action blocks here (has redirect header) before the content header so that they arent printed literally
# redirect to students.py when continue is clicked with this http header
if action == "continue":  
    print("Status: 302 Found")
    print(cookie.output())
    print("Location: students.py")
    print()
    exit()

# clicking the logout href from any of the 3 pages should execute this
if action == "logout":
    # set these to expire immediately
    expired_cookie = http.cookies.SimpleCookie()
    expired_cookie["dbuser"] = ""
    expired_cookie["dbpass"] = ""
    expired_cookie["schoolyearcombo"] = ""
    
    for key in expired_cookie:
        expired_cookie[key]["max-age"] = 0
        expired_cookie[key]["path"] = "/"
        
    print("Status: 302 Found")
    print(expired_cookie.output())
    print("Location: index.py")
    print()
    exit()

print("Content-Type: text/html\n") 

# connect to root first to get the school year databases
# then attempt to connect to the database with the form credentials
if action == "login":    
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="enrollmentsystem"
        )
        
        cursor = conn.cursor()
        
        cursor.execute("SHOW DATABASES LIKE '%_sy____\_____'") 
        school_year_dbs = [row[0] for row in cursor.fetchall()]    
        if not school_year_dbs:
            school_year_dbs.insert(0, "enrollmentsystem") 
        accessible_dbs = []          
        display_dbs = [] 
        
        if dbuser and dbpass:
            try:
                test_conn = mysql.connector.connect(
                    host="localhost",
                    user=dbuser,
                    password=dbpass
                )
                user_exists = True
                
                # return the list of databases that the user has access to
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
                login_fail = True
                pass
        
        if user_exists:
            display_dbs = accessible_dbs
            
        # print(f"<h3>DEBUG</h3>")
        print(f"user_exists: {user_exists}<br>")
        print(f"accessible_dbs: {accessible_dbs}<br>")
        print(f"display_dbs: {display_dbs}<br>")
        print(f"school_year_dbs: {school_year_dbs}<br>")

         
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
                border:2px solid red; 
                padding: 8px;
                width: fit-content;
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
                    <!-- submit dbuser and dbpass to index.py -->
                    <!-- cookies will be the one to relay this info to students.py -->
                    <form action="index.py" method="post" id="loginform">
                    
                        <!-- 
                            the if else block is imperative here. without it, the second login fail will 
                            return an error as the form values would have duplicated, creating a list.
                            AttributeError: 'list' object has no attribute 'strip'
                        -->
                        <input type="hidden" name="action" id="action" value="login">
                        <input type="hidden" name="dbuser" value=""" + (html.escape(dbuser) if user_exists else "") + """>
                        <input type="hidden" name="dbpass" value=""" + (html.escape(dbpass) if user_exists else "") + """>
  
                        Username:<br>
                        <input type="text" name="dbuser" value=""><br>
                        Password:<br>
                        <input type="password" name="dbpass"><br><br>
                        
                        <div id="sydiv"> 
                            School Year:<br> 
                            <select name="schoolyearcombo">
        """)
            
        # populate school year dropdown with available databases (depends on user)
        for db in display_dbs:
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
                        Invalid username or password. Please try again!
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
                    action.value = 'login';
                } else {
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
        

