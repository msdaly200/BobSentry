# Report UI Layer - Quick Reference

## Overview

Bob-Sentry reports use a **two-layer architecture**:

1. **Data Layer** (`.bob/reports/<attack-class>/<issue>/`) - Raw markdown reports and Python scripts (source of truth)
2. **UI Layer** (`.bob/reports/ui/`) - HTML templates, CSS, and generated HTML (presentation only)

## Why This Separation?

✅ **Change UI without touching data** - Switch from HTML to PDF, dashboards, or any format  
✅ **Version control friendly** - Only commit templates and raw reports, not generated HTML  
✅ **Multiple UIs simultaneously** - Generate HTML, PDF, and web dashboard from same data  
✅ **Automation ready** - Regenerate UI on-demand or in CI/CD pipelines

## Quick Start

### Generate HTML Reports

```bash
# Generate HTML for all reports
cd .bob/reports/ui
python3 generate_html_reports.py --all

# Generate HTML for a specific issue
python3 generate_html_reports.py --issue 50445

# Generate HTML for the most recent report
python3 generate_html_reports.py
```

### View Reports

```bash
# Open the index page
xdg-open .bob/reports/ui/generated/index.html

# Or serve with Python
cd .bob/reports/ui/generated
python3 -m http.server 8000
# Visit http://localhost:8000
```

## Directory Structure

```
.bob/reports/
│
├── ui/                              # 🎨 UI LAYER (presentation)
│   ├── templates/                   # HTML templates (Jinja2)
│   ├── assets/                      # CSS, JS, images
│   ├── generated/                   # Generated HTML (gitignored)
│   ├── generate_html_reports.py     # Generator script
│   └── README.md                    # Full documentation
│
├── SSRF-backchannel/                # 📊 DATA LAYER (source of truth)
│   └── 49915/
│       ├── triage-49915-*.md        # Markdown report
│       ├── setup_realm.py           # Setup script
│       └── exploit_test.py          # Exploit script
│
├── TOCTOU-role-rename/
│   └── 50445/
│       └── ...
│
└── novel-pattern/
    └── 49570/
        └── ...
```

## What Gets Committed?

| Path | Committed? | Why |
|------|-----------|-----|
| `.bob/reports/<attack-class>/<issue>/*.md` | ✅ Yes | Source of truth |
| `.bob/reports/<attack-class>/<issue>/*.py` | ✅ Yes | Reproduction scripts |
| `.bob/reports/ui/templates/` | ✅ Yes | UI templates |
| `.bob/reports/ui/assets/` | ✅ Yes | CSS, JS |
| `.bob/reports/ui/generate_html_reports.py` | ✅ Yes | Generator script |
| `.bob/reports/ui/generated/` | ❌ No | Ephemeral (regenerate from markdown) |

## Customizing the UI

### Change Colors/Styling

Edit `.bob/reports/ui/assets/report-styles.css`:

```css
:root {
    --color-primary: #2563eb;    /* Change to your brand color */
    --color-success: #16a34a;
    --color-danger: #dc2626;
}
```

### Modify HTML Structure

Edit `.bob/reports/ui/templates/report-template.html`

### Add a New UI Format

Create a new generator script (e.g., `generate_pdf_reports.py`) that reads the same markdown files.

## Integration with Triage Workflow

### During Triage (Automated)

Agent mode writes **only** to the data layer:
- Creates `.md` report
- Copies `.py` scripts

UI layer is **not touched**.

### After Triage (Manual/CI)

Generate HTML on-demand:
```bash
python3 .bob/reports/ui/generate_html_reports.py --all
```

## Dependencies

```bash
pip3 install markdown jinja2
```

## Testing

The system has been tested with all existing reports:

```bash
$ cd .bob/reports/ui
$ python3 generate_html_reports.py --all
Generating HTML for 4 report(s)...
✓ Generated: .../SSRF-backchannel/49915/triage-49915-2026-06-28.html
✓ Generated: .../SSRF-backchannel/49915/triage-49915-2026-07-04.html
✓ Generated: .../TOCTOU-role-rename/50445/triage-50445-2026-07-09.html
✓ Generated: .../novel-pattern/49570/triage-49570-2026-07-04.html
✓ Generated index: .../generated/index.html
Done!
```

## Full Documentation

See `.bob/reports/ui/README.md` for complete details.

---

**Remember:** Raw markdown reports are the source of truth. HTML is just one way to view them.