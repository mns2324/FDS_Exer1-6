#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")

tid = form.getvalue("tid", "")
selected_subjid = form.getvalue("subjid")

tname = html.escape(form.getvalue("tname", ""))
tdept = html.escape(form.getvalue("tdept", ""))
tadd = html.escape(form.getvalue("tadd", ""))
tcontact = html.escape(form.getvalue("tcontact", ""))
tstatus = form.getvalue("tstatus", "")

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
    cursor.execute("SELECT COALESCE(MAX(tid), 2999) + 1 FROM teachers")
    next_tid = cursor.fetchone()[0]

    # crud operations 
    if action == "insert" and tname and tdept and tadd and tcontact and tstatus:
        cursor.execute(
            "INSERT INTO teachers (tid, tname, tdept, tadd, tcontact, tstatus) VALUES (%s, %s, %s, %s, %s, %s)",
            (next_tid, tname, tdept, tadd, tcontact, tstatus)
        )
        conn.commit()

    elif action == "update" and tid and tname and tdept and tadd and tcontact and tstatus:
        cursor.execute(
            "UPDATE teachers SET tname=%s, tdept=%s, tadd=%s, tcontact=%s, tstatus=%s WHERE tid=%s",
            (tname, tdept, tadd, tcontact, tstatus, tid)
        )
        conn.commit()

    elif action == "delete" and tid:
        cursor.execute( "DELETE FROM teachers WHERE tid=%s", (tid,) )
        conn.commit()
        
    elif action == "assignteacher" and tid and selected_subjid:  
        cursor.execute(
            "INSERT INTO assign (subjid, tid) VALUES (%s, %s)",
            (selected_subjid, tid)
        )
        conn.commit()
        
    # elif action == "dropstudent" and studid and selected_subjid:
    #     cursor.execute(
    #         "DELETE FROM enroll WHERE studid=%s AND subjid=%s",
    #         (studid, selected_subjid)
    #     )
    #     conn.commit()

    # read all records from teachers table
    cursor.execute("SELECT tid, tname, tdept, tadd, tcontact, tstatus FROM teachers")
    rows = cursor.fetchall()
    
    # bandaid fix for window.location.href reloading the site after the input fields are populated
    selectedteacher = None
    if tid:
        cursor.execute(
            "SELECT tid, tname, tdept, tadd, tcontact, tstatus FROM teachers WHERE tid=%s",
            (tid,)
        )
        selectedteacher = cursor.fetchone()

    if selectedteacher:
        tid_val = str(selectedteacher[0])
        tname_val = html.escape(selectedteacher[1])
        tdept_val = html.escape(selectedteacher[2])
        tadd_val = html.escape(selectedteacher[3])
        tcontact_val = html.escape(selectedteacher[4])
        tstatus_val = html.escape(selectedteacher[5])
    else:
        tid_val = str(next_tid)
        tname_val = tdept_val = tadd_val = tcontact_val = tstatus_val = ""

    # get the data to populate the assigned subjects table for the selected teacher
    assignedsubjects = []
    if tid:
        cursor.execute(
            """SELECT a.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched 
               FROM assign a JOIN subjects s ON a.subjid = s.subjid 
               WHERE a.tid=%s""",
            (tid,)
        )
        assignedsubjects = cursor.fetchall()

    # for hiding assign button for teachers already assigned to a subject
    assigned_subj_ids = [str(s[0]) for s in assignedsubjects]

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
        const assignedsubjects = """ + str(assigned_subj_ids) + """;
        
        // copies data into the input fields to allow updating
        function fillFormTeachers(tid, tname, tdept, tadd, tcontact, tstatus) {
            document.getElementById("tid").value = tid;
            document.getElementById("tname").value = tname;
            document.getElementById("tdept").value = tdept;
            document.getElementById("tadd").value = tadd;
            document.getElementById("tcontact").value = tcontact;
            document.getElementById("tstatus").value = tstatus;
                 
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            
            // update the url if a teacher is selected  
            window.location.href = `teachers.py?tid=${studid || ''}&subjid=${subjid || ''}`;

            const btn = document.getElementById("assignbtn");

            // make assignbtn visible if teacher is selected. if no teacher selected, show ?
            // if already assigned, hide
            if (subjid) {
                if (assignedsubjects.includes(subjid)) {
                    btn.style.display = "none";
                } else {
                    btn.style.display = "inline-block";
                    btn.value = `Assign Teacher ID: ${tid || '?'} to Subject ID: ${subjid}`;
                }
            } else {
                btn.style.display = "none";
            }
        }
        
        function assignTeacher() {
           const params = new URLSearchParams(window.location.search);
           document.getElementById('subjid').value = params.get('subjid');
           
           // set the hidden action to assignteacher then execute
           document.getElementById('action').value = 'assignteacher';
           document.querySelector("form").submit();
        }
        
        // function dropStudent() {
        //     // set the hidden action to dropstudent then execute
        //     document.getElementById('action').value = 'dropstudent';
        //     document.querySelector("form").submit();
        // }
        
        // function selectSubjectToDrop(enrolledsubjid) {
        //     const params = new URLSearchParams(window.location.search);
        //     const studid = params.get('studid');
        //     const enrollbtn = document.getElementById("enrollbtn");
        //     const dropbtn = document.getElementById("dropbtn");
        //     
        //     // show the dropbtn ONLY if you select a student then one enrolled subject
        //     if (studid && enrolledsubjid) {
        //         enrollbtn.style.display = "none";
        //         dropbtn.style.display = "inline-block";
        //         dropbtn.value = `Drop Student ID: ${studid} from Subject ID: ${enrolledsubjid}`;
        //         
        //         // store this in the hidden form field for dropSubject()
        //         document.getElementById('subjid').value = enrolledsubjid;
        //     }
        // }
        
        // show the current teacher id (if it exists) when the page is loaded
        window.addEventListener("load", () => {
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const tid = params.get("tid");
            
            const btn = document.getElementById("assignbtn");

            // make assignbtn visible if teacher is selected. if no teacher selected, show ?. if already assigned, hide.
            if (subjid && tid) {
                if (enrolledsubjects.includes(subjid)) {
                    btn.style.display = "none";
                } else {
                    btn.style.display = "inline-block";
                    btn.value = `Assign Teacher ID: ${tid || '?'} to Subject ID: ${subjid}`;
                }
            } else {
                btn.style.display = "none";
            }
        });
        </script>
    </head>
    <body>
    <table width="100%" cellpadding="10">
        <tr>
            <td colspan="2" style="padding: 10px 5px;">
                <a id="studentformurl" href="students.py">Students</a>
                <a href="subjects.py">Subjects</a>
                <span>Teachers</span>
            </td>
        </tr>
        <tr>
            <td width="30%" valign="top">
                <h3>Teachers Form</h3>
                <!-- submit data back to this script -->
                <form action="teachers.py" method="post">
                    Teacher ID:<br>
                    <input type="text" name="tid" id="tid" readonly value="""+tid_val+"""><br>
                    Teacher Name:<br>
                    <input type="text" name="tname" id="tname" value="""+tname_val+"""><br>
                    Teacher Department:<br>
                    <input type="text" name="tdept" id="tdept" value="""+tdept_val+"""><br><br>
                    Teacher Address:<br>
                    <input type="text" name="tadd" id="tadd" value="""+tadd_val+"""><br><br>
                    Teacher Contact:<br>
                    <input type="text" name="tcontact" id="tcontact" value="""+tcontact_val+"""><br><br>
                    Teacher Status:<br>
                    <input type="text" name="tstatus" id="tstatus" value="""+tstatus_val+"""><br><br>
                    
                    <!-- insert,update,delete buttons -->
                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                    <input type="hidden" name="action" id="action" value="">
                    <input type="hidden" name="subjid" id="subjid">
                    
                    <!-- form.submit will send the data back -->
                    <input type="button" id="assignbtn" value="" style="display:none;" onclick="assignTeacher()">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Teachers Table</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>Teacher ID</th>
                        <th>Name</th>
                        <th>Department</th>
                        <th>Address</th>
                        <th>Contact</th>
                        <th>Status</th>
                    </tr>
    """)

    # clicking a row fills the form fields/input boxes
    for i in range(len(rows)):
        tid_val = str(rows[i][0])
        tname_val = str(rows[i][1])
        tdept_val = html.escape(str(rows[i][2]))
        tadd_val = html.escape(str(rows[i][3]))
        tcontact_val = html.escape(str(rows[i][4]))
        tstatus_val = str(rows[i][5])

        print(
            "<tr onclick=\"fillFormTeachers('{}','{}','{}','{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(tid_val, tname_val, tdept_val, tadd_val, tcontact_val, tstatus_val)
        )
        print("<td>" + tid_val + "</td>")
        print("<td>" + tname_val + "</td>")
        print("<td>" + tdept_val + "</td>")
        print("<td>" + tadd_val + "</td>")
        print("<td>" + tcontact_val + "</td>")
        print("<td>" + tstatus_val + "</td>")
        print("</tr>") # close the table row

    print("""
                </table>
            </td>
        </tr>
        
        <tr>
            <td width="30%"></td> <!-- empty cell to align with form -->
            <td width="70%" valign="top">
                <h3>Assigned Subjects</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>Subject ID</th>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Units</th>
                        <th>Schedule</th>
                    </tr>                 
        """)
    
    # # clicking a teacher shows their assigned subjects
    # for subject in enrolledsubjects:
    #     subjid_val = str(subject[0])
    #     subjcode_val = html.escape(str(subject[1]))
    #     subjdesc_val = html.escape(str(subject[2]))
    #     subjunits_val = str(subject[3])
    #     subjsched_val = html.escape(str(subject[4]))
    #     print(f"<tr onclick=\"selectSubjectToDrop('{subjid_val}')\" style=\"cursor:pointer;\">")
    #     print("<td>" + subjid_val + "</td>")
    #     print("<td>" + subjcode_val + "</td>")
    #     print("<td>" + subjdesc_val + "</td>")
    #     print("<td>" + subjunits_val + "</td>")
    #     print("<td>" + subjsched_val + "</td>")
    #     print("</tr>") 
        
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
