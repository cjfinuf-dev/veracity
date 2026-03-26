# Veracity Business Suite

**AI-Powered Accounting Intelligence Platform**

A comprehensive web application providing GAAP accounting research, reference materials, and business tools for accounting professionals.

---

## Overview

Veracity Business Suite is a static website application designed to help accounting professionals access:
- GAAP/FASB research and guidance
- Accounting Standards Updates (ASU) library
- Chart of Accounts templates
- Financial statement frameworks
- Best practice documentation

---

## Tech Stack

- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **Deployment:** Cloudflare Pages
- **Assets:** SVG logos, PNG shields, branding materials
- **Data:** JSON knowledge base + PDF reference library

---

## Project Structure

```
veracitybusinesssuite/
├── index.html              # Main application entry point
├── assets/                 # Logos, shields, branding images
├── data/                   # JSON knowledge base + ASU PDFs
├── scripts/                # JavaScript modules
├── PRD.md                  # Product requirements document
├── generate_branding_guide.py  # Branding PDF generator
└── Veracity_Branding_Guide.pdf # Brand guidelines
```

---

## Features

- **GAAP Research** - Search and reference accounting standards
- **ASU Library** - Browse Accounting Standards Updates
- **Interactive Tools** - Chart of Accounts builder, calculators
- **Knowledge Base** - Curated accounting best practices
- **Responsive Design** - Works on desktop, tablet, mobile

---

## Development

### Prerequisites
- Modern web browser
- Python 3.x (for branding guide generation)

### Local Development
```bash
# Clone the repo
git clone https://github.com/cjfinuf/veracity-business-suite.git

# Open in browser
open index.html
```

Or use a local server:
```bash
# Python
python -m http.server 8000

# Node
npx http-server
```

Then visit: http://localhost:8000

---

## Deployment

Deployed via **Cloudflare Pages**:
- Automatic deploys on push to `main`
- Global CDN distribution
- Free SSL/TLS
- Custom domain support

---

## Branding

Brand colors, logos, and guidelines are documented in `Veracity_Branding_Guide.pdf`.

To regenerate the branding guide:
```bash
python generate_branding_guide.py
```

---

## License

Proprietary - All Rights Reserved

---

## Contact

**Veracity Business Suite**
Developed by Connor Finuf
[GitHub](https://github.com/cjfinuf)

---

**Last Updated:** 2026-03-26
