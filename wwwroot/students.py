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
selected_subjid = form.getvalue("subjid")
conflict_msg = ""

studname = html.escape(form.getvalue("studname", ""))
studaddress= html.escape(form.getvalue("studaddress", ""))
studcourse = html.escape(form.getvalue("studcourse", ""))
studgender = html.escape(form.getvalue("studgender", ""))
yearlevel = form.getvalue("yearlevel", "")

# for the create db combo box
createdbcombo = form.getvalue("createdbcombo", "")
current_year = str(datetime.now().year)
next_year = str(datetime.now().year + 1)

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    if action in ("insert", "delete"):
        root_conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        root_cursor = root_conn.cursor()

    cursor = conn.cursor()  

    # get next student id (no auto increment)
    cursor.execute("SELECT COALESCE(MAX(studid), 999) + 1 FROM students")
    next_studid = cursor.fetchone()[0]

    # crud operations 
    if action == "insert" and studname and studaddress and studcourse and studgender and yearlevel:
        try:
            studuser = f"{next_studid}{studname.strip().lower()}" # remove whitespace and force lowercase
            studpw = f"AdDU{studname}"

            cursor.execute(
                "INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)",
                (next_studid, studname, studaddress, studcourse, studgender, yearlevel)
            )
            conn.commit()

            root_cursor.execute("CREATE USER IF NOT EXISTS %s@`localhost` IDENTIFIED BY %s", (studuser, studpw))
            root_cursor.execute("GRANT SELECT ON `{}`.* TO %s@`localhost`".format(selected_db_from_index), (studuser,))
            root_conn.commit()
        except mysql.connector.Error:
            # student users don't have insert permissions
            if dbuser[:4].isdigit():
                id = int(dbuser[:4])
                if 999 < id < 2000:
                    print(f"""
                        <script>
                            alert("Unable to insert student {studid}. You do not have the granted permissions.");
                        </script>
                    """)

    elif action == "update" and studid and studname and studaddress and studcourse and studgender and yearlevel:
        cursor.execute(
            "UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s",
            (studname, studaddress, studcourse, studgender, yearlevel, studid)
        )
        conn.commit()

    elif action == "delete" and studid:
        try:
            studuser = f"{studid}{studname.strip().lower()}"
            
            # check if they still have enrolled subjects
            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s", (studid,))
            if cursor.fetchone()[0] > 0:
                print(f"""
                    <script>
                        alert("Unable to delete student {studid}. They still have enrolled subjects.");
                    </script>
                """)
            else:
                cursor.execute("DELETE FROM students WHERE studid = %s", (studid,))
                conn.commit()
 
                # try revoking perms from the selected db
                try:
                    root_cursor.execute("REVOKE SELECT ON `{}`.* FROM %s@`localhost`".format(selected_db_from_index), (studuser,))
                    root_conn.commit()
                except mysql.connector.Error:
                    pass
                
                # check if they still have perms for other dbs. if not, we can now drop them
                root_cursor.execute(f"SHOW GRANTS FOR `{studuser}`@`localhost`")
                grants = root_cursor.fetchall()
                remaining_db_access = any(" ON `" in grant[0] and "_sy`." in grant[0] for grant in grants)   
                if not remaining_db_access:
                    root_cursor.execute(
                        f"DROP USER IF EXISTS `{studuser}`@`localhost`"
                    )
                    root_conn.commit()

        except mysql.connector.Error:
            # check first if the user isn't root (every user doesn't have delete perms) then show the first error. 
            if dbuser != "root":
                print(f"""
                    <script>
                        alert("Unable to delete student {studid}. You do not have the granted permissions.");
                    </script>
                """)
            # else:
            #     print(f"""
            #         <script>
            #             alert("Unable to delete student {studid}. They may still have enrolled subjects.");
            #         </script>
            #     """)
        
    elif action == "enrollstudent" and studid and selected_subjid:  
        # check for schedule conflict
        result = cursor.callproc('checkconflict', [studid, selected_subjid, 0, None])
        conflict_msg = result[3]      
        
        if conflict_msg == "No conflict":
            cursor.execute(
                "INSERT INTO enroll (studid, subjid, evaluation) VALUES (%s, %s, NULL)",
                (studid, selected_subjid)
            )
            conn.commit()
        
    elif action == "dropstudent" and studid and selected_subjid:
        cursor.execute(
            "DELETE FROM enroll WHERE studid=%s AND subjid=%s",
            (studid, selected_subjid)
        )
        conn.commit()

    # read all records from students table
    cursor.execute("SELECT studid, studname, studadd, studcrs, studgender, yrlvl FROM students")
    rows = cursor.fetchall()
    
    # fetch total units for all students at once
    cursor.execute(
        """SELECT st.studid, COALESCE(SUM(s.subjunits),0) AS total_units
           FROM students st
           LEFT JOIN enroll e ON st.studid = e.studid
           LEFT JOIN subjects s ON e.subjid = s.subjid
           GROUP BY st.studid"""
    )
    # assign total units value to the studid key (e.g. 1000: 24)
    studentunits = {}
    for studid_db, total_units in cursor.fetchall():
        studentunits[str(studid_db)] = total_units

    # bandaid fix for window.location.href reloading the site after the input fields are populated
    selectedstudent = None
    if studid:
        cursor.execute(
            "SELECT studid, studname, studadd, studcrs, studgender, yrlvl FROM students WHERE studid=%s",
            (studid,)
        )
        selectedstudent = cursor.fetchone()

    if selectedstudent:
        studid_val = str(selectedstudent[0])
        studname_val = html.escape(selectedstudent[1])
        studaddress_val = html.escape(selectedstudent[2])
        studcourse_val = html.escape(selectedstudent[3])
        studgender_val = html.escape(selectedstudent[4])
        yearlevel_val = str(selectedstudent[5])
    else:
        studid_val = str(next_studid)
        studname_val = studaddress_val = studcourse_val = studgender_val = yearlevel_val = ""

    # get the data to populate the enrolled subjects table for the selected student
    enrolledsubjects = []
    if studid:
        cursor.execute(
            """SELECT e.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
               FROM enroll e JOIN subjects s ON e.subjid = s.subjid 
               WHERE e.studid=%s""",
            (studid,)
        )
        enrolledsubjects = cursor.fetchall()

    # for hiding enroll button for students already enrolled in a subject
    enrolled_subj_ids = [str(s[0]) for s in enrolledsubjects]
    # for showing the conflict message span
    conflict_msg_js = ""
    
    # page load check - check conflict to control message and button visibility
    if studid and selected_subjid and action != "enrollstudent":
        result = cursor.callproc('checkconflict', [studid, selected_subjid, 0, None])
        conflict_msg = result[3] 
        conflict_msg_js = html.escape(conflict_msg)
        
    # close root connection after the crud operations
    if 'root_cursor' in locals():
        root_cursor.close()
    if 'root_conn' in locals():
        root_conn.close()
    
    # print(f"user: {dbuser}<br>")

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
        const enrolledsubjects = """ + str(enrolled_subj_ids) + """;
        const conflictMessage = """ + f'"{conflict_msg_js}"' + """;

        // show conflict message dynamically
        function showConflictMessage(msg) {
            const span = document.getElementById("conflictmsg");
            span.textContent = msg;
            if(msg && msg !== "No conflict") {
                span.style.display = "inline";
            } else {
                span.style.display = "none";
            }
        }
        
        // copies data into the input fields to allow updating
        function fillFormStudents(studid, studname, studaddress, studcourse, studgender, yearlevel) {
            document.getElementById("studid").value = studid;
            document.getElementById("studname").value = studname;
            document.getElementById("studaddress").value = studaddress;
            document.getElementById("studcourse").value = studcourse;
            document.getElementById("studgender").value = studgender;
            document.getElementById("yearlevel").value = yearlevel;
                 
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            
            // reload page with both IDs so the window load func can run checkconflict
            const newUrl = subjid ? `students.py?studid=${studid}&subjid=${subjid}` : `students.py?studid=${studid}`;
            window.location.href = newUrl;
        }
        
        function enrollStudent() {
           const params = new URLSearchParams(window.location.search);
           document.getElementById('subjid').value = params.get('subjid');
           
           // set the hidden action to enrollstudent then execute
           document.getElementById('action').value = 'enrollstudent';
           document.getElementById("studentForm").submit();
        }
        
        function dropStudent() {
            // set the hidden action to dropstudent then execute
            document.getElementById('action').value = 'dropstudent';
            document.getElementById("studentForm").submit();
        }
        
        function selectSubjectToDrop(enrolledsubjid) {
            const params = new URLSearchParams(window.location.search);
            const studid = params.get('studid');
            const enrollbtn = document.getElementById("enrollbtn");
            const dropbtn = document.getElementById("dropbtn");
            
            // show the dropbtn ONLY if you select a student then one enrolled subject
            if (studid && enrolledsubjid) {
                enrollbtn.style.display = "none";
                dropbtn.style.display = "inline-block";
                dropbtn.value = `Drop Student ID: ${studid} from Subject ID: ${enrolledsubjid}`;
                
                // store this in the hidden form field for dropSubject()
                document.getElementById('subjid').value = enrolledsubjid;
            }
        }
        
        function confirmLogout() {
            if (confirm("Are you sure you want to logout?")) {
                window.location.href = "index.py?action=logout";
            }
            return false;
        }
        
        window.addEventListener("load", () => {
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const studid = params.get("studid");
            
            const enrollbtn = document.getElementById("enrollbtn");
            document.getElementById("dropbtn").style.display = "none";

            // enroll button logic: need both a student and subject selected
            if (subjid && studid) {
                // already enrolled in this subject
                if (enrolledsubjects.includes(subjid)) {
                    enrollbtn.style.display = "none";
                // schedule conflict exists, hide button, show message
                } else if (conflictMessage && conflictMessage !== "No conflict") {
                    enrollbtn.style.display = "none";
                    showConflictMessage(conflictMessage);
                // no conflict and not yet enrolled, show enroll button
                } else {
                    enrollbtn.style.display = "inline-block";
                    enrollbtn.value = `Enroll Student ID: ${studid} to Subject ID: ${subjid}`;
                }
            } else {
                enrollbtn.style.display = "none";
            }
        });
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
                    <span>Students</span>
                    <a href="subjects.py">Subjects</a>
                    <a href="teachers.py">Teachers</a>
                    
                    <form action="students.py" method="post" id="createDbForm">                        
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
                <h3>Student Form</h3>
                
                <!-- big fyi: since there are now 2 forms in this file, an id is required
                so that .submit() recognizes the correct form to submit to keep the logic working
                (earlier it was only submitting the form that was first in order [createdb]) -->
                
                <form action="students.py" method="post" id="studentForm">
                    Student ID:<br>
                    <input type="text" name="studid" id="studid" readonly value="""+studid_val+"""><br>
                    Student Name:<br>
                    <input type="text" name="studname" id="studname" value="""+studname_val+"""><br>
                    Student Address:<br>
                    <input type="text" name="studaddress" id="studaddress" value="""+studaddress_val+"""><br><br>
                    Student Course:<br>
                    <input type="text" name="studcourse" id="studcourse" value="""+studcourse_val+"""><br><br>
                    Student Gender:<br>
                    <input type="text" name="studgender" id="studgender" value="""+studgender_val+"""><br><br>
                    Year Level:<br>
                    <input type="number" name="yearlevel" id="yearlevel" value="""+yearlevel_val+"""><br><br>
                    
                    <!-- insert,update,delete buttons -->
                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                    <!-- form.submit will send the data back -->
                    <input type="button" id="enrollbtn" value="" style="display:none;" onclick="enrollStudent()">
                    <input type="button" id="dropbtn" value="" style="display:none;" onclick="dropStudent()"><br><br>
                    <span id="conflictmsg" style="color:red;"></span>
                    
                    <input type="hidden" name="action" id="action" value="">
                    <input type="hidden" name="subjid" id="subjid">
                    

                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Students Table for: """+conn.database+"""</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Address</th>
                        <th>Course</th>
                        <th>Gender</th>
                        <th>Year</th>
                        <th>Total Units</th>
                    </tr>
    """)
    
    # get the value that was pressed in the combo box then make the database
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
                print(f"""
                    <script>
                        alert("{dbname} already exists.");
                    </script>
                """)
            else:
                cursor_createdb.execute(f"CREATE DATABASE `{dbname}`")
                conn_createdb.commit()
                
                # clone tables from the original database "enrollmentsystem"         
                cursor_createdb.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                """, (selected_db_from_index,))
                tables_to_clone = cursor_createdb.fetchall()

                for (table_name,) in tables_to_clone:
                    cursor_createdb.execute(
                        f"CREATE TABLE `{dbname}`.`{table_name}` LIKE `{selected_db_from_index}`.`{table_name}`"
                    )
                    # copy the data from subjects only, leave the other tables empty
                    if table_name == "subjects":
                        cursor_createdb.execute(
                            f"INSERT INTO `{dbname}`.`subjects` SELECT * FROM `{selected_db_from_index}`.`subjects`"
                        )
                
                # clone checkconflict from the original database "enrollmentsystem"                
                cursor_createdb.execute(
                    "SHOW CREATE PROCEDURE `{}`.`checkconflict`".format(selected_db_from_index)
                )
                proc_definition = cursor_createdb.fetchone()[2]
                    
                # replace the database name inside procedure definition
                proc_definition = proc_definition.replace(f"`enrollmentsystem`", f"`{dbname}`")
                # prevent "Warning: Could not clone procedure: 1046 (3D000): No database selected"
                cursor_createdb.execute(f"USE `{dbname}`")
                cursor_createdb.execute(proc_definition)
   
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
                
    # clicking a row fills the form fields/input boxes
    for i in range(len(rows)):
        # studid, studname, studaddress, studcourse, studgender, yearlevel
        studid_val = str(rows[i][0])
        studname_val = str(rows[i][1])
        studaddress_val = html.escape(str(rows[i][2]))
        studcourse_val = html.escape(str(rows[i][3]))
        studgender_val = html.escape(str(rows[i][4]))
        yearlevel_val = str(rows[i][5])
        # get the total units for the student from the dict, 0 as default
        totalunits_val = studentunits.get(studid_val, 0)

        print(
            "<tr onclick=\"fillFormStudents('{}','{}','{}','{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(studid_val, studname_val, studaddress_val, studcourse_val, studgender_val, yearlevel_val)
        )
        print("<td>" + studid_val + "</td>")
        print("<td>" + studname_val + "</td>")
        print("<td>" + studaddress_val + "</td>")
        print("<td>" + studcourse_val + "</td>")
        print("<td>" + studgender_val + "</td>")
        print("<td>" + yearlevel_val + "</td>")
        print("<td>" + str(totalunits_val) + "</td>")
        print("</tr>") # close the table row

    print("""
                </table>
            </td>
        </tr>
        
        <tr>
            <td width="30%"></td> <!-- empty cell to align with form -->
            <td width="70%" valign="top">
                <h3>Enrolled Subjects</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>Subject ID</th>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Units</th>
                        <th>Schedule</th>
                    </tr>                 
        """)
    
    # clicking a student shows their enrolled subjects
    for subject in enrolledsubjects:
        subjid_val = str(subject[0])
        subjcode_val = html.escape(str(subject[1]))
        subjdesc_val = html.escape(str(subject[2]))
        subjunits_val = str(subject[3])
        subjsched_val = html.escape(str(subject[4]))
        print(f"<tr onclick=\"selectSubjectToDrop('{subjid_val}')\" style=\"cursor:pointer;\">")
        print("<td>" + subjid_val + "</td>")
        print("<td>" + subjcode_val + "</td>")
        print("<td>" + subjdesc_val + "</td>")
        print("<td>" + subjunits_val + "</td>")
        print("<td>" + subjsched_val + "</td>")
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


