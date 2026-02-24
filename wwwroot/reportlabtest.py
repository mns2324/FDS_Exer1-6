#!/usr/bin/env python3

import sys
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table

try:
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)

    data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "London"],
        ["Charlie", "35", "Paris"],
    ]

    table = Table(data)
    doc.build([table])

    pdf = buffer.getvalue()
    buffer.close()

    # ---- HEADERS (CRITICAL ORDER) ----
    sys.stdout.write("Content-Type: application/pdf\r\n")
    sys.stdout.write("Content-Disposition: inline; filename=table_example.pdf\r\n")
    sys.stdout.write("Content-Length: {}\r\n".format(len(pdf)))
    sys.stdout.write("\r\n")  # required blank line
    sys.stdout.flush()

    # ---- BINARY OUTPUT ----
    sys.stdout.buffer.write(pdf)
    sys.stdout.buffer.flush()

except Exception as e:
    # If error happens, IIS needs valid headers
    sys.stdout.write("Content-Type: text/plain\r\n\r\n")
    sys.stdout.write(str(e))