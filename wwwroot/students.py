import cgi
import mysql.connector
import html

print("Content-Type: text/html")
print("")
form = cgi.FieldStorage()
action = form.getvalue("action", "")
std_id = form.getvalue("stdid", "")
name = form.getvalue("stdname", "")
address = form.getvalue("stdaddress", "")
student_course = form.getvalue("stdcourse", "")
gender = form.getvalue("stdgender", "")
year_level = form.getvalue("stdyearlevel", "")
subj_id = form.getvalue("subjid", "")



try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="student_information_system"
    )
    
    cursor = conn.cursor()

    cursor.execute("select coalesce(max(studid),999) +1 from students")
    next_std_id = cursor.fetchone()[0]

    if action == "enroll" and std_id and subj_id:
        cursor.execute(
            "INSERT INTO enroll (studid, subjid) VALUES (%s, %s)",
            (std_id, subj_id,)
        )
        
        std_id = ""
        
    
        conn.commit()
    elif action == "insert" and std_id and name and address and student_course and gender and year_level:
        std_id = next_std_id
        cursor.execute(
            "INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)",
            (std_id, name, address, student_course, gender, year_level,)
        )
        conn.commit()
        std_id = ""


    elif action == "update" and std_id and name and address and student_course and gender and year_level:
        cursor.execute(
            "UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s",
            (name, address, student_course, gender, year_level, std_id,)
        )
        conn.commit()
        std_id = ""
   


    elif action == "delete" and std_id:
        cursor.execute(
            "DELETE FROM enroll WHERE studid=%s",
            (std_id,)
        )
        cursor.execute(
            "DELETE FROM students WHERE studid=%s",
            (std_id,)
        )
        conn.commit()
        std_id = ""

    elif action == "drop" and std_id and subj_id:
        cursor.execute(
            "DELETE FROM enroll WHERE studid=%s AND subjid=%s",
            (std_id, subj_id)
        )
        conn.commit()
        std_id = ""
        subj_id = ""

    

    if std_id and action == "":
        cursor.execute(
            "SELECT * FROM students WHERE studid=%s",
            (std_id,)
        )
        student = cursor.fetchone()
        if student:
            std_id, name, address, student_course, gender, year_level = student
            next_std_id = std_id
            
    

    cursor.execute("SELECT * FROM students")
    stdTble = cursor.fetchall()
    cursor.execute("Select * from enroll")
    enrollTble = cursor.fetchall()
    drop_exists = False
    if std_id and subj_id:
        for enroll in enrollTble:
            enroll_id, enroll_studid, enroll_subjid, enroll_eval= enroll
            if enroll_studid == int(std_id) and enroll_subjid == int(subj_id):
                drop_exists = True
    print(f"""<!DOCTYPE html>
          
          
          <html>
          <head>
          <title>Student Information System</title>
          <link rel="stylesheet" type="text/css" href="styles.css">
          </head>
          <body>
          <table width="100%" cellpadding="10">
            <tr>
            <td width="30%" valign="top">  
            <h1>Student Information System</h1>
            <a href="subjects.py"><h2>Subjects</h2></a>
            <form action="students.py" method="post">
            student ID: 
            <input type="text" id="stdid" name="stdid" readonly="readonly" value="{next_std_id}"><br>
            
            Name: <input type="text" id="stdname"name="stdname" value="{name}"><br>
            Address: <input type="text" id="stdaddress" name="stdaddress" value="{address}"><br>
            Student Course: <input type="text" id="stdcourse" name="stdcourse" value="{student_course}"><br>
            Gender: <input type="text" id="stdgender" name="stdgender" value="{gender}"><br>
            Year Level: <input type="text" id="stdyearlevel" name="stdyearlevel" value="{year_level}"><br>

            <input type="hidden" name="action" id="action">

            <input type="submit" value="insert" onclick="document.getElementById('action').value='insert'">
            <input type="submit" value="update" onclick="document.getElementById('action').value='update'">
            <input type="submit" value="delete" onclick="document.getElementById('action').value='delete'">
            
           """)
    if (subj_id):
        disabled = ""
        display_stdid = std_id
        if not std_id:
            display_stdid = "???"
            disabled = "disabled"
        if drop_exists:
            print(f"""
            <input type="hidden" name="subjid" value="{subj_id}">
            <input type="submit" value="drop Student ID: {display_stdid} from Subject ID: {subj_id}" onclick="document.getElementById('action').value='drop'">""")
        else:
            print(f"""
            <input type="hidden" name="subjid" value="{subj_id}">s
            <input type="submit" value="enroll Student ID: {display_stdid} into Subject ID: {subj_id}" onclick="document.getElementById('action').value='enroll'" {disabled}>
        
""")
    print(f"""
          </form>
          </td>
          <td width="70%" valign="top">
          <h1>Students List</h1>
            <table border="1" cellpadding="5" cellspacing="0" width="75%">
            <tr>
            <th>Id</th>
            <th>Name</th>
            <th>Address</th>
            <th>Course</th>
            <th>Gender</th>
            <th>Year Level</th>
            <th>Total Units</th>
            </tr>
          """)
    
    for id_val, name_val, address_val, course_val, gender_val, year_level_val in stdTble:
        onclickURL = f"students.py?stdid={id_val}"
        if subj_id and (action != "drop" or action != "enroll"):
            onclickURL += f"&subjid={subj_id}"
        
        cursor.execute("SELECT SUM(s.subjunits) FROM subjects s JOIN enroll e ON s.subjid = e.subjid WHERE e.studid = %s", params=(id_val,))
        total_units = cursor.fetchone()[0] or 0

        print(f"<tr onclick=\"window.location.href='{onclickURL}'\" style=\"cursor:pointer;\">")
        print(f"<td>{id_val}</td>")
        print(f"<td>{html.escape(name_val)}</td>")
        print(f"<td>{html.escape(address_val)}</td>")
        print(f"<td>{html.escape(course_val)}</td>")
        print(f"<td>{html.escape(gender_val)}</td>")
        print(f"<td>{html.escape(year_level_val)}</td>")
        print(f"<td>{total_units}</td>")
        print("</tr>")
    
    print("""
          </table>
          <h1> Enrolled Subjects </h1>
          <table border="1" cellpadding="5" cellspacing="0" width="75%">
          <tr>
          <th>Subject ID</th>
                <th>Code</th>
                <th>Description</th>
                <th>Units</th>
                <th>Schedule</th>
          </tr>
            """)
    for enroll in enrollTble:
        enroll_id, enroll_studid, enroll_subjid, enroll_eval= enroll
        
        if std_id != "":
            if enroll_studid == int(std_id):
                cursor.execute(
                    "SELECT subjid, subjcode, subjdesc, subjunits, subjsched FROM subjects WHERE subjid=%s",
                    (enroll_subjid,)
                )
                subject = cursor.fetchone()
                if subject:
                    subj_id, subjcode, subjdesc, subjunit, subjsched = subject
                    print(f"""
            <tr onclick="window.location='students.py?stdid={std_id}&subjid={subj_id}'" style="cursor:pointer;">
                    <td>{subj_id}</td>
                    <td>{subjcode}</td>
                    <td>{subjdesc}</td>
                    <td>{subjunit}</td>
                    <td>{subjsched}</td>
            </tr>
            """)
    print("""
          </table>
          </td>
          </tr>
          </table>
        
          </body>
          </html>""")

except Exception as e:
    print("<h1>Error</h1>")
    print(f"<pre>{e}</pre>")
finally:
    if 'conn' in locals():
        conn.close()
