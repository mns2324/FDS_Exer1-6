import cgi
import mysql.connector
import html
print("Content-Type: text/html")
print("")
form = cgi.FieldStorage()
action = form.getvalue("action", "")

subjid = form.getfirst("subjid", "")
subjcode = form.getvalue("subjcode", "")
subjdesc = form.getvalue("subjdesc", "")
subjunit = form.getvalue("subjunit", "")
subjsched = form.getvalue("subjsched", "")
std_url = "students.py"


try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="student_information_system"
    )
    cursor = conn.cursor()
    cursor.execute("select coalesce(max(subjid),1999) +1 from subjects")
    nextSubjID = cursor.fetchone()[0]

    if action == "insert" and subjcode and subjdesc and subjunit and subjsched:
        cursor.execute(
            "INSERT INTO subjects (subjid,subjcode, subjdesc, subjunits, subjsched) VALUES (%s, %s, %s, %s, %s)",
            (nextSubjID, subjcode, subjdesc, subjunit, subjsched)
        )
        conn.commit()
        subjid = ""
    elif action == "update" and subjid and subjcode and subjdesc and subjunit and subjsched:
        cursor.execute(
            "UPDATE subjects SET subjcode=%s, subjdesc=%s, subjunits=%s, subjsched=%s WHERE subjid=%s",
            (subjcode, subjdesc, subjunit, subjsched, subjid)
        )
        conn.commit()
        subjid = ""
    elif action == "delete" and subjid:
        cursor.execute(
            "DELETE FROM subjects WHERE subjid=%s",
            (subjid,)
        )
        conn.commit()
        cursor.execute(
            "DELETE FROM enroll WHERE subjid=%s",
            (subjid,)
        )
        subjid = ""
    
    

    if subjid and action == "":
        cursor.execute(
            "SELECT * FROM subjects WHERE subjid=%s",
            (subjid,)
        )
        subject = cursor.fetchone()
        if subject:
            subjid, subjcode, subjdesc, subjunit, subjsched = subject
            std_url += f"?subjid={subjid}"
            nextSubjID = subjid

    cursor.execute("select * from subjects")
    subjects = cursor.fetchall()
    cursor.execute("Select * from enroll")
    enrollTbl = cursor.fetchall()

    
    print(f"""
    <html>
    <head>
    <title>Subject Management</title>
    <link rel ="stylesheet" href="styles.css">
    </head>
    <body>
        <table width="100%" cellpadding="10">
        <tr>
        <td width="30%" valign="top">
        <h1>Subject Management</h1>
        <a href="{std_url}"><h2>Students</h2></a> 
        
        <form method="post" action="subjects.py">
            <input type="hidden" name="action" id="action" value="">
            Subject ID: <input type="text" name="subjid" value="{nextSubjID}" readonly><br>
            Subject Code:<input type="text" name="subjcode" value="{subjcode}" ><br>
            Subject Description: <input type="text" name="subjdesc" value="{subjdesc}" ><br>
            Subject Units: <input type="number" name="subjunit" value="{subjunit}" ><br>
            Subject Schedule: <input type="text" name="subjsched" value="{subjsched}" ><br>
            
             <input type="submit" value="Add Subject" onclick="document.getElementById('action').value='insert'">
            <input type="submit" value="Update Subject" onclick="document.getElementById('action').value='update'">
            <input type="submit" value="Delete Subject" onclick="document.getElementById('action').value='delete'">
        </form>
        </td>
        <td width="70%" valign="top">
        <h1>Subjects List</h1>
        <table border="1" cellpadding="5" cellspacing="0" width="75%">
            <tr>
                <th>Subject ID</th>
                <th>Code</th>
                <th>Description</th>
                <th>Units</th>
                <th>Schedule</th>
                <th>Number Of Students</th>
            </tr>
            
    """)
    for subject in subjects:
        subjid, subjcode, subjdesc, subjunit, subjsched = subject
        cursor.execute(
            "SELECT COUNT(*) FROM enroll WHERE subjid=%s", (subjid,))
        count = cursor.fetchone()[0]
        print(f"""
            <tr onclick="window.location='subjects.py?subjid={subjid}'" style="cursor:pointer;">
                <td>{subjid}</td>
                <td>{subjcode}</td>
                <td>{subjdesc}</td>
                <td>{subjunit}</td>
                <td>{subjsched}</td>
                <td>{count}</td>
            </tr>
        """)
    print(f"""
        </table>
        <h1> Students Enrolled in Subjects</h1>
        <table border="1" cellpadding="5" cellspacing="0" width="75%">
          <tr>
          <th>Student Id</th>
            <th>Name</th>
            <th>Address</th>
            <th>Course</th>
            <th>Gender</th>
            <th>Year Level</th>
          </tr>
          """)
    for enroll in enrollTbl:
        enroll_id, enroll_studid, enroll_subjid, enroll_eval = enroll
        
        if subjid != "":

            if enroll_subjid == int(subjid):
                
                cursor.execute(
                    "SELECT * FROM students WHERE studid=%s",
                    (enroll_studid,)
                )
                student = cursor.fetchone()
                if student:
                    
                    stdid, name, address, course, gender, year_level = student
                print(f"""
                <tr>
                <td>{stdid}</td>
                <td>{html.escape(name)}</td>
                <td>{html.escape(address)}</td>
                <td>{html.escape(course)}</td>
                <td>{html.escape(gender)}</td>
                <td>{html.escape(year_level)}</td>
                </tr>
            """)
    print("""
          </table>
        </td>
        </tr>
        </table>
    </body></html>
    """)
except Exception as e:
    print("<h1>Error</h1>")
    print(f"<pre>{e}</pre>")
finally:
    if 'conn' in locals():
        conn.close()
