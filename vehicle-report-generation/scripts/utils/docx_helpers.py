"""docx XML manipulation utilities for table/section operations."""

try:
    from docx.oxml import qn
except ImportError:
    from docx.oxml.ns import qn


def remove_table_rows(table, row_indices):
    """Remove rows from a table by index (descending order to avoid index shift).

    Args:
        table: docx Table object.
        row_indices: list of row indices to remove.
    """
    for idx in sorted(set(row_indices), reverse=True):
        if 0 <= idx < len(table.rows):
            row = table.rows[idx]
            row._element.getparent().remove(row._element)


def remove_section_by_heading(doc, heading_text, next_headings=None):
    """Remove all elements from a heading paragraph up to (but not including)
    the next heading paragraph or the document's sectPr.

    Args:
        doc: docx Document object.
        heading_text: text to search for in the starting paragraph.
        next_headings: list of texts that mark the start of the next section.
                       Defaults to ["≥70%", "40%-70%", "≤40%"].

    Returns:
        bool: True if a section was found and removed.
    """
    if next_headings is None:
        next_headings = ["≥70%", "40%-70%", "≤40%"]

    body = doc.element.body
    children = list(body)

    # Find the start index of the heading paragraph
    start_idx = None
    for i, elem in enumerate(children):
        if elem.tag.endswith("}p"):
            texts = elem.findall(f".//{qn('w:t')}")
            para_text = "".join(t.text or "" for t in texts)
            if heading_text in para_text:
                start_idx = i
                break

    if start_idx is None:
        return False

    # Find the end index (next heading or sectPr)
    end_idx = len(children)
    for i in range(start_idx + 1, len(children)):
        child = children[i]
        if child.tag.endswith("}sectPr"):
            end_idx = i
            break
        if child.tag.endswith("}p"):
            texts = child.findall(f".//{qn('w:t')}")
            para_text = "".join(t.text or "" for t in texts)
            if any(h in para_text for h in next_headings):
                end_idx = i
                break

    # Remove elements from end to start to avoid index shift issues
    for i in range(end_idx - 1, start_idx - 1, -1):
        body.remove(children[i])

    return True


def insert_table_at_top(doc, rows, cols):
    """Insert a new table at the top of the document (before the first paragraph).

    Args:
        doc: docx Document object.
        rows: number of rows.
        cols: number of columns.

    Returns:
        Table: the newly created and moved table.
    """
    # Create table at the end first
    new_table = doc.add_table(rows=rows, cols=cols)
    new_tbl_elem = new_table._element

    body = doc.element.body
    # Remove from current position and re-insert at position 0
    body.remove(new_tbl_elem)
    body.insert(0, new_tbl_elem)
    return new_table
