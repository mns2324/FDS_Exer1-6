#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback
from datetime import datetime
import os 
import http.cookies

cookies = http.cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))

dbuser = cookies["dbuser"].value if "dbuser" in cookies else ""
dbpass = cookies["dbpass"].value if "dbpass" in cookies else ""
selected_db_from_index = cookies["schoolyearcombo"].value if "schoolyearcombo" in cookies else "enrollmentsystem"

# redirect back to index if not logged in
if not dbuser or not dbpass:
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")

studid = form.getvalue("studid", "")
subjid, selected_subjid = form.getvalue("subjid", ""), form.getvalue("subjid", "")

subjcode = html.escape(form.getvalue("subjcode", ""))
subjdesc = html.escape(form.getvalue("subjdesc", ""))
subjunits = html.escape(form.getvalue("subjunits", ""))
subjsched = html.escape(form.getvalue("subjsched", ""))

# for the create db combo box
createdbcombo = form.getvalue("createdbcombo", "")
current_year = str(datetime.now().year)
next_year = str(datetime.now().year + 1)
tables = [
    """CREATE TABLE IF NOT EXISTS students (
        studid INT NOT NULL,
        studname TEXT NOT NULL,
        studadd TEXT,
        studcrs TEXT,
        studgender TEXT,
        yrlvl TEXT,
        PRIMARY KEY (studid)
    ) ENGINE=InnoDB """,
    
    """CREATE TABLE IF NOT EXISTS subjects (
        subjid INT NOT NULL,
        subjcode TEXT,
        subjdesc TEXT,
        subjunits INT,
        subjsched TEXT,
        PRIMARY KEY (subjid)
    ) ENGINE=InnoDB """,
    
    """CREATE TABLE IF NOT EXISTS teachers (
        tid INT NOT NULL,
        tname TEXT,
        tdept TEXT,
        tadd TEXT,
        tcontact TEXT,
        tstatus TEXT,
        PRIMARY KEY (tid)
    ) ENGINE=InnoDB """,
    
    """CREATE TABLE IF NOT EXISTS assign (
        SubjID INT NOT NULL,
        TID INT NOT NULL,
        UNIQUE KEY (SubjID),
        KEY (TID),
        FOREIGN KEY (SubjID) REFERENCES subjects (subjid),
        FOREIGN KEY (TID) REFERENCES teachers (tid)
    ) ENGINE=InnoDB """,
    
    """CREATE TABLE IF NOT EXISTS enroll (
        eid INT NOT NULL AUTO_INCREMENT,
        studid INT,
        subjid INT,
        evaluation TEXT,
        PRIMARY KEY (eid),
        UNIQUE KEY (studid, subjid),
        KEY (subjid),
        FOREIGN KEY (studid) REFERENCES students (studid),
        FOREIGN KEY (subjid) REFERENCES subjects (subjid)
    ) ENGINE=InnoDB """,
    
    """CREATE TABLE IF NOT EXISTS grades (
        gradeid INT NOT NULL AUTO_INCREMENT,
        enroll_eid INT NOT NULL,
        prelim TEXT,
        midterm TEXT,
        prefinal TEXT,
        final TEXT,
        PRIMARY KEY (gradeid),
        UNIQUE KEY (enroll_eid),
        FOREIGN KEY (enroll_eid) REFERENCES enroll (eid)
    ) ENGINE=InnoDB """
]

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    
    cursor = conn.cursor()

    # don't use auto increment lol...
    cursor.execute("SELECT COALESCE(MAX(subjid), 1999) + 1 FROM subjects")
    next_subjid = cursor.fetchone()[0]

    # insert, update, delete to sql
    if action == "insert" and subjcode and subjdesc and subjunits and subjsched:
        cursor.execute(
            "INSERT INTO subjects (subjid, subjcode, subjdesc, subjunits, subjsched) VALUES (%s, %s, %s, %s, %s)",
            (next_subjid, subjcode, subjdesc, subjunits, subjsched)
        )
        conn.commit()

    elif action == "update" and subjid and subjcode and subjdesc and subjunits and subjsched:
        cursor.execute(
            "UPDATE subjects SET subjcode=%s, subjdesc=%s, subjunits=%s, subjsched=%s WHERE subjid=%s",
            (subjcode, subjdesc, subjunits, subjsched, subjid)
        )
        conn.commit()

    elif action == "delete" and subjid:
        cursor.execute( "DELETE FROM subjects WHERE subjid=%s", (subjid,) )
        conn.commit()

    # read all records from subjects, even those with no enrollees
    cursor.execute("""
        SELECT 
            s.subjid,
            s.subjcode,
            s.subjdesc,
            s.subjunits,
            s.subjsched,
            COUNT(e.studid) AS enrolledcount
        FROM subjects s
        LEFT JOIN enroll e ON e.subjid = s.subjid
        GROUP BY s.subjid
    """)
    rows = cursor.fetchall()
    
    # show what subject id is currently selected + update table to show # of students
    if selected_subjid:
        heading = f"Students Enrolled in Subject ID: {html.escape(selected_subjid)}"

        cursor.execute(
            "SELECT COUNT(*) FROM enroll WHERE subjid = %s",
            (selected_subjid,)
        )
        studenrolledcount = cursor.fetchone()[0] # extract only the int from the tuple

        # cursor.execute(
        #     "SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid=%s",
        #     (selected_subjid,)
        # )
        # selectedsubject = cursor.fetchone()
    else:
        heading = "Students Enrolled in Subject ID: (not selected yet)"
        studenrolledcount = 0
        
    # fix for window.location.href reloading the site after the input fields are populated
    selectedsubject = None
    if selected_subjid:
        cursor.execute(
            "SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid=%s",
            (selected_subjid,)
        )
        selectedsubject = cursor.fetchone()

    if selectedsubject:
        subjid_val = str(selectedsubject[0])
        subjcode_val = html.escape(selectedsubject[1])
        subjdesc_val = html.escape(selectedsubject[2])
        subjunits_val = str(selectedsubject[3])
        subjsched_val = html.escape(selectedsubject[4])
    else:
        subjid_val = str(next_subjid)
        subjcode_val = subjdesc_val = subjunits_val = subjsched_val = ""
        
    # get the data to populate the enrolled students table for the selected subject
    enrolledstudents = []
    if selected_subjid:
        cursor.execute(
            """SELECT s.studid, s.studname, s.studadd, s.studcrs, s.studgender, s.yrlvl
                FROM enroll e JOIN students s ON e.studid = s.studid
                WHERE e.subjid=%s""",
            (selected_subjid,)
        )
        enrolledstudents = cursor.fetchall()

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
        </style>
        
        <script>  
        
        // copies data into the input fields to allow updating
        function fillForm(subjid) {
            document.getElementById("subjid").value = subjid;
            document.getElementById("changesubjid").innerText = "Students Enrolled in Subject ID: " + subjid;

            window.location.href = `subjects.py?subjid=${subjid}`;       
            updateUrl();
        }
            
        function updateUrl() {
            // grab the subjects url, get the current subjid, then append it to the students href
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const studentlink = document.getElementById("studentformurl");
            const teacherlink = document.getElementById("teacherformurl");
            
            if (subjid) {
                studentlink.href = `students.py?subjid=${subjid}`;
                teacherlink.href = `teachers.py?subjid=${subjid}`;
            }
        }
        
        function confirmLogout() {
            if (confirm("Are you sure you want to logout?")) {
                window.location.href = "index.py?action=logout";
            }
            return false;
        }
        
        // run this function when the subjects form is loaded
        window.addEventListener("load", updateUrl);
        
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
            <td colspan="2" style="padding: 10px 5px;">
                <div class="nav-bar">
                    <a id="studentformurl" href="students.py">Students</a>
                    <span>Subjects</span>
                    <a id="teacherformurl" href="teachers.py">Teachers</a>
                    
                    <form method="post" action="subjects.py">                        
                        <select name="createdbcombo" id="createdbcombo" onchange="this.form.submit()"> <!-- submit the selected value -->
                            <option value="">Create DB</option>
                            <option value="1stsem">1st Sem</option>
                            <option value="2ndsem">2nd Sem</option>
                            <option value="summer">Summer</option>
                        </select><br>
                        <input type="hidden" name="action" value="createdb">
                    </form>
                        
                    <a href="#" id="logoutbtn" onclick="confirmLogout();">Logout</a>
                    <span id="currentuser">CURRENT USER: """+dbuser+"""
                </div>
            </td>
        </tr>
        <tr>
            <td width="30%" valign="top">
                <h3>Subjects Form</h3>
                <!-- submit data back to this script -->
                <form action="subjects.py" method="post">
                    Subject ID:<br>
                    <input type="text" name="subjid" id="subjid" value="""+subjid_val+""" readonly><br>
                    Subject Code:<br>
                    <input type="text" name="subjcode" id="subjcode" value="""+subjcode_val+"""><br>
                    Description:<br>
                    <!-- add literal quotes here to preserve values with spaces -->
                    <input type="text" name="subjdesc" id="subjdesc" value=\""""+subjdesc_val+"""\"><br><br>
                    Units:<br>
                    <input type="number" name="subjunits" id="subjunits" value="""+subjunits_val+"""><br><br>
                    Schedule:<br>
                    <!-- add literal quotes here to preserve values with spaces -->
                    <input type="text" name="subjsched" id="subjsched" value=\""""+subjsched_val+"""\"><br><br>

                    <input type="hidden" name="action" id="action">
                  
                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Subjects Table for: """+conn.database+"""</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>ID</th>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Units</th>
                        <th>Schedule</th>
                        <th># of Students</th>
                    </tr>
    """)
    
    # get the value that was pressed in the combo box
    if action == "createdb" and createdbcombo != "":
        dbname = f"{createdbcombo}_sy{current_year}_{next_year}"
        
        try:
            conn_createdb = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            cursor_createdb = conn_createdb.cursor()
                   
            # if it already exists, do nothing   
            cursor_createdb.execute("SHOW DATABASES LIKE %s", (dbname,))
            if cursor_createdb.fetchone():
                print(f"<h3>{dbname} already exists</h3>")
            else:
                cursor_createdb.execute(f"CREATE DATABASE `{dbname}`")
                conn_createdb.commit()
                
            # after the database is created, insert the schema structure (tables)
            conn_tables = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",
                database=dbname
            )
            cursor_tables = conn_tables.cursor()                       
            for table_sql in tables:
                cursor_tables.execute(table_sql)
            conn_tables.commit()
            
            # for convenience, premade subjects with schedules
            subjects_data = [
                (2000, 'aa', 'aa', 12, 'MWF 08:20-09:20'),
                (2001, 'bb', 'bb', 5,  'MWF 11:35-12:35'),
                (2002, 'cc', 'cc', 3,  'MWF 10:30-11:30'),
                (2003, 'dd', 'dd', 3,  'TTH 10:30-11:30'),
                (2004, 'ee', 'ee', 2,  'MWF 09:30-10:25'),
                (2005, 'ff', 'ff', 5,  'TTH 08:20-09:20'),
                (2006, 'gg', 'gg', 3,  'TTH 09:30-10:25'),
                (2007, 'hh', 'hh', 12, 'MWF 11:00-12:00'),
                (2008, 'ii', 'ii', 2,  'MWF 09:00-11:00'),
                (2009, 'kk', 'kk', 5,  'TTH 10:40-11:25')
            ]
            for subject in subjects_data:
                cursor_tables.execute(
                    "INSERT INTO subjects (subjid, subjcode, subjdesc, subjunits, subjsched) VALUES (%s, %s, %s, %s, %s)",
                    subject
                )
            conn_tables.commit()
    
            print(f"""
                <script>
                    alert("Database {dbname} successfully.");
                </script>
            """)
    
        except Exception as e:
            print(f"<pre>{e}</pre>")

        finally:
            if 'conn_createdb' in locals():
                conn_createdb.close()
            if 'conn_tables' in locals():
                conn_tables.close()

    # clicking a row fills the form fields/input boxes
    for i in range(len(rows)):
        subjid_val = str(rows[i][0])
        subjcode_val = html.escape(str(rows[i][1]))
        subjdesc_val = html.escape(str(rows[i][2]))
        subjunits_val = str(rows[i][3])
        subjsched_val = html.escape(str(rows[i][4]))
        enrolledcount = str(rows[i][5])

        # urlsubjappend = str(rows[i][0])

        print(
            "<tr onclick=\"fillForm('{}')\" style=\"cursor:pointer;\">"
            .format(subjid_val)
        )
        print("<td>" + subjid_val + "</td>")
        print("<td>" + subjcode_val + "</td>")
        print("<td>" + subjdesc_val + "</td>")
        print("<td>" + subjunits_val + "</td>")
        print("<td>" + subjsched_val + "</td>")
        print("<td>" + enrolledcount + "</td>")
        print("</tr>")

    print("""
                </table>
            </td>
        </tr>
        
        <tr>
            <td width="30%"></td> <!-- empty cell to align with form -->
            <td width="70%" valign="top">
                <h3 id="changesubjid">""" + heading + """</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Address</th>
                        <th>Course</th>
                        <th>Gender</th>
                        <th>Year Level</th>
                    </tr>
        """)
        
    # clicking a subject shows all students currently enrolled in it
    for student in enrolledstudents:
        studid_val = str(student[0])
        studname_val = str(student[1])
        studaddress_val = html.escape(str(student[2]))
        studcourse_val = html.escape(str(student[3]))
        studgender_val = html.escape(str(student[4]))
        yearlevel_val = str(student[5])
        print("<tr style=\"cursor:pointer;\">")
        print("<td>" + studid_val + "</td>")
        print("<td>" + studname_val + "</td>")
        print("<td>" + studaddress_val + "</td>")
        print("<td>" + studcourse_val + "</td>")
        print("<td>" + studgender_val + "</td>")
        print("<td>" + yearlevel_val + "</td>")
        print("</tr>") 
        
    print("""
                </table>
            </td>
        </tr>       
    </table>
    </body>
    </html>
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

