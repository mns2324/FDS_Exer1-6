#!/usr/bin/env python3

import sys
import os
import http.cookies
import mysql.connector
from io import BytesIO
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.units import inch

cookies = http.cookies.SimpleCookie(os.environ.get("HTTP_COOKIE", ""))
dbuser = cookies["dbuser"].value if "dbuser" in cookies else ""
dbpass = cookies["dbpass"].value if "dbpass" in cookies else ""
selected_db_from_index = cookies["schoolyearcombo"].value if "schoolyearcombo" in cookies else "enrollmentsystem"

# redirect back to index if not logged in or not student
if not dbuser or not dbpass:
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()
    
if not (dbuser[:4].isdigit() and 999 < int(dbuser[:4]) < 2000):
    print("Status: 302 Found")
    print("Location: index.py")
    print()
    exit()
    
studid = int(dbuser[:4])

try:
    conn = mysql.connector.connect(
        host="localhost",
        user=dbuser,
        password=dbpass,
        database=selected_db_from_index
    )
    cursor = conn.cursor()

    # fetch student info
    cursor.execute(
        "SELECT studid, studname, studcrs, yrlvl FROM students WHERE studid = %s",
        (studid,)
    )
    student = cursor.fetchone()
    
    # if not student:
    #     sys.stdout.write("Content-Type: text/plain\r\n\r\nStudent record not found.")
    #     sys.exit()
        
    # shorthand way of unpacking the student tuple into individual variables
    studid_val, studname_val, studcourse_val, yearlevel_val = student
    
    # show all subjects, even those with missing grades
    cursor.execute(
        """SELECT s.subjid, s.subjcode, g.prelim, g.midterm, g.prefinal, g.final
           FROM enroll e
           JOIN subjects s ON e.subjid = s.subjid
           LEFT JOIN grades g ON g.enroll_eid = e.eid
           WHERE e.studid = %s""",
        (studid,)
    )
    subjects = cursor.fetchall()
    conn.close()

except Exception as e:
    sys.stdout.write("Content-Type: text/plain\r\n\r\n")
    sys.stdout.write(str(e))
    sys.exit()

try:
    # create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    
    # paragraph styles
    center_bold = ParagraphStyle(
        name='CenterBold',          # internal style name
        alignment=TA_CENTER,        # text alignment
        fontName='Helvetica-Bold',  # bold font 
        fontSize=14,                # font size
    )
    left_align = ParagraphStyle(
        name='LeftAlign',
        alignment=TA_LEFT
    )
    right_align = ParagraphStyle(
        name='RightAlign',
        alignment=TA_RIGHT
    )
    
    # school logo image + university header text
    logo = Image("catgulp.jpg", width=1*inch, height=1*inch)
    paragraph1 = Paragraph("UNIVERSITY NAME", center_bold)
    paragraph2 = Paragraph("Registrar's Office", center_bold)
    
    # table used to place logo and text side-by-side
    header_table = Table([
        [
            logo, 
            [paragraph1, paragraph2]
        ]
    ], colWidths=[1.2 * inch, 4 * inch])
    header_table.setStyle(TableStyle([
        # vertical alignment = (start_cell, end_cell, valign)
        # padding adjustments = (start_cell, end_cell, padding_value)
        
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # vertically center content
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),          
    ]))
    
    # rows/columns for the student info
    studentinfo = [
        ["Student ID", str(studid_val)],
        ["School Year", selected_db_from_index],
        ["Student Name", studname_val],
        ["Student Course", studcourse_val],
        ["Student Year", str(yearlevel_val)]
    ]
 
    title = Paragraph("Student Grade Sheet", center_bold)

    # rows/columns for the subject spreadsheet
    subjectdata = [
        ["Subject ID", "Subject Code", "Prelim", "Midterm", "Prefinal", "FINAL"],
    ]
    for row in subjects:
        subjectdata.append([
            str(row[0]),        # subjid
            str(row[1]),        # subjcode
            str(row[2] or ""),  # prelim
            str(row[3] or ""),  # midterm
            str(row[4] or ""),  # prefinal
            str(row[5] or ""),  # final
        ])
        
    studinfotable = Table(studentinfo, hAlign='LEFT')  
    studinfotable.setStyle(TableStyle([
        # text alignment = (start_cell, end_cell, alignment_value)
        # font name = (start_cell, end_cell, font_name)
        # padding = (start_cell, end_cell, padding_value)
        
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),              # left-align all text
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),  # first column bold
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),           # add spacing between rows
    ]))
    
    # no subjects, no grades
    if not subjects:
        gradetable = Paragraph("No records found.", left_align)
        subjectamount = Paragraph("")
    else:
        # apply those column widths to the 6 columns
        gradetable = Table(subjectdata, colWidths=[1*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])  
        gradetable.setStyle(TableStyle([
            # grid lines = (grid_start, grid_end, grid_width, grid_color)
            # grid outline = (grid_start, grid_end, box_width, box_color)
            # text alignment = (grid_start, grid_end, alignment_value)
            # font name = (header_start, header_end, header_font)
            
            ('GRID', (0, 0), (-1, -1), 1, colors.black),        # thin grid lines for all cells
            ('BOX', (0, 0), (-1, -1), 2, colors.black),         # thicker outer border
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),                # left-align table content
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),              # center all letter grades     
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),    # bold header text
            ('FONTNAME', (5, 1), (5, -1), 'Helvetica-Bold')     # bold final grades
        ]))
        
        subjectamount = Paragraph(f"Number of Subjects Listed: {len(subjects)}", left_align)
  
    registrar = Paragraph("Registrar", right_align)
    
    doc.build([
        header_table,
        Spacer(1, 0.2 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.black),
        Spacer(1, 0.3 * inch),

        title,
        Spacer(1, 0.3 * inch),

        studinfotable,
        Spacer(1, 0.5 * inch),

        gradetable,
        Spacer(1, 0.3 * inch),

        subjectamount,
        Spacer(1, 0.7 * inch),

        HRFlowable(width="40%", thickness=1, color=colors.black, hAlign='RIGHT'),
        registrar
    ])
    
    # extract pdf data from memory
    pdf = buffer.getvalue()
    buffer.close()

    # send pdf headers
    sys.stdout.write("Content-Type: application/pdf\r\n")
    sys.stdout.write("Content-Disposition: inline; filename=table_example.pdf\r\n")
    sys.stdout.write("Content-Length: {}\r\n".format(len(pdf)))
    sys.stdout.write("\r\n")  # required blank line
    sys.stdout.flush()

    # send pdf binary data
    sys.stdout.buffer.write(pdf)
    sys.stdout.buffer.flush()

except Exception as e:
    # if error happens, IIS needs valid headers
    sys.stdout.write("Content-Type: text/plain\r\n\r\n")
    sys.stdout.write(str(e))