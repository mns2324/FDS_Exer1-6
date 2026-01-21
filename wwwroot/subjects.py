#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")

studid = form.getvalue("studid", "")
subjid, selected_subjid = form.getvalue("subjid", ""), form.getvalue("subjid", "")

subjcode = html.escape(form.getvalue("subjcode", ""))
subjdesc = html.escape(form.getvalue("subjdesc", ""))
subjunits = html.escape(form.getvalue("subjunits", ""))
subjsched = html.escape(form.getvalue("subjsched", ""))

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

        cursor.execute(
            "SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid=%s",
            (selected_subjid,)
        )
        selectedsubject = cursor.fetchone()
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
        th, td { 
            border:2px solid white; padding:5px; 
        }
        </style>
        
        <script>  
        
        // copies data into the input fields to allow updating
        function fillForm(subjid, subjcode, subjdesc, subjunits, subjsched) {
            document.getElementById("subjid").value = subjid;
            document.getElementById("subjcode").value = subjcode;
            document.getElementById("subjdesc").value = subjdesc;
            document.getElementById("subjunits").value = subjunits;
            document.getElementById("subjsched").value = subjsched;
            document.getElementById("changesubjid").innerText = "Students Enrolled in Subject ID: " + subjid;

            window.location.href = `subjects.py?subjid=${subjid}`;       
            updateStudentUrl();
        }
            
        function updateStudentUrl() {
            // grab the subjects url, get the current subjid, then append it to the students href
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const link = document.getElementById("studentformurl");
            
            if (subjid) {
                link.href = `http://localhost/students.py?subjid=${subjid}`;
            }
        }
        
        // run this function when the subjects form is loaded
        window.addEventListener("load", updateStudentUrl);
        
        </script>        
    </head>

    <body>
    <table width="100%" cellpadding="10">
        <tr>
            <td colspan="2">
                <a id="studentformurl" href="http://localhost/students.py">Students</a>
            </td>
        </tr>
        <tr>
            <td width="30%" valign="top">
                <h3>Subjects Form</h3>
                <!-- submit data back to this script -->
                <form id="hello" action="subjects.py" method="post">
                    Subject ID:<br>
                    <input type="text" name="subjid" id="subjid" value="""+subjid_val+""" readonly><br>
                    Subject Code:<br>
                    <input type="text" name="subjcode" id="subjcode" value="""+subjcode_val+"""><br>
                    Description:<br>
                    <input type="text" name="subjdesc" id="subjdesc" value="""+subjdesc_val+"""><br><br>
                    Units:<br>
                    <input type="number" name="subjunits" id="subjunits" value="""+subjunits_val+"""><br><br>
                    Schedule:<br>
                    <input type="text" name="subjsched" id="subjsched" value="""+subjsched_val+"""><br><br>

                    <input type="hidden" name="action" id="action">
                  
                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Subjects Table</h3>
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

    # clicking a row fills the form fields/input boxes
    for i in range(len(rows)):
        subjid_val = str(rows[i][0])
        subjcode_val = html.escape(str(rows[i][1]))
        subjdesc_val = html.escape(str(rows[i][2]))
        subjunits_val = str(rows[i][3])
        subjsched_val = html.escape(str(rows[i][4]))
        enrolledcount = str(rows[i][5])

        urlsubjappend = str(rows[i][0])

        print(
            "<tr onclick=\"fillForm('{}','{}','{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(subjid_val, subjcode_val, subjdesc_val, subjunits_val, subjsched_val)
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

