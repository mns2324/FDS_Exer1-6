#!/usr/bin/env python3

import cgi
import mysql.connector
import html
import traceback
from datetime import datetime
import os
import http.cookies
import json as _json

# decision trees that votes on predictions
from sklearn.ensemble import RandomForestClassifier
# converts lists of subject IDs (multi-label targets) into a binary matrix the model can learn from
from sklearn.preprocessing import MultiLabelBinarizer
# converts categorical inputs (gender, course, year level) into numeric vectors
from sklearn.preprocessing import OneHotEncoder
# used here specifically for accuracy_score to evaluate the trained model
from sklearn import metrics
# serializes (saves/loads) the trained model to/from disk as a .pkl file
import joblib
# loads raw SQL query results into a DataFrame for easy data manipulation and grouping
import pandas as pd

cookies = http.cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))

dbuser = cookies["dbuser"].value if "dbuser" in cookies else ""
dbpass = cookies["dbpass"].value if "dbpass" in cookies else ""
selected_db_from_index = cookies["schoolyearcombo"].value if "schoolyearcombo" in cookies else "enrollmentsystem"

# redirect back to index if not logged in
if not dbuser or not dbpass:
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()

# if student, redirect to studrec to show the pdf
if dbuser[:4].isdigit() and 999 < int(dbuser[:4]) < 2000:
    print("Status: 302 Found")
    print("Location: studrec.py")
    print()
    exit()

# if teacher, redirect to encodegrades
if dbuser[:4].isdigit() and 2999 < int(dbuser[:4]) < 4000:
    print("Status: 302 Found")
    print("Location: encodegrades.py")
    print()
    exit()

form   = cgi.FieldStorage()
action = form.getvalue("action", "")

studid         = form.getvalue("studid", "")
selected_subjid = form.getvalue("subjid")
conflict_msg   = ""

studname    = html.escape(form.getvalue("studname", ""))
studaddress = html.escape(form.getvalue("studaddress", ""))
studcourse  = html.escape(form.getvalue("studcourse", ""))
studgender  = html.escape(form.getvalue("studgender", ""))
yearlevel   = form.getvalue("yearlevel", "")

createdbcombo = form.getvalue("createdbcombo", "")
current_year  = str(datetime.now().year)
next_year     = str(datetime.now().year + 1)

# trains a mlm to learn which subjects students typically enroll in, 
# based on their gender, course, and year level
if action == "trainmodel":
    print("Content-Type: application/json\n")
    
    # if the model is retrained, the old pkl is removed
    stale = os.path.join("ai_models", "enroll_model.pkl")
    if os.path.exists(stale):
        os.remove(stale)

    train_db = form.getvalue("traindb", "")
    if not train_db:
        print(_json.dumps({"error": "No training database specified."}))
        exit()

    try:
        train_conn   = mysql.connector.connect(
            host="localhost", user=dbuser, password=dbpass, database=train_db
        )
        train_cursor = train_conn.cursor()
        # fetch (gender, course, yearlevel, subjid) from students with enrolled subjects
        train_cursor.execute("""
            SELECT st.studgender, st.studcrs, st.yrlvl, e.subjid
            FROM students st
            JOIN enroll e ON st.studid = e.studid
        """)
        raw_rows = train_cursor.fetchall()
        train_conn.close()
    except Exception as ex:
        print(_json.dumps({"error": str(ex)}))
        exit()

    if not raw_rows:
        print(_json.dumps({"error": "No enrolled data found in the selected database."}))
        exit()

    # raw rows are loaded into a pandas DataFrame
    df = pd.DataFrame(raw_rows, columns=["gender", "course", "yearlevel", "subjid"])
    # normalize all entries
    df["gender"]    = df["gender"].str.strip().str.lower()
    df["course"]    = df["course"].str.strip().str.lower()
    df["yearlevel"] = df["yearlevel"].astype(str).str.strip().str.lower()
    yr_map = {"1": "1st", "2": "2nd", "3": "3rd", "4": "4th"}
    df["yearlevel"] = df["yearlevel"].replace(yr_map)
    # any row that has missing values are dropped immediately
    df = df.dropna(subset=["gender", "course", "yearlevel", "subjid"])

    grouped = (
        df.groupby(["gender", "course", "yearlevel"])["subjid"]
        .apply(lambda s: sorted(s.unique().tolist()))
        .reset_index()
    )

    # OneHotEncoder converts each category into a binary vector
    # all three columns are encoded and concatenated into one flat numeric vector per row
    X     = grouped[["gender", "course", "yearlevel"]].values.tolist()
    y_raw = grouped["subjid"].tolist()
    enc   = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    X_enc = enc.fit_transform(X)

    # MultiLabelBinarizer converts this into a binary matrix where each column represents one possible subject id
    # 1 in a column means that profile enrolled in that subject, 0 means they didn't
    mlb = MultiLabelBinarizer()
    Y   = mlb.fit_transform(y_raw)

    # RandomForestClassifier trains 100 decision trees (n_estimators=100) on the encoded data.
    # each tree learns slightly different patterns due to random sampling, and their predictions are averaged/voted on at inference time
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_enc, Y)
    Y_pred   = clf.predict(X_enc)
    accuracy = float(metrics.accuracy_score(Y, Y_pred))

    # the classifier, the input encoder, and the output binarizer are saved together in one .pkl file
    model_dir = "ai_models"
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump({"clf": clf, "enc": enc, "mlb": mlb},
                os.path.join(model_dir, "enroll_model.pkl"))

    # response JSON tells the frontend the accuracy and which database was used
    print(_json.dumps({"accuracy": round(accuracy * 100, 2), "trained_on": train_db}))
    exit()
    
try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )

    # aienroll returns JSON. print its header now, before any HTML
    if action == "aienroll":
        print("Content-Type: application/json\n")
    else:
        print("Content-Type: text/html\n")

    if action in ("insert", "delete"):
        root_conn = mysql.connector.connect(
            host="localhost", user="root", password="root"
        )
        root_cursor = root_conn.cursor()

    cursor = conn.cursor()

    # get next student id (no auto increment)
    cursor.execute("SELECT COALESCE(MAX(studid), 999) + 1 FROM students")
    next_studid = cursor.fetchone()[0]

    # crud operations
    if action == "insert" and studname and studaddress and studcourse and studgender and yearlevel:
        try:
            studuser = f"{next_studid}{studname.strip().lower()}"
            studpw   = f"AdDU{studname}"

            cursor.execute(
                "INSERT INTO students (studid, studname, studadd, studcrs, studgender, yrlvl) VALUES (%s, %s, %s, %s, %s, %s)",
                (next_studid, studname, studaddress, studcourse, studgender, yearlevel)
            )
            conn.commit()

            root_cursor.execute("CREATE USER IF NOT EXISTS %s@`localhost` IDENTIFIED BY %s", (studuser, studpw))
            root_cursor.execute("GRANT SELECT ON `{}`.* TO %s@`localhost`".format(selected_db_from_index), (studuser,))
            root_cursor.execute("GRANT UPDATE (evaluation) ON `{}`.enroll TO %s@`localhost`".format(selected_db_from_index), (studuser,))
            root_conn.commit()

        except mysql.connector.Error:
            if dbuser[:4].isdigit():
                id = int(dbuser[:4])
                if 999 < id < 2000:
                    print(f'<script>alert("Unable to insert student {studid}. You do not have the granted permissions.");</script>')

    elif action == "update" and studid and studname and studaddress and studcourse and studgender and yearlevel:
        cursor.execute(
            "UPDATE students SET studname=%s, studadd=%s, studcrs=%s, studgender=%s, yrlvl=%s WHERE studid=%s",
            (studname, studaddress, studcourse, studgender, yearlevel, studid)
        )
        conn.commit()

    elif action == "delete" and studid:
        try:
            studuser = f"{studid}{studname.strip().lower()}"

            cursor.execute("SELECT COUNT(*) FROM enroll WHERE studid = %s", (studid,))
            if cursor.fetchone()[0] > 0:
                print(f'<script>alert("Unable to delete student {studid}. They still have enrolled subjects.");</script>')
            else:
                cursor.execute("DELETE FROM students WHERE studid = %s", (studid,))
                conn.commit()

                try:
                    root_cursor.execute("REVOKE SELECT ON `{}`.* FROM %s@`localhost`".format(selected_db_from_index), (studuser,))
                    root_conn.commit()
                except mysql.connector.Error:
                    pass

                root_cursor.execute(f"SHOW GRANTS FOR `{studuser}`@`localhost`")
                grants = root_cursor.fetchall()
                remaining_db_access = any(
                    "GRANT SELECT ON `" in grant[0] and "_sy" in grant[0] for grant in grants
                )
                if not remaining_db_access:
                    root_cursor.execute(f"DROP USER IF EXISTS `{studuser}`@`localhost`")
                    root_conn.commit()

        except mysql.connector.Error:
            if dbuser != "root":
                print(f'<script>alert("Unable to delete student {studid}. You do not have the granted permissions.");</script>')

    elif action == "aienroll" and studid:
        # check if the pkl exists before enrolling
        model_path = os.path.join("ai_models", "enroll_model.pkl")
        if not os.path.exists(model_path):
            print(_json.dumps({"error": "Model not trained yet. Please train the model first."}))
            exit()

        # fetch "features" of selected student
        cursor.execute(
            "SELECT studgender, studcrs, yrlvl FROM students WHERE studid = %s", (studid,)
        )
        stud_row = cursor.fetchone()
        if not stud_row:
            print(_json.dumps({"error": "Student not found."}))
            exit()

        # the saved .pkl is loaded and unpacked into its three components
        gender, course, yr = stud_row
        model_data = joblib.load(model_path)
        clf = model_data["clf"]
        enc = model_data["enc"]
        mlb = model_data["mlb"]

        # normalize the year levels
        yr_map = {"1": "1st", "2": "2nd", "3": "3rd", "4": "4th"}
        yr_normalized = yr_map.get(str(yr).strip(), str(yr).strip().lower())

        # student's profile is assembled into a single-row list, passed through the saved encoder
        # then predicted by the classifier. inverse_transform converts the binary output vector back into actual subject ids
        X_new = enc.transform([[
            str(gender).strip().lower(),
            str(course).strip().lower(),
            yr_normalized
        ]])
        Y_pred = clf.predict(X_new)
        inverse = mlb.inverse_transform(Y_pred)
        
        # if the prediction returns nothing, fall back to probability scores
        if not inverse or len(inverse[0]) == 0:
            # predict_proba returns per-class probabilities for each subject
            # any subject where the probability of enrollment is >= 0.3 gets included
            proba = clf.predict_proba(X_new)
            predicted_indices = [
                i for i, p in enumerate(proba)
                if p[0][1] >= 0.3
            ]
            if predicted_indices:
                predicted_subj_ids = [int(mlb.classes_[i]) for i in predicted_indices]
            else:
                print(_json.dumps({"error": f"Model returned no subjects for profile (gender={gender}, course={course}, year={yr}). Please retrain with more data."}))
                exit()
        else:
            predicted_subj_ids = [int(s) for s in inverse[0]]

        # for each predicted subject, three things are checked:
        # is the student already enrolled to the subject? skip
        # does it conflict with an existing enrolled subject's sched? skip
        # passes both checks? go through with the enrollment
        cursor.execute("SELECT subjid FROM enroll WHERE studid = %s", (studid,))
        already_enrolled = {row[0] for row in cursor.fetchall()}
        enrolled         = []
        skipped_conflict = []
        skipped_enrolled = []

        for sid in predicted_subj_ids:
            if sid in already_enrolled:
                skipped_enrolled.append(sid)
                continue
            result = cursor.callproc('checkconflict', [studid, sid, 0, None])
            msg    = result[3]
            if msg == "No conflict":
                cursor.execute(
                    "INSERT INTO enroll (studid, subjid, evaluation) VALUES (%s, %s, NULL)",
                    (studid, sid)
                )
                conn.commit()
                enrolled.append(sid)
            else:
                skipped_conflict.append(sid)

        print(_json.dumps({
            "enrolled":         enrolled,
            "skipped_conflict": skipped_conflict,
            "skipped_enrolled": skipped_enrolled
        }))
        exit()

    elif action == "enrollstudent" and studid and selected_subjid:
        result       = cursor.callproc('checkconflict', [studid, selected_subjid, 0, None])
        conflict_msg = result[3]

        if conflict_msg == "No conflict":
            cursor.execute(
                "INSERT INTO enroll (studid, subjid, evaluation) VALUES (%s, %s, NULL)",
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

    cursor.execute(
        """SELECT st.studid, COALESCE(SUM(s.subjunits),0) AS total_units
           FROM students st
           LEFT JOIN enroll e ON st.studid = e.studid
           LEFT JOIN subjects s ON e.subjid = s.subjid
           GROUP BY st.studid"""
    )
    studentunits = {}
    for studid_db, total_units in cursor.fetchall():
        studentunits[str(studid_db)] = total_units

    selectedstudent = None
    if studid:
        cursor.execute(
            "SELECT studid, studname, studadd, studcrs, studgender, yrlvl FROM students WHERE studid=%s",
            (studid,)
        )
        selectedstudent = cursor.fetchone()

    if selectedstudent:
        studid_val      = str(selectedstudent[0])
        studname_val    = html.escape(selectedstudent[1])
        studaddress_val = html.escape(selectedstudent[2])
        studcourse_val  = html.escape(selectedstudent[3])
        studgender_val  = html.escape(selectedstudent[4])
        yearlevel_val   = str(selectedstudent[5])
    else:
        studid_val      = str(next_studid)
        studname_val    = studaddress_val = studcourse_val = studgender_val = yearlevel_val = ""

    enrolledsubjects = []
    if studid:
        cursor.execute(
            """SELECT e.subjid, s.subjcode, s.subjdesc, s.subjunits, s.subjsched
               FROM enroll e JOIN subjects s ON e.subjid = s.subjid
               WHERE e.studid=%s""",
            (studid,)
        )
        enrolledsubjects = cursor.fetchall()

    enrolled_subj_ids = [str(s[0]) for s in enrolledsubjects]
    conflict_msg_js   = ""

    if studid and selected_subjid and action != "enrollstudent":
        result          = cursor.callproc('checkconflict', [studid, selected_subjid, 0, None])
        conflict_msg    = result[3]
        conflict_msg_js = html.escape(conflict_msg)

    if 'root_cursor' in locals():
        root_cursor.close()
    if 'root_conn' in locals():
        root_conn.close()

    # fetch available school year databases for the train model modal
    try:
        root_conn_sy = mysql.connector.connect(host="localhost", user="root", password="root")
        cursor_sy    = root_conn_sy.cursor()
        cursor_sy.execute("SHOW DATABASES LIKE '%\\_sy%'")
        sy_dbs = [r[0] for r in cursor_sy.fetchall()]
        cursor_sy.execute("SHOW DATABASES LIKE 'enrollmentsystem'")
        sy_dbs += [r[0] for r in cursor_sy.fetchall()]
        cursor_sy.close()
        root_conn_sy.close()
    except Exception:
        sy_dbs = []
    sy_options = "".join(f'<option value="{db}">{db}</option>' for db in sy_dbs)

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
            border-collapse: separate;
            border-spacing: 0;
        }
        th, td, .header {
            border: 2px solid white;
            padding: 5px;
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
        #logoutbtn {
            background-color: white;
            color: red;
        }
        .nav-bar {
            margin-left: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .nav-bar form {
            margin: 0;
        }
        .nav-bar-right {
            margin-left: auto;
            margin-right: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        th {
            position: sticky;
            top: 0;
            background-color: #1f1f1f;
            border-bottom: 2px solid white;
        }
        .modal {
            display: none;
            position: fixed;
            z-index: 9999;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.75);
        }
        .modal-content {
            background-color: #1f1f1f;
            padding: 20px;
            border: 2px solid white;
            border-radius: 10px;
            width: 300px;
            text-align: center;
            position: fixed;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
        }
        </style>

        <script>
        const enrolledsubjects = """ + str(enrolled_subj_ids) + """;
        const conflictMessage  = """ + f'"{conflict_msg_js}"' + """;

        function showConflictMessage(msg) {
            const span = document.getElementById("conflictmsg");
            span.textContent = msg;
            span.style.display = (msg && msg !== "No conflict") ? "inline" : "none";
        }

        function fillFormStudents(studid) {
            const params = new URLSearchParams(window.location.search);
            const subjid = params.get("subjid");
            const newUrl = subjid
                ? `students.py?studid=${studid}&subjid=${subjid}`
                : `students.py?studid=${studid}`;
            window.location.href = newUrl;
        }

        function enrollStudent() {
            const params = new URLSearchParams(window.location.search);
            document.getElementById('subjid').value = params.get('subjid');
            document.getElementById('action').value = 'enrollstudent';
            document.getElementById("studentForm").submit();
        }

        function dropStudent() {
            document.getElementById('action').value = 'dropstudent';
            document.getElementById("studentForm").submit();
        }

        function selectSubjectToDrop(enrolledsubjid) {
            const params    = new URLSearchParams(window.location.search);
            const studid    = params.get('studid');
            const enrollbtn = document.getElementById("enrollbtn");
            const dropbtn   = document.getElementById("dropbtn");

            if (studid && enrolledsubjid) {
                enrollbtn.style.display = "none";
                dropbtn.style.display   = "inline-block";
                dropbtn.value = `Drop Student ID: ${studid} from Subject ID: ${enrolledsubjid}`;
                document.getElementById('subjid').value = enrolledsubjid;
            }
        }

        function openTrainingModal() {
            document.getElementById("trainModal").style.display = "flex";
        }

        function trainModel() {
            // validates that a database was selected, then disables the button and relabels it
            const db = document.getElementById("traindbselect").value;
            if (!db) { alert("Please select a school year database."); return; }

            const trainBtn    = document.querySelector("#trainModal input[value='Train']");
            trainBtn.disabled = true;
            trainBtn.value    = "Training...";

            // on success it shows the accuracy in an alert and closes the modal. on failure, it shows the error.
            // the .finally() block always re-enables the button regardless of success or failure, so the user can retry.
            fetch(`students.py?action=trainmodel&traindb=${encodeURIComponent(db)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        alert("Training failed: " + data.error);
                    } else {
                        alert(`Model trained successfully on: ${data.trained_on}\\nValidation Accuracy: ${data.accuracy}%`);
                        document.getElementById("trainModal").style.display = "none";
                    }
                })
                .catch(err => alert("Training request failed: " + err))
                .finally(() => {
                    trainBtn.disabled = false;
                    trainBtn.value    = "Train";
                });
        }

        function aiEnrollStudent() {
            // validates that a student was selected, then disables the button and relabels it
            const params = new URLSearchParams(window.location.search);
            const studid = params.get("studid");
            if (!studid) { alert("Please select a student first."); return; }

            const btn    = document.getElementById("aienrollbtn");
            btn.disabled = true;
            btn.value    = "AI Enrolling...";

            fetch(`students.py?action=aienroll&studid=${encodeURIComponent(studid)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        alert("AI Enroll failed: " + data.error);
                    } else {
                        // build a message to show the user what happend during the ai enroll then reload the page
                        let msg = "";
                        if (data.enrolled && data.enrolled.length > 0)
                            msg += `Enrolled into: ${data.enrolled.join(", ")}\\n`;
                        if (data.skipped_enrolled && data.skipped_enrolled.length > 0)
                            msg += `Already enrolled (skipped): ${data.skipped_enrolled.join(", ")}\\n`;
                        if (data.skipped_conflict && data.skipped_conflict.length > 0)
                            msg += `Schedule conflict (skipped): ${data.skipped_conflict.join(", ")}\\n`;
                        if (!msg) msg = "No subjects to enroll (all already enrolled or conflicting).";
                        alert(msg);
                        window.location.href = `students.py?studid=${studid}`;
                    }
                })
                .catch(err => alert("AI Enroll request failed: " + err))
                .finally(() => {
                    btn.disabled = false;
                    btn.value    = `AI Enroll Student ${studid}`;
                });
        }

        window.addEventListener("load", () => {
            const params      = new URLSearchParams(window.location.search);
            const subjid      = params.get("subjid");
            const studid      = params.get("studid");
            const enrollbtn   = document.getElementById("enrollbtn");
            const aienrollbtn = document.getElementById("aienrollbtn");
            document.getElementById("dropbtn").style.display = "none";

            // ai enroll button - only need to select student
            if (studid) {
                aienrollbtn.style.display = "inline-block";
                aienrollbtn.value = `AI Enroll Student ${studid}`;
            } else {
                aienrollbtn.style.display = "none";
            }

            // regular enroll button - needs both student and subject
            if (subjid && studid) {
                if (enrolledsubjects.includes(subjid)) {
                    enrollbtn.style.display = "none";
                } else if (conflictMessage && conflictMessage !== "No conflict") {
                    enrollbtn.style.display = "none";
                    showConflictMessage(conflictMessage);
                } else {
                    enrollbtn.style.display = "inline-block";
                    enrollbtn.value = `Enroll Student ID: ${studid} to Subject ID: ${subjid}`;
                }
            } else {
                enrollbtn.style.display = "none";
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
                    <span>Students</span>
                    <a href="subjects.py">Subjects</a>
                    <a href="teachers.py">Teachers</a>

                    <form action="students.py" method="post" id="createDbForm">
                        <select name="createdbcombo" id="createdbcombo" onchange="this.form.submit()">
                            <option value="">Create DB</option>
                            <option value="1stsem">1st Sem</option>
                            <option value="2ndsem">2nd Sem</option>
                            <option value="summer">Summer</option>
                        </select><br>
                        <input type="hidden" name="action" value="createdb">
                    </form>

                    <button onclick="openTrainingModal()">Train Model</button>

                    <div class="nav-bar-right">
                        <span id="currentuser">CURRENT USER: """+dbuser+"""</span>
                        <a href="index.py?action=logout" id="logoutbtn"
                            onclick="return confirm('Are you sure you want to logout?');">Logout</a>
                    </div>
                </div>
            </td>
        </tr>
        <tr>
            <td width="30%" valign="top">
                <h3>Student Form</h3>
                <form action="students.py" method="post" id="studentForm">
                    Student ID:<br>
                    <input type="text" name="studid" id="studid" readonly value="""+studid_val+"""><br>
                    Student Name:<br>
                    <input type="text" name="studname" id="studname" value=\""""+studname_val+"""\"><br>
                    Student Address:<br>
                    <input type="text" name="studaddress" id="studaddress" value=\""""+studaddress_val+"""\"><br>
                    Student Course:<br>
                    <input type="text" name="studcourse" id="studcourse" value="""+studcourse_val+"""><br><br>
                    Student Gender:<br>
                    <input type="text" name="studgender" id="studgender" value="""+studgender_val+"""><br><br>
                    Year Level:<br>
                    <input type="number" name="yearlevel" id="yearlevel" value="""+yearlevel_val+"""><br><br>

                    <input type="submit" value="Insert" onclick="document.getElementById('action').value='insert'">
                    <input type="submit" value="Update" onclick="document.getElementById('action').value='update'">
                    <input type="submit" value="Delete" onclick="document.getElementById('action').value='delete'">
                    <br><br>
                    <input type="button" id="aienrollbtn" value="AI Enroll Student"
                           style="display:none; background-color:#1a3a7a; border:2px solid #4488ff; border-radius:4px; cursor:pointer; padding:5px 10px;"
                           onclick="aiEnrollStudent()"><br><br>
                    <input type="button" id="enrollbtn" value="" style="display:none;" onclick="enrollStudent()">
                    <input type="button" id="dropbtn"   value="" style="display:none;" onclick="dropStudent()"><br><br>
                    <span id="conflictmsg" style="color:red;"></span>

                    <input type="hidden" name="action" id="action" value="">
                    <input type="hidden" name="subjid" id="subjid">
                </form>
            </td>

            <td width="70%" valign="top">
                <h3>Students Table for: """+conn.database+"""</h3>
                <div style="max-height: 375px; overflow-y: auto; display: block;">
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

    # get the value that was pressed in the combo box then make the database
    if action == "createdb" and createdbcombo != "":
        dbname = f"{createdbcombo}_sy{current_year}_{next_year}"

        try:
            conn_createdb   = mysql.connector.connect(host="localhost", user="root", password="root")
            cursor_createdb = conn_createdb.cursor()

            cursor_createdb.execute("SHOW DATABASES LIKE %s", (dbname,))
            if cursor_createdb.fetchone():
                print(f'<script>alert("{dbname} already exists.");</script>')
            else:
                cursor_createdb.execute(f"CREATE DATABASE `{dbname}`")
                conn_createdb.commit()

                cursor_createdb.execute("""
                    SELECT table_name FROM information_schema.tables WHERE table_schema = %s
                """, (selected_db_from_index,))
                tables_to_clone = cursor_createdb.fetchall()

                for (table_name,) in tables_to_clone:
                    cursor_createdb.execute(
                        f"CREATE TABLE `{dbname}`.`{table_name}` LIKE `{selected_db_from_index}`.`{table_name}`"
                    )
                    if table_name == "subjects":
                        cursor_createdb.execute(
                            f"INSERT INTO `{dbname}`.`subjects` SELECT * FROM `{selected_db_from_index}`.`subjects`"
                        )

                cursor_createdb.execute(
                    "SHOW CREATE PROCEDURE `{}`.`checkconflict`".format(selected_db_from_index)
                )
                proc_definition = cursor_createdb.fetchone()[2]
                proc_definition = proc_definition.replace("`enrollmentsystem`", f"`{dbname}`")
                cursor_createdb.execute(f"USE `{dbname}`")
                cursor_createdb.execute(proc_definition)

                print(f'<script>alert("Database {dbname} created successfully.");</script>')

        except Exception as e:
            print(f"<pre>{e}</pre>")

        finally:
            if 'conn_createdb' in locals():
                conn_createdb.close()

    # clicking a row fills the form fields
    for i in range(len(rows)):
        studid_val      = str(rows[i][0])
        studname_val    = str(rows[i][1])
        studaddress_val = html.escape(str(rows[i][2]))
        studcourse_val  = html.escape(str(rows[i][3]))
        studgender_val  = html.escape(str(rows[i][4]))
        yearlevel_val   = str(rows[i][5])
        totalunits_val  = studentunits.get(studid_val, 0)

        print(f"<tr onclick=\"fillFormStudents('{studid_val}')\" style=\"cursor:pointer;\">")
        print("<td>" + studid_val      + "</td>")
        print("<td>" + studname_val    + "</td>")
        print("<td>" + studaddress_val + "</td>")
        print("<td>" + studcourse_val  + "</td>")
        print("<td>" + studgender_val  + "</td>")
        print("<td>" + yearlevel_val   + "</td>")
        print("<td>" + str(totalunits_val) + "</td>")
        print("</tr>")

    print("""
                    </table>
                </div>
            </td>
        </tr>

        <tr>
            <td width="30%"></td>
            <td width="70%" valign="top">
                <h3>Enrolled Subjects</h3>
                <div style="max-height: 375px; overflow-y: auto; display: block;">
                    <table border="1" cellpadding="5" cellspacing="0" width="100%">
                        <tr>
                            <th>Subject ID</th>
                            <th>Code</th>
                            <th>Description</th>
                            <th>Units</th>
                            <th>Schedule</th>
                        </tr>
    """)

    for subject in enrolledsubjects:
        subjid_val    = str(subject[0])
        subjcode_val  = html.escape(str(subject[1]))
        subjdesc_val  = html.escape(str(subject[2]))
        subjunits_val = str(subject[3])
        subjsched_val = html.escape(str(subject[4]))
        print(f"<tr onclick=\"selectSubjectToDrop('{subjid_val}')\" style=\"cursor:pointer;\">")
        print("<td>" + subjid_val    + "</td>")
        print("<td>" + subjcode_val  + "</td>")
        print("<td>" + subjdesc_val  + "</td>")
        print("<td>" + subjunits_val + "</td>")
        print("<td>" + subjsched_val + "</td>")
        print("</tr>")

    print("""
                    </table>
                </div>
            </td>
        </tr>

    </table>

    <div id="trainModal" class="modal">
        <div class="modal-content">
            <h2>Select School Year as Training Data</h2>
            <select id="traindbselect" style="width:100%; margin-bottom:12px;">
                <option value="">-- Select a database --</option>
                """ + sy_options + """
            </select><br>
            <input type="button" value="Train"
                   style="border-color:#1a7a1a; color:#aaffaa; cursor:pointer; padding:6px 16px;"
                   onclick="trainModel()">
            <input type="button" value="Cancel"
                   style="margin-left:8px; cursor:pointer; padding:6px 16px;"
                   onclick="document.getElementById('trainModal').style.display='none'">
        </div>
    </div>

    </body>
    </html>
    """)

except Exception:
    tb = traceback.format_exc()
    print("<h2>Error</h2>")
    print(f"<pre>{tb}</pre>")

finally:
    if 'conn' in locals():
        conn.close()
