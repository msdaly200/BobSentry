# Bob-Sentry Report UI System

This directory contains the UI layer for Bob-Sentry triage reports. It is **completely separate** from the raw report data, allowing you to change the presentation layer without affecting the underlying triage artifacts.

## Directory Structure

```
.bob/reports/
├── ui/                          # UI layer (this directory)
│   ├── templates/               # HTML templates
│   │   └── report-template.html # Main report template
│   ├── assets/                  # Static assets (CSS, JS, images)
│   │   └── report-styles.css    # Report stylesheet
│   ├── generated/               # Generated HTML reports (gitignored)
│   │   ├── index.html          # Index of all reports
│   │   └── <attack-class>/     # Mirrors raw report structure
│   │       └── <issue-number>/
│   │           └── triage-*.html
│   ├── generate_html_reports.py # HTML generator script
│   └── README.md               # This file
│
├── <attack-class>/             # Raw report data (source of truth)
│   └── <issue-number>/
│       ├── triage-*.md         # Markdown triage report
│       ├── setup_realm.py      # Realm setup script
│       └── exploit_test.py     # Exploit verification script
│
└── metrics-summary.md          # Aggregate metrics

```

## Design Philosophy

### Separation of Concerns

The report system follows a strict separation between **data** and **presentation**:

| Layer | Location | Purpose | Mutable? |
|-------|----------|---------|----------|
| **Data Layer** | `.bob/reports/<attack-class>/<issue>/` | Source of truth - markdown reports and Python scripts | ✅ Yes - updated by triage sessions |
| **UI Layer** | `.bob/reports/ui/` | Presentation templates and generated HTML | ⚠️ Templates: rarely; Generated: always |

**Why this matters:**

1. **UI Independence**: You can switch from HTML to PDF, web dashboard, Jupyter notebooks, or any other format without touching the raw reports
2. **Version Control**: Raw markdown reports are committed; generated HTML is gitignored (ephemeral)
3. **Automation**: The UI layer can be regenerated at any time from the markdown source
4. **Multiple UIs**: You can have multiple presentation formats simultaneously (HTML + PDF + dashboard)

### Data Flow

```
Triage Session
    ↓
Raw Markdown Report (.md)
    ↓
generate_html_reports.py
    ↓
HTML Report (.html)
    ↓
Browser / Web Server
```

## Usage

### Generate HTML for a Specific Issue

```bash
cd .bob/reports/ui
python generate_html_reports.py --issue 50445
```

This creates:
- `.bob/reports/ui/generated/<attack-class>/<issue>/triage-<issue>-<date>.html`

### Generate HTML for All Reports

```bash
python generate_html_reports.py --all
```

This creates:
- HTML for every markdown report in the reports directory
- An index page at `.bob/reports/ui/generated/index.html`

### Generate HTML for the Most Recent Report

```bash
python generate_html_reports.py
```

(No arguments = most recently modified report)

### View Reports

Open the generated index:

```bash
# Linux/macOS
xdg-open .bob/reports/ui/generated/index.html

# Or use a local web server
python -m http.server 8000 --directory .bob/reports/ui/generated
# Then visit http://localhost:8000
```

## Customizing the UI

### Modify the HTML Template

Edit `.bob/reports/ui/templates/report-template.html`

The template uses Jinja2 syntax with these variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{title}}` | Report title | "Privilege escalation via..." |
| `{{issue_number}}` | GitHub issue number | "50445" |
| `{{cve_id}}` | CVE identifier | "CVE-2026-4629" |
| `{{date}}` | Triage date | "2026-07-09" |
| `{{verdict}}` | Triage verdict | "✅ CONFIRMED" |
| `{{verdict_class}}` | CSS class for verdict | "confirmed" |
| `{{severity}}` | Severity level | "BLOCKER" |
| `{{severity_class}}` | CSS class for severity | "blocker" |
| `{{content}}` | Rendered HTML content | (full report body) |
| `{{raw_report_path}}` | Path to markdown source | "../../TOCTOU-role-rename/50445/..." |

### Modify the Stylesheet

Edit `.bob/reports/ui/assets/report-styles.css`

The stylesheet uses CSS custom properties (variables) for easy theming:

```css
:root {
    --color-primary: #2563eb;      /* Primary brand color */
    --color-success: #16a34a;      /* Success/confirmed */
    --color-warning: #ea580c;      /* Warning/escalate */
    --color-danger: #dc2626;       /* Danger/critical */
    /* ... more variables ... */
}
```

### Add a New UI Format

To add a new presentation format (e.g., PDF):

1. Create a new template in `templates/` (e.g., `report-template-pdf.html`)
2. Add a new generator function in `generate_html_reports.py`
3. Or create a separate script (e.g., `generate_pdf_reports.py`)

The raw markdown reports remain unchanged.

## Dependencies

The HTML generator requires:

```bash
pip install markdown jinja2
```

Optional (for syntax highlighting):

```bash
pip install pygments
```

## Integration with Triage Workflow

### During Triage (Agent Mode)

Agent mode writes **only** to the data layer:

```
.bob/reports/<attack-class>/<issue-number>/
├── triage-<issue>-<date>.md    # Written by Agent mode
├── setup_realm.py              # Copied from /tmp/keycloak-triage/
└── exploit_test.py             # Copied from /tmp/keycloak-triage/
```

The UI layer is **not touched** during triage.

### After Triage (Manual or CI)

Generate HTML reports:

```bash
# In CI or manually
cd .bob/reports/ui
python generate_html_reports.py --all
```

### Viewing Reports

Developers can:
1. Read the raw markdown directly (it's human-readable)
2. Generate HTML on-demand for better formatting
3. Use a CI job to auto-generate HTML on every commit

## Git Configuration

The `.gitignore` should include:

```gitignore
# Generated HTML reports (ephemeral)
.bob/reports/ui/generated/

# Python cache
.bob/reports/ui/__pycache__/
```

The following **are** committed:
- `.bob/reports/ui/templates/` (HTML templates)
- `.bob/reports/ui/assets/` (CSS, JS)
- `.bob/reports/ui/generate_html_reports.py` (generator script)
- `.bob/reports/<attack-class>/<issue>/` (raw reports and scripts)

## Future UI Options

With this architecture, you can easily add:

### Web Dashboard
```python
# dashboard.py
from flask import Flask, render_template
from generate_html_reports import ReportGenerator

app = Flask(__name__)
generator = ReportGenerator()

@app.route('/reports')
def list_reports():
    reports = generator.find_all_reports()
    return render_template('dashboard.html', reports=reports)
```

### PDF Export
```python
# generate_pdf_reports.py
from weasyprint import HTML

def generate_pdf(report_info):
    html_path = generator.generate_html(report_info)
    pdf_path = html_path.replace('.html', '.pdf')
    HTML(html_path).write_pdf(pdf_path)
```

### Jupyter Notebooks
```python
# In a notebook cell
from generate_html_reports import ReportGenerator
from IPython.display import Markdown

generator = ReportGenerator()
reports = generator.find_all_reports()

for report in reports:
    with open(report['path']) as f:
        display(Markdown(f.read()))
```

### Static Site Generator
```bash
# Use Hugo, Jekyll, or MkDocs
mkdocs build --config-file .bob/reports/ui/mkdocs.yml
```

All of these consume the same raw markdown reports - no duplication needed.

## Troubleshooting

### "No reports found"

Check that markdown reports exist:
```bash
find .bob/reports -name "triage-*.md"
```

### "Template not found"

Ensure you're running from the correct directory:
```bash
cd .bob/reports/ui
python generate_html_reports.py
```

Or specify the base directory:
```bash
python generate_html_reports.py --base-dir /path/to/.bob/reports
```

### CSS not loading

The generated HTML uses relative paths. If you move the HTML files, update the CSS link:
```html
<link rel="stylesheet" href="../assets/report-styles.css">
```

## Contributing

When adding new UI features:

1. **Never modify the data layer** (raw reports) for UI purposes
2. **Keep templates generic** - use Jinja2 variables, not hardcoded content
3. **Document new variables** in this README
4. **Test with multiple reports** to ensure consistency
5. **Consider accessibility** - use semantic HTML and ARIA labels

---

**Questions?** See `.bob/skills/cve-analyzer/SKILL.md` for the full triage workflow.