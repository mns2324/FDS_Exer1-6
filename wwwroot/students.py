#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")

studid = form.getvalue("studid", "")
selected_subjid = form.getvalue("subjid")

studname = html.escape(form.getvalue("studname", ""))
studaddress= html.escape(form.getvalue("studaddress", ""))
studcourse = html.escape(form.getvalue("studcourse", ""))
studgender = html.escape(form.getvalue("studgender", ""))
yearlevel = form.getvalue("yearlevel", "")

try:
    # connects to the mysql server
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="enrollmentsystem"
    )

    # allow execution of sql queries
    cursor = conn.cursor()

    # get next student id (no auto increment)
    cursor.execute("SELECT COALESCE(MAX(studid), 999) + 1 FROM students")
    next_studid = cursor.fetchone()[0]

    # crud operations 
    if action == "insert" and studname and studaddress and studcourse and studgender and yearlevel:
        cursor.execute(
            "INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)",
            (next_studid, studname, studaddress, studcourse, studgender, yearlevel)
        )
        conn.commit()

    elif action == "update" and studid and studname and studaddress and studcourse and studgender and yearlevel:
        cursor.execute(
            "UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s",
            (studname, studaddress, studcourse, studgender, yearlevel, studid)
        )
        conn.commit()

    elif action == "delete" and studid:
        cursor.execute( "DELETE FROM students WHERE studid=%s", (studid,) )
        conn.commit()
        
    elif action == "enrollstudent" and studid and selected_subjid:
        cursor.execute(
            # ignore will silently ignore duplicate enrolls
            "INSERT IGNORE INTO enroll (studid, subjid, evaluation) VALUES (%s, %s, NULL)",
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
    # student id: total units (e.g. 1000: 24)
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
        th, td { 
            border:2px solid white; padding:5px; 
        }
        </style>
        
        <script>
        
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
            
            // update the url if a student is selected  
            window.location.href = `students.py?studid=${studid || ''}&subjid=${subjid || ''}`;

            // make enrollbtn visible if subject is selected. if no student selected, show ?
            const btn = document.getElementById("enrollbtn");
            if (subjid){
                btn.style.display = "inline-block";
                btn.value = `Enroll Student ID: ${studid || '?'} to Subject ID: ${subjid}`;
            }
            else {
                btn.style.display = "none";
            }
        }
        
        function enrollStudent() {
           const params = new URLSearchParams(window.location.search);
           document.getElementById('subjid').value = params.get('subjid');
           
           // set the hidden action to enrollstudent then execute
           document.getElementById('action').value = 'enrollstudent';
           document.querySelector("form").submit();
        }
        
        function dropStudent() {
            // set the hidden action to dropstudent then execute
            document.getElementById('action').value = 'dropstudent';
            document.querySelector("form").submit();
        }
        
        function selectSubjectToDrop(enrolledsubjid) {
            const params = new URLSearchParams(window.location.search);
            const studid = params.get('studid');
            const enrollbtn = document.getElementById("enrollbtn");
            const dropbtn = document.getElementById("dropbtn");
            
            // shopw the dropbtn ONLY if you select a student then one enrolled subject
            if (studid && enrolledsubjid) {
                enrollbtn.style.display = "none";
                dropbtn.style.display = "inline-block";
                dropbtn.value = `Drop Student ID: ${studid} from Subject ID: ${enrolledsubjid}`;
                
                // store this in the hidden form field for dropSubject()
                document.getElementById('subjid').value = enrolledsubjid;
            }
        }
        
        // show the current student id (if it exists) when the page is loaded
        window.addEventListener("load", () => {
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const studid = params.get("studid");
            
            // make enrollbtn visible if subject is selected. if no student selected, show ?
            const btn = document.getElementById("enrollbtn");
            if (subjid) { 
                btn.style.display = "inline-block";
                btn.value = `Enroll Student ID: ${studid || '?'} to Subject ID: ${subjid}`;
            }
            
            // initialize drop button as hidden
            document.getElementById("dropbtn").style.display = "none";
        });
      
        </script>
    </head>
    <body>
    <table width="100%" cellpadding="10">
        <tr>
            <td colspan="2">
                <a href="http://localhost/subjects.py">Subjects</a>
            </td>
        </tr>
        <tr>
            <td width="30%" valign="top">
                <h3>Student Form</h3>
                <!-- submit data back to this script -->
                <form action="students.py" method="post">
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
                    <input type="hidden" name="action" id="action" value="">
                    <input type="hidden" name="subjid" id="subjid">
                    
                    <!-- form.submit will send the data back -->
                    <input type="button" id="enrollbtn" value="" style="display:none;" onclick="enrollStudent()">
                    <input type="button" id="dropbtn" value="" style="display:none;" onclick="dropStudent()">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Students Table</h3>
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
