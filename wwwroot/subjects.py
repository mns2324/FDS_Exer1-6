#!/usr/bin/env python3

import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")

subjid = form.getvalue("subjid", "")
selected_subjid = form.getvalue("subjid")

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

    # insert, update, delete to sql
    if action == "insert" and subjcode and subjdesc and subjunits and subjsched:
        cursor.execute(
            "INSERT INTO subjects (subjcode, subjdesc, subjunits, subjsched) VALUES (%s, %s, %s, %s)",
            (subjcode, subjdesc, subjunits, subjsched)
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

    # read all records from subjects
    cursor.execute("SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects")
    rows = cursor.fetchall()
    
    # show what subject id is currently selected
    if selected_subjid:
        heading = f"Students Enrolled in Subject ID: {html.escape(selected_subjid)}"
    else:
        heading = "Students Enrolled in Subject ID: (not selected yet)"

    print("""
    <html>
    <head>
        <style>
        body {
            background-color: #000000;
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
            border:1px solid white; padding:5px; 
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

            // pushState should make the page not reload compared to window.location.href
            history.pushState({}, "", `subjects.py?subjid=${subjid}`);
            
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
                    <input type="text" name="subjid" id="subjid" readonly><br>
                    Subject Code:<br>
                    <input type="text" name="subjcode" id="subjcode"><br>
                    Description:<br>
                    <input type="text" name="subjdesc" id="subjdesc"><br><br>
                    Units:<br>
                    <input type="number" name="subjunits" id="subjunits"><br><br>
                    Schedule:<br>
                    <input type="text" name="subjsched" id="subjsched"><br><br>

                    <!-- use ts to append the subjid to the url, somehow -->
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
        subjid = str(rows[i][0])
        subjcode = html.escape(str(rows[i][1]))
        subjdesc = html.escape(str(rows[i][2]))
        subjunits = str(rows[i][3])
        subjsched = html.escape(str(rows[i][4]))

        urlsubjappend = str(rows[i][0])

        print(
            "<tr onclick=\"fillForm('{}','{}','{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(subjid, subjcode, subjdesc, subjunits, subjsched)
        )
        print("<td>" + subjid + "</td>")
        print("<td>" + subjcode + "</td>")
        print("<td>" + subjdesc + "</td>")
        print("<td>" + subjunits + "</td>")
        print("<td>" + subjsched + "</td>")
        print("<td>0</td>") # total units here
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
                        <th>Gender</th>
                        <th>Course</th>
                        <th>Year Level</th>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    </body>
    </html>
    """)

# prevent blank pages, displays database/runtime errors if there are any
except Exception as e:
    print("<h2>Error</h2>")
    print(f"<pre>{e}</pre>")

# ensure database connection is closed
finally:
    if 'conn' in locals():
        conn.close()


