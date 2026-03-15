#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback
import os
import http.cookies

cookies = http.cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
dbuser = cookies["dbuser"].value if "dbuser" in cookies else ""
dbpass = cookies["dbpass"].value if "dbpass" in cookies else ""
selected_db_from_index = cookies["schoolyearcombo"].value if "schoolyearcombo" in cookies else "enrollmentsystem"

# redirect back to index if not logged in or not student
if not dbuser or not dbpass:
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()
if not (dbuser[:4].isdigit() and 999 < int(dbuser[:4]) < 2000):
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()

form = cgi.FieldStorage()
action = form.getvalue("action", "")
studid = int(dbuser[:4])
subjid = form.getvalue("subjid", "")
eid = form.getvalue("eid", "")

currentstudent = None
subjects = []

studid_val = ""
studname_val = ""
studcourse_val = ""
yearlevel_val = ""

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    cursor = conn.cursor()
    
    # submit evaluation for this specific subject
    evaltext = form.getvalue("evaltext", "")
    if action == "submitcomment" and studid and evaltext:
        cursor.execute(
            "UPDATE enroll SET evaluation = %s WHERE eid = %s AND studid = %s",
            (evaltext, eid, studid)
        )
        conn.commit()
        
        print(f"Status: 302 Found")
        print(f"Location: evaluate.py?subjid={subjid}&eid={eid}&submitted=1")
        print()
        exit()
        
        existing_eval = ""

    # fetch student info to display on the page
    cursor.execute(
        "SELECT studid, studname, studcrs, yrlvl FROM students WHERE studid = %s",
        (studid,)
    )
    currentstudent = cursor.fetchone()

    if currentstudent:
        studid_val      = str(currentstudent[0])
        studname_val    = html.escape(str(currentstudent[1]))
        studcourse_val  = html.escape(str(currentstudent[2]))
        yearlevel_val   = str(currentstudent[3])
    else:
        studid_val = studname_val = studcourse_val = yearlevel_val = ""

    # fetch the single clicked subject's info
    cursor.execute(
        """SELECT s.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched, e.eid, e.evaluation
           FROM enroll e
           JOIN subjects s ON e.subjid = s.subjid
           WHERE e.eid = %s AND e.studid = %s""",
        (eid, studid)
    )
    subjects = cursor.fetchall()

except Exception:
    tb = traceback.format_exc()
    print("<h2>Error</h2>")
    print(f"<pre>{tb}</pre>")

finally:
    if 'conn' in locals():
        conn.close()
        
print("Content-Type: text/html\n")

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
        th, td, .header { 
            border:2px solid white; padding:5px; 
        }
        .header {
            display: flex;
            padding: 10px;
            text-align: left;
            background: #0a68f5;
            color: white;
            font-size: 18px;
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
        a {
            display: inline-block;      
            background-color: #0a68f5;
            color: cyan;
            padding: 5px;
            border-radius: 6px;
        }
        #logoutbtn{
            background-color: white;
            color: red;
        }
        .nav-bar {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .nav-bar form {
            margin: 0;
        }
        textarea {
            width: 100%;
            max-width: 500px;
            height: 100px;
        }
        #submitsuccess {
            border:2px solid green; 
            padding: 8px;
            width: fit-content;
            color: green;
            display: none;
            margin-top: 10px;
        }
        </style>
        <script>
            window.addEventListener("load", () => {
                const params = new URLSearchParams(window.location.search);
                
                // show save popup if evaluation was submitted
                if (params.get("submitted") === "1") {
                    const popup = document.getElementById("submitsuccess");
                    popup.style.display = "block";
                    setTimeout(() => { popup.style.display = "none"; }, 4000);
                }
            });
        </script>
    </head>
    <body>

    <div class="header">
        <img src="catgulp.jpg">
        <div class="header-text">
            <h1>STUDENT INFORMATION SYSTEM</h1>
            <span>UNIVERSITY NAME</span>
        </div>
    </div>

    <div class="nav-bar">
        <br><br>
        <span>CURRENT USER: """+dbuser+""" /// CURRENT DATABASE: """+selected_db_from_index+"""</span>
    </div>

    <a href="studrec.py">Back to Student Record</a> 
    <h2>Student Information</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Course</th>
            <th>Year Level</th>
        </tr>
        <tr>
            <td>"""+studid_val+"""</td>
            <td>"""+studname_val+"""</td>
            <td>"""+studcourse_val+"""</td>
            <td>"""+yearlevel_val+"""</td>
        </tr>
    </table>

    <h2>Subject Information</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Description</th>
            <th>Units</th>
            <th>Schedule</th>
        </tr>
    """)

for subj in subjects:
    print(f"""
    <tr>
        <td>{html.escape(str(subj[0]))}</td>
        <td>{html.escape(str(subj[1]))}</td>
        <td>{html.escape(str(subj[2]))}</td>
        <td>{html.escape(str(subj[3]))}</td>
        <td>{html.escape(str(subj[4]))}</td>
    </tr>
    """)

print("""
    </table>

    <p>Your Evaluation/Comments</p>
    <p id="submitsuccess">Comment submitted successfully!</p>
    <form action="evaluate.py" method="post" id="evalForm">
        <textarea id="evaltext" name="evaltext" placeholder="Enter your thoughts here..."></textarea><br><br>
        <input type=submit value="Submit Comment" onclick="document.getElementById('action').value='submitcomment'">
        
        <input type="hidden" name="eid" value=""" + html.escape(str(eid)) + """>
        <input type="hidden" name="subjid" value=""" + html.escape(str(subjid)) + """>
        <input type="hidden" name="action" id="action" value="">
    </form>

    </body>
    </html>
""")
