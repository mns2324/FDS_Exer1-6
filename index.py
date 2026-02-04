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

if action == "login" and dbpass == "":
    try:
        # connects to the mysql server
        conn = mysql.connector.connect(
            host="localhost",
            user=dbuser,
            password=dbpass,
            database="enrollmentsystem"
        )

        # allow execution of sql queries
        cursor = conn.cursor()
            
        print("""
        <html>
        <head>
            <style>
            body {
                background-color: #1f1f1f;
                color: white;
            }
            input {
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
            select {
                background-color: #1f1f1f;
                color: white;
            }
            </style>
            
            <script>

            </script>
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
                    <!-- submit data back to this script -->
                    <form action="index.py" method="post">
                    
                        <input type="hidden" name="action" id="action" value="">
                    
                        Username:<br>
                        <input type="text" name="dbuser"><br>
                        Password:<br>
                        <input type="text" name="dbpass"><br><br>
                        
                        <div id="sydiv" style="display:none;"> 
                            School Year:<br> 
                            <select name="schoolyearcombo">
                                <option value="1stsem_sy2026_2027">1stsem_sy2026_2027</option> 
                            </select><br><br>    
                        </div>
                        
                        <button type="submit" id="loginbtn">Login</button>

                    </form>
                </td>

                <td width="70%" valign="top">
                    <h1>Welcome to the Student Information System</h1>
                    <h3>Please log in to continue :)</h3>
                </td>
        """)

    # displays database/runtime errors if there are any, shows line number of error
    except Exception:
        tb = traceback.format_exc()
        print("<h2>Error</h2>")
        print(f"<pre>{tb}</pre>")

    # ensure database connection is closed
    finally:
        if 'conn' in locals():
            conn.close()


