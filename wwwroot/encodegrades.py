import sys
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

# redirect back to index if not logged in or not teacher
if not dbuser or not dbpass:
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()
    
if not (dbuser[:4].isdigit() and 2999 < int(dbuser[:4]) < 4000):
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()

tid = int(dbuser[:4])

form = cgi.FieldStorage()
action = form.getvalue("action", "")
studid = form.getvalue("studid", "")
selected_subjid = form.getvalue("subjid", "")

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    cursor = conn.cursor()
    
    if action == "savegrades" and selected_subjid and studid:
        prelim = form.getvalue("prelim", None)
        midterm = form.getvalue("midterm", None)
        prefinal = form.getvalue("prefinal", None)
        final = form.getvalue("final", None)

        # get the eid for this student and subject
        cursor.execute(
            "SELECT eid FROM enroll WHERE studid = %s AND subjid = %s",
            (studid, selected_subjid)
        )
        row = cursor.fetchone()
        
        if row:
            eid = row[0]
            
            # update grades if they already exist. if not, insert them first
            cursor.execute("SELECT gradeid FROM grades WHERE enroll_eid = %s", (eid,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE grades SET prelim=%s, midterm=%s, prefinal=%s, final=%s WHERE enroll_eid=%s",
                    (prelim, midterm, prefinal, final, eid)
                )
            else:
                cursor.execute(
                    "INSERT INTO grades (enroll_eid, prelim, midterm, prefinal, final) VALUES (%s, %s, %s, %s, %s)",
                    (eid, prelim, midterm, prefinal, final)
                )
            conn.commit()
            
            print(f"Status: 302 Found")
            print(f"Location: encodegrades.py?tid={tid}&subjid={selected_subjid}&eid={eid}&saved=1")
            print()
            exit()

    # fetch assigned subjects for this teacher
    cursor.execute(
        """SELECT a.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched
           FROM assign a JOIN subjects s ON a.subjid = s.subjid 
           WHERE a.tid = %s""",
        (tid,)
    )
    assignedsubjects = cursor.fetchall()

    # fetch students enrolled in the selected subject + their grades
    enrolledstudents = []
    if selected_subjid:
        cursor.execute(
            """SELECT s.studid, s.studname, g.prelim, g.midterm, g.prefinal, g.final, e.eid
               FROM enroll e 
               JOIN students s ON e.studid = s.studid
               LEFT JOIN grades g ON g.enroll_eid = e.eid
               WHERE e.subjid = %s""",
            (selected_subjid,)
        )
        enrolledstudents = cursor.fetchall()
        
    # get total enrolee count for each subject
    cursor.execute(
        """SELECT e.subjid, COUNT(e.studid) AS enrolledcount
           FROM enroll e
           WHERE e.subjid IN (SELECT subjid FROM assign WHERE tid = %s)
           GROUP BY e.subjid""",
        (tid,)
    )
    # assign enrolledcount value to the subjid key (e.g. 2000: 5)
    enrolledcount = {}
    for subjid_db, count in cursor.fetchall():
        enrolledcount[str(subjid_db)] = count
    
    heading = f"Enrolled Students in Subject ID: {html.escape(selected_subjid)}" if selected_subjid else "Enrolled Students: (no subject selected)"
    
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
            tr.selectedrow td { 
                background-color: #0a68f5; 
            }
            #savepopup {
                display: none;
                background-color: #0a68f5;
                color: white;
                font-style: bold;
                padding: 15px 25px;
                border-radius: 8px;
                font-size: 16px;
            }
            </style>
            
            <script>
            
            const gradeOptions = `
                <option value="">NG</option>
                <option value="A">A</option>
                <option value="B+">B+</option>
                <option value="B">B</option>
                <option value="C+">C+</option>
                <option value="C">C</option>
                <option value="D">D</option>
                <option value="F">F</option>
                <option value="FD">FD</option>
            `;

            let current_studid = null;
            let current_subjid = null;
            
            function confirmLogout() {
                if (confirm("Are you sure you want to logout?")) {
                    window.location.href = "index.py?action=logout";
                }
                return false;
            }
            
            // highlight the row that was pressed and append subjid to url
            function selectSubject(subjid) {
                if (current_subjid && current_subjid !== subjid) {
                    const previous = document.getElementById("subj" + current_subjid); 
                    if (previous) previous.classList.remove("selectedrow");
                }
                current_subjid = subjid;
                document.getElementById("subj" + subjid).classList.add("selectedrow"); 
                window.location.href = `encodegrades.py?tid=""" + str(tid) + """&subjid=${subjid}`;
            }
            
            function saveGrades(studid, prelim, midterm, prefinal, final, eid) {
                // restore previous row's cells back to text
                if (current_studid && current_studid !== studid) {
                    const previous = document.getElementById("row" + current_studid);
                    if (previous) {
                        previous.classList.remove("selectedrow");
                        document.getElementById("prelim" + current_studid).textContent = document.getElementById("prelim").value || "";
                        document.getElementById("midterm" + current_studid).textContent = document.getElementById("midterm").value || "";
                        document.getElementById("prefinal" + current_studid).textContent = document.getElementById("prefinal").value || "";
                        document.getElementById("final" + current_studid).textContent = document.getElementById("final").value || "";
                    }
                }
                
                current_studid = studid;
                document.getElementById("studid").value = studid;
                document.getElementById("row" + studid).classList.add("selectedrow");
                
                // append eid without reloading so that the grade dropdowns still persist
                const params = new URLSearchParams(window.location.search);
                params.set("eid", eid);
                window.history.replaceState({}, "", `encodegrades.py?${params.toString()}`);
                
                // replace cell text with select combo boxes
                ["prelim", "midterm", "prefinal", "final"].forEach(grading => {
                    const cell = document.getElementById(grading + studid);
                    
                    let val;
                    if (grading === "prelim") val = prelim;
                    else if (grading === "midterm") val = midterm;
                    else if (grading === "prefinal") val = prefinal;
                    else if (grading === "final") val = final;
                    
                    cell.innerHTML = `<select name="${grading}" id="${grading}">${gradeOptions}</select>`;
                    
                    // save the grade value here based on which grading's combo box was used
                    document.getElementById(grading).value = val;
                });

                document.getElementById("savebtn").style.display = "block";
            }
            
            // append tid on first load, preserve subjid if already present
            window.addEventListener("load", () => {
                const params = new URLSearchParams(window.location.search);
                
                // avoid infinite reload
                if (!params.get("tid")) {
                    const subjid = params.get("subjid");
                    const newUrl = subjid 
                        ? `encodegrades.py?tid=""" + str(tid) + """&subjid=${subjid}` 
                        : `encodegrades.py?tid=""" + str(tid) + """`;
                    window.location.href = newUrl;
                }
                
                // restore subject highlight after page reload
                const subjid = params.get("subjid");
                if (subjid) {
                    const row = document.getElementById("subj" + subjid);
                    if (row) {
                        row.classList.add("selectedrow");
                        current_subjid = subjid;
                    }
                }
                
                // show save popup if grades were just saved
                if (params.get("saved") === "1") {
                    const popup = document.getElementById("savepopup");
                    popup.style.display = "block";
                    setTimeout(() => { popup.style.display = "none"; }, 4000);
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
                            <a href="#" id="logoutbtn" onclick="confirmLogout();">Logout</a>
                            <span id="currentuser">CURRENT USER: """+dbuser+""" /// CURRENT DATABASE: """+conn.database+"""</span>
                        </div>
                    </td>
                </tr>
                <td width="70%" valign="top">
                    <h3>Assigned Subjects</h3>
                    <table border="1" cellpadding="5" cellspacing="0" width="100%">
                        <tr>
                            <th>ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                            <th># of Enrolled Students</th>
                        </tr>
        """)

    for subject in assignedsubjects:
        subjid_val = str(subject[0])
        subjcode_val = html.escape(str(subject[1]))
        subjdesc_val = html.escape(str(subject[2]))
        subjunits_val = str(subject[3])
        subjsched_val = html.escape(str(subject[4]))
        # get the enrolled count for the subject from the dict, 0 as default
        totalenrolled = str(enrolledcount.get(subjid_val, 0))
        print(f'<tr id="subj{subjid_val}" onclick="selectSubject(\'{subjid_val}\')" style="cursor:pointer;">')
        print("<td>" + subjid_val + "</td>")
        print("<td>" + subjcode_val + "</td>")
        print("<td>" + subjdesc_val + "</td>")
        print("<td>" + subjunits_val + "</td>")
        print("<td>" + subjsched_val + "</td>")
        print("<td>" + totalenrolled + "</td>")
        print("</tr>") 
        
    print("""
                    </table>
                </td>
            </tr>
            
            <tr>
                <td width="70%" valign="top">
                    <h3>"""+heading+"""</h3>
                    <div style="display:flex; align-items:flex-end; gap:15px; margin-bottom:10px;">
                        <h4 style="color:cyan; margin:0;"> Click a student row to edit grades. Save button will appear below the table. </h4>
                        <div id="savepopup">Grades saved successfully!</div>
                    </div>
                    <form action="encodegrades.py" method="post" id="gradeForm">
                        <input type="hidden" name="studid" id="studid">
                        <input type="hidden" name="subjid" value="""+selected_subjid+""">
                        <input type="hidden" name="action" value="savegrades">
                        <table border="1" cellpadding="5" cellspacing="0" width="100%">
                            <tr>
                                <th width="10%">ID</th>
                                <th width="30%">Name</th>
                                <th width="15%">Prelim</th>
                                <th width="15%">Midterm</th>
                                <th width="15%">Prefinal</th>
                                <th width="15%">FINAL</th>
                            </tr>                        
    """)
        
    for student in enrolledstudents:
        studid_val = str(student[0])
        studname_val = html.escape(str(student[1]))
        prelim_val = str(student[2] or "")
        midterm_val = str(student[3] or "")
        prefinal_val = str(student[4] or "")
        final_val = str(student[5] or "")
        eid_val = str(student[6]) # to append to the url
        
        prelim_display = prelim_val or ""
        midterm_display = midterm_val or ""
        prefinal_display = prefinal_val or ""
        final_display = final_val or ""
        
        # the ids are there to identify which student a row belongs to when displaying the combo boxes
        print(f'<tr id="row{studid_val}" style="cursor:pointer;">')
        print(f'<td onclick="saveGrades(\'{studid_val}\', \'{prelim_val}\', \'{midterm_val}\', \'{prefinal_val}\', \'{final_val}\', \'{eid_val}\')">' + studid_val + "</td>")
        print(f'<td onclick="saveGrades(\'{studid_val}\', \'{prelim_val}\', \'{midterm_val}\', \'{prefinal_val}\', \'{final_val}\', \'{eid_val}\')">' + studname_val + "</td>")
        print(f'<td id="prelim{studid_val}">' + prelim_display + "</td>")
        print(f'<td id="midterm{studid_val}">' + midterm_display + "</td>")
        print(f'<td id="prefinal{studid_val}">' + prefinal_display + "</td>")
        print(f'<td id="final{studid_val}">' + final_display + "</td>")
        print("</tr>")

    print("""
                        </table>
                        <div id="savebtn" style="display:none; margin-top:10px;">
                            <input type="submit" value="Save Grades">
                        </div>
                    </form>
                </td>
            </tr>
        </body>
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