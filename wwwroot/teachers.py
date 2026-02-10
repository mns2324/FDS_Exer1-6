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
conflict_msg = ""

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
        teachuser = f"{next_tid}{tname.replace(' ', '').lower()}" # force lowercase and remove whitespace
        teachpw = f"AdDU{tname}"

        cursor.execute(
            "INSERT INTO teachers (tid, tname, tdept, tadd, tcontact, tstatus) VALUES (%s, %s, %s, %s, %s, %s)",
            (next_tid, tname, tdept, tadd, tcontact, tstatus)
        )

        cursor.execute(f"CREATE USER IF NOT EXISTS '{teachuser}'@'localhost' IDENTIFIED BY '{teachpw}'")
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, EXECUTE ON enrollmentsystem.* TO '{teachuser}'@'localhost'")
        conn.commit()

    elif action == "update" and tid and tname and tdept and tadd and tcontact and tstatus:
        cursor.execute(
            "UPDATE teachers SET tname=%s, tdept=%s, tadd=%s, tcontact=%s, tstatus=%s WHERE tid=%s",
            (tname, tdept, tadd, tcontact, tstatus, tid)
        )
        conn.commit()

    elif action == "delete" and tid:
        try:
            teachuser = f"{tid}{tname.replace(' ', '').lower()}"

            cursor.execute( "DELETE FROM teachers WHERE tid=%s", (tid,) )
            cursor.execute(f"DROP USER IF EXISTS '{teachuser}'@'localhost'")
            conn.commit()
        except Exception:
            print(f"""
                <script>
                    alert("Unable to delete teacher {tid} as they still have assigned subjects.");
                </script>
            """)
        
    elif action == "assignteacher" and tid and selected_subjid: 
        # check for schedule conflict/teacher already assigned
        result = cursor.callproc('checkconflict', [tid, selected_subjid, 1, None])
        conflict_msg = result[3]   
        
        if conflict_msg == "No conflict":
            cursor.execute(
                "INSERT INTO assign (subjid, tid) VALUES (%s, %s)",
                (selected_subjid, tid)
            )
            conn.commit()

    elif action == "unassignteacher" and tid and selected_subjid:
        cursor.execute(
            "DELETE FROM assign WHERE tid=%s AND subjid=%s",
            (tid, selected_subjid)
        )
        conn.commit()
        
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
    # for showing the conflict message span
    conflict_msg_js = ""
    
    # page load check - check conflict to control message and button visibility
    if tid and selected_subjid:
        result = cursor.callproc('checkconflict', [tid, selected_subjid, 1, None])
        conflict_msg = result[3] 
        conflict_msg_js = html.escape(conflict_msg)

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
            margin-top: 8px;
            color: purple;
        }
        </style>
        
        <script>       
        const assignedsubjects = """ + str(assigned_subj_ids) + """;
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
        function fillFormTeachers(tid, tname, tdept, tadd, tcontact, tstatus) {
            document.getElementById("tid").value = tid;
            document.getElementById("tname").value = tname;
            document.getElementById("tdept").value = tdept;
            document.getElementById("tadd").value = tadd;
            document.getElementById("tcontact").value = tcontact;
            document.getElementById("tstatus").value = tstatus;
                 
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            
            // reload page with both IDs so the server can run checkconflict
            const newUrl = subjid ? `teachers.py?tid=${tid}&subjid=${subjid}` : `teachers.py?tid=${tid}`;
            window.location.href = newUrl;
        }
        
        function assignTeacher() {
           const params = new URLSearchParams(window.location.search);
           document.getElementById('subjid').value = params.get('subjid');
           
           // set the hidden action to assignteacher then execute
           document.getElementById('action').value = 'assignteacher';
           document.querySelector("form").submit();
        }
        
        function unassignTeacher() {
            document.getElementById('action').value = 'unassignteacher';
            document.querySelector("form").submit();
        }
        
        function selectSubjectToUnassign(enrolledsubjid) {
            const params = new URLSearchParams(window.location.search);
            const tid = params.get('tid');
            const assign = document.getElementById("assignbtn");
            const unassign = document.getElementById("unassignbtn");
            
            // show the dropbtn ONLY if you select a teacher then one assigned subject
            if (tid && enrolledsubjid) {
                assign.style.display = "none";
                unassign.style.display = "inline-block";
                unassign.value = `Unassign Teacher ID: ${tid} from Subject ID: ${enrolledsubjid}`;
                
                // store this in the hidden form field for dropSubject()
                document.getElementById('subjid').value = enrolledsubjid;
            }
        }
        
        window.addEventListener("load", () => {
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const tid = params.get("tid");
            
            const assignbtn = document.getElementById("assignbtn");
            document.getElementById("unassignbtn").style.display = "none";

            // assign button logic: need both a teacher and subject selected
            if (subjid && tid) {
                // already assigned to this subject
                if (assignedsubjects.includes(subjid)) {
                    assignbtn.style.display = "none";
                // schedule conflict exists, hide button, show message
                } else if (conflictMessage && conflictMessage !== "No conflict") {
                    assignbtn.style.display = "none";
                    showConflictMessage(conflictMessage);
                // no conflict and not yet assigned 
                } else {
                    assignbtn.style.display = "inline-block";
                    assignbtn.value = `Assign Teacher ID: ${tid} to Subject ID: ${subjid}`;
                }
            } else {
                assignbtn.style.display = "none";
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
                <a href="students.py">Students</a>
                <a href="subjects.py">Subjects</a>
                <span>Teachers</span>
                <select name="createdbcombo" id="createdbcombo">
                    <option value="createdb">Create DB</option>
                    <option value="1stsem">1st Sem</option>
                    <option value="2ndsem">2nd Sem</option>
                    <option value="summer">Summer</option>
                </select><br>
                <a href="index.py" id="logoutbtn">Logout</a>
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
                    <!-- form.submit will send the data back -->
                    <input type="button" id="assignbtn" value="" style="display:none;" onclick="assignTeacher()">
                    <input type="button" id="unassignbtn" value="" style="display:none;" onclick="unassignTeacher()"><br><br>
                    <span id="conflictmsg" style="color:red;"></span>
                    
                    <input type="hidden" name="action" id="action" value="">
                    <input type="hidden" name="subjid" id="subjid">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Teachers Table for: """+conn.database+"""</h3>
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
    
    # clicking a teacher shows their assigned subjects
    for subject in assignedsubjects:
        subjid_val = str(subject[0])
        subjcode_val = html.escape(str(subject[1]))
        subjdesc_val = html.escape(str(subject[2]))
        subjunits_val = str(subject[3])
        subjsched_val = html.escape(str(subject[4]))
        print(f"<tr onclick=\"selectSubjectToUnassign('{subjid_val}')\" style=\"cursor:pointer;\">")
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
