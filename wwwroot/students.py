#!/usr/bin/env python3

import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")
# name = html.escape(form.getvalue("name", ""))
# age = form.getvalue("age", "")
# email = html.escape(form.getvalue("email", ""))
studid = form.getvalue("studid", "")
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

    # insert, update, delete 
    if action == "insert" and studname and studaddress and studcourse and studgender and yearlevel:
        cursor.execute(
            "INSERT INTO students (studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s)",
            (studname, studaddress, studcourse, studgender, yearlevel)
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
        
    # elif action == "enrollstudent" and studid:
    #     cursor.execute()
    #     conn.commit()

    # read all records from users table
    # cursor.execute("SELECT name, age, email FROM users")
    cursor.execute("SELECT studid, studname, studadd, studcrs, studgender, yrlvl FROM students")
    rows = cursor.fetchall()

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
        </style>
        
        <script>
        // copies data into the input fields to allow updating
        function fillForm(studid, studname, studaddress, studcourse, studgender, yearlevel) {
            document.getElementById("studid").value = studid;
            document.getElementById("studname").value = studname;
            document.getElementById("studaddress").value = studaddress;
            document.getElementById("studcourse").value = studcourse;
            document.getElementById("studgender").value = studgender;
            document.getElementById("yearlevel").value = yearlevel;
        }
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
                    <input type="text" name="studid" id="studid" readonly><br>
                    Student Name:<br>
                    <input type="text" name="studname" id="studname"><br>
                    Student Address:<br>
                    <input type="text" name="studaddress" id="studaddress"><br><br>
                    Student Course:<br>
                    <input type="text" name="studcourse" id="studcourse"><br><br>
                    Student Gender:<br>
                    <input type="text" name="studgender" id="studgender"><br><br>
                    Year Level:<br>
                    <input type="number" name="yearlevel" id="yearlevel"><br><br>
                    
                    <!-- insert,update,delete buttons -->
                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                    <input type="hidden" name="action" id="action" value="">
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

        print(
            # string interpolation being used here, remember
            "<tr onclick=\"fillForm('{}','{}','{}','{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(studid_val, studname_val, studaddress_val, studcourse_val, studgender_val, yearlevel_val)
        )
        print("<td>" + studid_val + "</td>")
        print("<td>" + studname_val + "</td>")
        print("<td>" + studaddress_val + "</td>")
        print("<td>" + studcourse_val + "</td>")
        print("<td>" + studgender_val + "</td>")
        print("<td>" + yearlevel_val + "</td>")
        print("<td>0</td>")  # placeholder
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


