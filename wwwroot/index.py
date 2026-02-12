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
schoolyearcombo = form.getvalue("schoolyearcombo", "")
logged_in = False
user_exists = False
login_fail = False

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

                test_cursor = test_conn.cursor()
                test_cursor.execute(f"SHOW GRANTS FOR '{dbuser}'@'localhost'")
                grants = test_cursor.fetchall()

                # extract the database names from the grants
                for grant_tuple in grants:
                    grant_str = str(grant_tuple[0])
                    if "SELECT" in grant_str and "ON `" in grant_str:
                        start = grant_str.find("ON `") + 4
                        end = grant_str.find("`", start)
                        db_name = grant_str[start:end]

                        if db_name in school_year_dbs:
                            accessible_dbs.append(db_name)

                test_conn.close()
            except mysql.connector.Error:
                login_fail = True

        # change db dropdown options based on enroll status
        if user_exists and accessible_dbs:
            display_dbs = accessible_dbs
        else:
            display_dbs = school_year_dbs
            
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
                    <form action="index.py" method="post" id="loginform">
                    
                        <input type="hidden" name="action" id="action" value="login">
                    
                        Username:<br>
                        <input type="text" name="dbuser" id="username" value="""+html.escape(dbuser)+"""><br>
                        Password:<br>
                        <input type="password" name="dbpass" id="password"><br><br>
                        
                        <div id="sydiv"> 
                            School Year:<br> 
                            <select name="schoolyearcombo" id="schoolyearcombo" required>
                                <option value="">--- Select Semester ---</option>
        """)
            
        # populate school year dropdown with available databases
        # keep the same option selected it the site is reloaded
        for db in display_dbs:
            selected = 'selected' if db == schoolyearcombo else ''
            print(f'<option value="{db}" {selected}>{db}</option>')
            
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
            var sydiv = document.getElementById('sydiv');
            var schoolyearcombo = document.getElementById('schoolyearcombo');

            function storeUsername() {
                const username = document.getElementById('username').value;
                if (username) {
                    const expirationDate = new Date();
                    expirationDate.setDate(expirationDate.getDate() + 7); // cookie expires in 7 days
                    document.cookie = `username=${username}; expires=${expirationDate.toUTCString()}; path=/`;
                }
            }

            // w3schools getCookie: if cookie is found, return its value.
            function getCookie(name) {
                const nameEQ = name + "=";
                const decodedCookie = decodeURIComponent(document.cookie);
                const ca = decodedCookie.split(';');
                for(let i = 0; i < ca.length; i++) {
                    let c = ca[i];
                    while (c.charAt(0) === ' ') c = c.substring(1, c.length);
                    if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
                }
                return '';
            }

            const storedUsername = getCookie('username');
            if (storedUsername !== '') {
                document.getElementById('username').value = storedUsername;
            }
            
            // update ui based on login state
            if (userExists){
                loginbtn.textContent = 'Continue';
                action.value = 'continue';
                sydiv.style.display = 'block';
            } else {
                sydiv.style.display = 'none';
            }

            loginForm.addEventListener('submit', function(e){
                storeUsername();
                
                if(!userExists){
                    loginForm.action = 'index.py';
                    action.value = 'login';
                } else {
                    const selectedSY = schoolyearcombo.value;
                    if (!selectedSY || selectedSY === '') {
                        e.preventDefault();
                        alert('Please select a school year to continue.');
                    }
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

