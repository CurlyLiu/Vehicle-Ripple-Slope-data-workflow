from docx import Document
import os

TEMPLATE_DIR = "C:/Users/31915/.claude/skills/vehicle-report-generation/templates"

files = ["ripple_report_template.docx", "slope_report_template.docx"]

for filename in files:
    filepath = os.path.join(TEMPLATE_DIR, filename)
    if not os.path.exists(filepath):
        print(f"\n{'='*60}")
        print(f"FILE NOT FOUND: {filename}")
        print(f"{'='*60}")
        continue

    print(f"\n{'='*60}")
    print(f"DOCUMENT: {filename}")
    print(f"{'='*60}")

    doc = Document(filepath)
    tables = doc.tables
    print(f"Total tables: {len(tables)}")

    for i, table in enumerate(tables):
        rows = len(table.rows)
        cols = len(table.columns)
        print(f"\n--- Table {i+1}: {rows} rows x {cols} columns ---")

        # For the last table, print row contents (up to 30 rows)
        if i == len(tables) - 1:
            print("  [Last table - listing row text content]")
            for r_idx, row in enumerate(table.rows[:30]):
                cells_text = []
                for cell in row.cells:
                    text = cell.text.strip().replace('\n', ' ').replace('\r', '')
                    cells_text.append(text)
                print(f"    Row {r_idx+1}: {cells_text}")
            if rows > 30:
                print(f"    ... ({rows - 30} more rows)")
