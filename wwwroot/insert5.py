#!/usr/bin/env python3

import cgi
import mysql.connector
import html

print("Content-Type: text/html\n")

form = cgi.FieldStorage()
action = form.getvalue("action", "")
name = html.escape(form.getvalue("name", ""))
age = form.getvalue("age", "")
email = html.escape(form.getvalue("email", ""))

try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="sample"
    )

    cursor = conn.cursor()

    if action == "insert" and name and age and email:
        cursor.execute(
            "INSERT INTO users (name, age, email) VALUES (%s, %s, %s)",
            (name, age, email)
        )
        conn.commit()

    elif action == "update" and name and age and email:
        cursor.execute(
            "UPDATE users SET name=%s, age=%s WHERE email=%s",
            (name, age, email)
        )
        conn.commit()

    elif action == "delete" and email:
        cursor.execute(
            "DELETE FROM users WHERE email=%s",
            (email,)
        )
        conn.commit()

    cursor.execute("SELECT name, age, email FROM users")
    rows = cursor.fetchall()

    print("""
    <html>
    <script>
    function fillForm(name, age, email) {
        document.getElementById("name").value = name;
        document.getElementById("age").value = age;
        document.getElementById("email").value = email;
    }
    </script>

    <body>
    <table width="100%" cellpadding="10">
        <tr>
            <td width="30%" valign="top">
                <h3>Add User</h3>
                <form action="insert5.py" method="post">
                    Name:<br>
                    <input type="text" name="name" id="name"><br>
                    Age:<br>
                    <input type="text" name="age" id="age"><br>
                    Email:<br>
                    <input type="text" name="email" id="email"><br><br>

                    <input type="hidden" name="action" id="action">

                    <input type="submit" value="Insert"
                        onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update"
                        onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete"
                        onclick="document.getElementById('action').value='delete'">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Users Table</h3>
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>Name</th>
                        <th>Age</th>
                        <th>Email</th>
                    </tr>
    """)

    for i in range(len(rows)):
        name_val = html.escape(rows[i][0])
        age_val = str(rows[i][1])
        email_val = html.escape(str(rows[i][2]))

        print(
            "<tr onclick=\"fillForm('{}','{}','{}')\" style=\"cursor:pointer;\">"
            .format(name_val, age_val, email_val)
        )
        print("<td>" + name_val + "</td>")
        print("<td>" + age_val + "</td>")
        print("<td>" + email_val + "</td>")
        print("</tr>")

    print("""
                </table>
            </td>
        </tr>
    </table>
    </body>
    </html>
    """)

except Exception as e:
    print("<h2>Error</h2>")
    print(f"<pre>{e}</pre>")

finally:
    if 'conn' in locals():
        conn.close()


