#!/usr/bin/env python3

import sys
from io import BytesIO
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
from reportlab.lib.units import inch

try:
    # create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    
    # paragraph styles
    center_bold = ParagraphStyle(
        name='CenterBold',          # internal style name
        alignment=TA_CENTER,        # text alignment
        textColor=colors.black,     # text color
        fontName='Helvetica-Bold',  # bold font 
        fontSize=14,                # font size
    )
    left_align = ParagraphStyle(
        name='LeftAlign',
        textColor=colors.black,
        alignment=TA_LEFT
    )
    right_align = ParagraphStyle(
        name='RightAlign',
        textColor=colors.black,
        alignment=TA_RIGHT
    )
    
    # school logo image + university header text
    logo = Image("catgulp.jpg", width=1*inch, height=1*inch)
    paragraph1 = Paragraph("UNIVERSITY NAME", center_bold)
    paragraph2 = Paragraph("Registrar's Office", center_bold)
    
    # table used to place logo and text side-by-side
    header_table = Table([
        [logo, [paragraph1, paragraph2]]
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
        ["Student ID", "test"],
        ["School Year", "test"],
        ["Student Name", "test"],
        ["Student Course", "test"],
        ["Student Year", "test"]
    ]
 
    title = Paragraph("Student Grade Sheet", center_bold)

    # rows/columns for the subject spreadsheet
    subjectdata = [
        ["Subject ID", "Subject Code", "Prelim", "Midterm", "Prefinal", "FINAL"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "London"],
        ["Charlie", "35", "Paris"],
    ]

    studinfotable = Table(studentinfo)   
    gradetable = Table(subjectdata)  
    studinfotable.setStyle(TableStyle([
        # text alignment = (start_cell, end_cell, alignment_value)
        # font name = (start_cell, end_cell, font_name)
        # padding = (start_cell, end_cell, padding_value)
        
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),              # left-align all text
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),  # first column bold
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),           # add spacing between rows
    ]))
    gradetable.setStyle(TableStyle([
        # grid lines = (grid_start, grid_end, grid_width, grid_color)
        # grid outline = (grid_start, grid_end, box_width, box_color)
        # text alignment = (grid_start, grid_end, alignment_value)
        # font name = (header_start, header_end, header_font)
        
        ('GRID', (0, 0), (-1, -1), 1, colors.black),    # thin grid lines for all cells
        ('BOX', (0, 0), (-1, -1), 2, colors.black),     # thicker outer border
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),            # left-align table content
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold') # bold header text
    ]))
  
    subjectamount = Paragraph("Number of Subjects Listed: ", left_align)
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