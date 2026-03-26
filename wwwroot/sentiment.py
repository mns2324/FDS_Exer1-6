#!/usr/bin/env python3

import json
import os
import sys
import warnings

os.environ["HF_HOME"] = "D:\\ModelCache"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TQDM_DISABLE"] = "1"

# create the eval_cache folder
CACHE_DIR = "eval_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# these funcs should make subsequent loads slightly faster
def get_cache_path(subjid):
    # e.g. eval_cache/2000.json
    return os.path.join(CACHE_DIR, f"{subjid}.json")

def load_cache(subjid):
    path = get_cache_path(subjid)
    # check if the path exists, then return the analyzed rows
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def save_cache(subjid, data):
    path = get_cache_path(subjid)
    # writes the analyzed rows list to that json
    with open(path, "w") as f:
        json.dump(data, f)

# silence noise before http headers (prevent 502.2)
class _NullWriter:
    def write(self, *_args, **_kwargs): pass
    def flush(self): pass

_ORIG_STDOUT = sys.stdout
_ORIG_STDERR = sys.stderr
sys.stdout = _NullWriter()
sys.stderr = _NullWriter()

warnings.filterwarnings("ignore")

import cgi
import html
import traceback
import http.cookies
import mysql.connector
import re
from transformers import pipeline

# used to return positive or negative with a confidence score
sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    device_map="cpu"
)

# zero-shot-classification; used to assign topic categories to each clause
# pass the list of labels below and the model scores each one against the clause text
zero_shot_pipeline = pipeline(
    "zero-shot-classification",
    model="cross-encoder/nli-deberta-v3-small"
)

candidate_labels = [
    "Laboratory", "Facility", "Instruction",
    "Curriculum", "Assessment", "Management"
]

# increase for stricter requirement
category_score_threshold = 0.35

sys.stdout = _ORIG_STDOUT
sys.stderr = _ORIG_STDERR

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
    
print("Content-Type: text/html; charset=utf-8")
    
form = cgi.FieldStorage()
subjid = form.getvalue("subjid", "")
# "All" as default as the teacher can either see all or only select certain sentiments/categories
filter_sentiment = form.getvalue("sentiment", "All")
filter_category = form.getvalue("category", "All")

subject_evals = []
analyzed_rows = []
filtered_rows = []
sorted_categories = []
prev_studid = None

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    cursor = conn.cursor()
    
    # fetch all student evaluations (non-null and non-only whitespace) from the selected subject
    if subjid:
        cursor.execute("""
            SELECT e.studid, e.subjid, e.evaluation FROM ENROLL e
            WHERE e.subjid = %s AND e.evaluation IS NOT NULL AND TRIM(e.evaluation) != ''
            ORDER BY e.studid        
            """, (subjid,)
        )
        subject_evals = cursor.fetchall()
        
    cached_rows = load_cache(subjid)
    
    # get the set of evaluations currently in the DB
    db_evals = {str(sid): etxt for (sid, sjid, etxt) in subject_evals}
    # get the set of evaluations that were cached
    cached_evals = {str(row["studid"]): row["full_eval"] for row in cached_rows} if cached_rows else {}
    
    # if there's no cache yet / a new evaluation was sent, run the models
    if cached_rows is None or db_evals != cached_evals:
        for (studid_val, subjid_val, eval_text) in subject_evals:
            
            # split the full evaluation text into smaller pieces (regex used here)
            # splits on semicolons, commas before conjunctions, conjunctions themselves and commas after conjunction-led sentences
            # clauses under 15 characters are dropped as they are too small for any meaningful analysis   
            split_pattern = (
                r'\s*;\s*'
                r'|\s*,\s*(?=(?:but|however|although|yet|while|though|whereas)\b)'
                r'|\s+(?=(?:but|however|although|yet|while|though|whereas)\b)'
                r'|(?<=\w),\s+(?!(?:but|however|although|yet|while|though|whereas)\b)' 
            )
            raw_parts = re.split(split_pattern, eval_text, flags=re.IGNORECASE) # make a list of these clauses
            clauses = []
            for part in raw_parts:
                cleaned = part.strip()
                if len(cleaned) >= 15:
                    clauses.append(cleaned)
            
            # run the sentiment model on each clause, will return positive or negative depending on the text content
            for clause in clauses:
                sentiment_results = sentiment_pipeline(clause, truncation=True, max_length=512)
                sentiment = sentiment_results[0]["label"].upper()
                # if sentiment not in ("POSITIVE", "NEGATIVE"):
                #     sentiment = "POSITIVE"
                
                # run zs on the candidate labels, only labels above the threshold are kept, multi-label=True allows 2 or more labels for one clause
                zs_result = zero_shot_pipeline(clause, candidate_labels=candidate_labels, multi_label=True)
                
                categories = []
                # zip combines the labels and scores into one so both can be looped over at the same time (parallel iteration)
                for label, score in zip(zs_result["labels"], zs_result["scores"]): 
                    if score >= category_score_threshold:
                        categories.append(label)
                if not categories:
                    categories = ["General"]

                analyzed_rows.append({
                    "studid"    : studid_val,
                    "subjid"    : subjid_val,
                    "clause"    : clause,
                    "sentiment" : sentiment,
                    "categories": categories,
                    "full_eval" : eval_text,
                })
            
        save_cache(subjid, analyzed_rows)       
    else:
        analyzed_rows = cached_rows

    for row in analyzed_rows:
        # skip the row if the row's sentiment doesnt match the filter that was picked
        if filter_sentiment != "All" and row["sentiment"] != filter_sentiment.upper():
            continue
        # skip the row if none of the row's categories match the filter that was picked
        if filter_category != "All":
            if filter_category.lower() not in [c.lower() for c in row["categories"]]: # convert filter and category list to lowercase first
                continue
        filtered_rows.append(row)
        
    # build the category dropdown for the filter only from categories that actually appear
    all_categories = set()
    for row in analyzed_rows:
        for category in row["categories"]:
            all_categories.add(category)
    sorted_categories = sorted(all_categories)

    print("""
    <html>
        <head>
            <meta charset="utf-8">
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
            .positive{
                background-color: #1a7a1a; 
                color: #aaffaa; 
                font-weight: bold; 
                padding: 3px 8px; 
                border-radius: 4px; 
                display: inline-block; 
            }
            .negative{
                background-color: #8b0000; 
                color: #aaffaa; 
                font-weight: bold; 
                padding: 3px 8px; 
                border-radius: 4px; 
                display: inline-block; 
            }
            .category-tag {
                background-color: #0a68f5;
                color: white;
                font-size: 12px;
                padding: 2px 7px;
                border-radius: 10px;
                display: inline-block;
                margin: 2px;
            }
            </style>
            <script>
                function confirmLogout() {
                    if (confirm("Are you sure you want to logout?")) {
                        window.location.href = "index.py?action=logout";
                    }
                    return false;
                }
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
                    <h2>Student Evaluation</h2>
                    <form action="sentiment.py" method="get">
                        <input type="hidden" name="subjid" value=\""""+html.escape(subjid)+"""\">
                        <div class="filter-bar">
                            <label>
                                Filter by Sentiment:
                                <select name="sentiment">
                                    <option value="All">All</option> 
                                    <option value="POSITIVE" """ + ('selected' if filter_sentiment == 'POSITIVE' else '') + """>Positive</option> 
                                    <option value="NEGATIVE" """ + ('selected' if filter_sentiment == 'NEGATIVE' else '') + """>Negative</option> 
                                </select>
                            </label>
                            <label>
                                Filter by Category:
                                <select name="category">
                                    <option value="All">All</option>
    """)

    for category in sorted_categories:
        selected = 'selected' if category == filter_category else ''
        print(f'<option value="{html.escape(category)}" {selected}>{html.escape(category)}</option>') 

    print("""
                                </select>
                            </label>
                            <input type="submit" value="Apply">
                        </div>
                    </form>
                    <div class='subject-filter'>Subject filter: <strong>"""+html.escape(subjid)+"""</strong></div>
                    
                    <table width="100%" cellpadding="5" cellspacing="0">
                    <tr>
                        <th>StudID</th>
                        <th>SubjID</th>
                        <th>Clause</th>
                        <th>Sentiment</th>
                        <th>Category</th>
                        <th>Full Evaluation</th>
                    </tr>
    """)

    if not filtered_rows:
        print('<tr><td colspan="6" style="text-align:center; color:#aaa;">No results found.</td></tr>')
        
    for row in filtered_rows:      
        sentiment_html = (
            '<span class="positive">POSITIVE</span>'
            if row["sentiment"] == "POSITIVE" else
            '<span class="negative">NEGATIVE</span>'
        )
        
        category_tags_html = ""
        for category in row["categories"]:
            category_tags_html += f'<span class="category-tag">{html.escape(category)}</span>'
            
        if row["studid"] != prev_studid:
            full_eval_html = html.escape(row["full_eval"])
            prev_studid = row["studid"]
        else:
            full_eval_html = "(Same as above.)"
        
        print("<tr>")
        print(f"<td>{html.escape(str(row['studid']))}</td>")
        print(f"<td>{html.escape(str(row['subjid']))}</td>")
        print(f"<td>{html.escape(row['clause'])}</td>")
        print(f"<td>{sentiment_html}</td>")
        print(f"<td>{category_tags_html}</td>")
        print(f"<td>{full_eval_html}</td>")
        print("</tr>")
        
    print("""
    </table>
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
    sys.stdout.flush()