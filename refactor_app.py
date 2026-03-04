import re

with open("frontend/app.py", "r") as f:
    lines = f.readlines()

out = []
in_page = False
current_page_func = ""

for line in lines:
    if line.startswith('if page_name == "Query Console":'):
        out.append('def page_query_console():\n')
        out.append('    render_header("Query Console", "Ask any business question in plain English")\n')
        in_page = True
        continue
    elif line.startswith('elif page_name == "Transparency":'):
        out.append('\ndef page_transparency():\n')
        out.append('    render_header("Transparency", "Inspect LLM reasoning, schema selection, and correction steps")\n')
        in_page = True
        continue
    elif line.startswith('elif page_name == "Analytics":'):
        out.append('\ndef page_analytics():\n')
        out.append('    render_header("Analytics", "Real-time performance and accuracy metrics")\n')
        in_page = True
        continue
    elif line.startswith('elif page_name == "History":'):
        out.append('\ndef page_history():\n')
        out.append('    render_header("History", "Audit log of all past queries")\n')
        in_page = True
        continue
    elif line.startswith('elif page_name == "Data Upload":'):
        out.append('\ndef page_data_upload():\n')
        out.append('    render_header("Data Upload", "Upload CSV / Parquet files and query them instantly with AI")\n')
        in_page = True
        continue

    if in_page:
        if line.strip() == "" or line.startswith("    ") or line.startswith("import time"):
            # It's already indented or a blank line, maybe keep it? Wait, the original code inside the `if` was indented by 4 spaces.
            # If we change `if` to `def`, the indentation shouldn't change!
            # BUT `elif page_name` was NOT indented. So the content INSIDE `elif` was indented by 4 spaces. 
            # When we make it `def`, the content inside `def` also needs 4 spaces. So we don't need to change the indentation of the content!
             out.append(line)
        else:
            # wait, if it's not indented, and not a blank line, what is it?
            if line.startswith("# ════"):
                out.append(line)
            else:
                out.append(line)
    else:
        out.append(line)

# Add the navigation router at the very bottom
out.append('''

# ══════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════
pg = st.navigation([
    st.Page(page_query_console, title="Query Console", icon="⚡"),
    st.Page(page_transparency, title="Transparency", icon="🔬"),
    st.Page(page_analytics, title="Analytics", icon="📊"),
    st.Page(page_history, title="History", icon="📜"),
    st.Page(page_data_upload, title="Data Upload", icon="📂"),
])
pg.run()
''')

with open("frontend/app.py", "w") as f:
    f.writelines(out)
