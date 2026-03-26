"""
Vera Module Enhancer — Sequential daily module content enrichment

Processes one module per run through the ACCOUNTING_MODULES list.
Matches knowledge from vera-knowledge.json + asu-knowledge.json to each module,
then builds enhanced content with:
  - Plain-language expanded definitions
  - Bulleted detail lists
  - Real-world examples
  - Source citations with links
  - SVG diagram specifications
  - Callout boxes (tips, warnings, common mistakes)
  - Key takeaways

After reaching the last module, loops back to Module 1.

Scheduled: Daily at 9:45 AM (after vera_knowledge_gatherer.py finishes)
"""

import json
import os
import re
import sys
import logging
from datetime import datetime, date
from difflib import SequenceMatcher

# -- Paths --
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
KNOWLEDGE_FILE = os.path.join(DATA_DIR, 'vera-knowledge.json')
ASU_FILE = os.path.join(DATA_DIR, 'asu-knowledge.json')
ENHANCED_FILE = os.path.join(DATA_DIR, 'enhanced-modules.json')
STATE_FILE = os.path.join(DATA_DIR, 'enhancer-state.json')
LOG_DIR = os.path.join(ROOT, 'scripts', 'logs')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f'enhancer_{date.today().isoformat()}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('vera_enhancer')


# ======================================================================
# MODULE DEFINITIONS (mirrors ACCOUNTING_MODULES in index.html)
# ======================================================================

MODULES = [
    {
        "id": "mod01", "title": "The Accounting Equation", "level": "beginner", "ascRefs": [],
        "keywords": ["accounting equation", "assets", "liabilities", "equity", "balance", "net assets", "owner's equity"],
        "concepts": ["Assets", "Liabilities", "Equity", "Why It Always Balances"],
        "diagramType": "equation-balance",
        "relatedModules": ["mod02", "mod06"],
    },
    {
        "id": "mod02", "title": "Double-Entry Bookkeeping", "level": "beginner", "ascRefs": [],
        "keywords": ["double entry", "debits", "credits", "bookkeeping", "t-account", "normal balance", "golden rules"],
        "concepts": ["Debits (Dr)", "Credits (Cr)", "Normal Balances", "T-Accounts", "The Golden Rules"],
        "diagramType": "t-account",
        "relatedModules": ["mod01", "mod04"],
    },
    {
        "id": "mod03", "title": "Chart of Accounts & General Ledger", "level": "beginner", "ascRefs": [],
        "keywords": ["chart of accounts", "general ledger", "account numbers", "sub-ledger", "coa", "gl"],
        "concepts": ["Chart of Accounts (COA)", "Account Numbers", "General Ledger (GL)", "Sub-Ledgers"],
        "diagramType": "account-tree",
        "relatedModules": ["mod02", "mod04"],
    },
    {
        "id": "mod04", "title": "Journal Entries", "level": "beginner", "ascRefs": [],
        "keywords": ["journal entry", "adjusting entry", "compound entry", "reversing entry", "debit credit"],
        "concepts": ["Standard Journal Entry", "Compound Entries", "Adjusting Journal Entries (AJEs)", "Reversing Entries", "Supporting Documentation"],
        "diagramType": "journal-entry",
        "relatedModules": ["mod02", "mod03"],
    },
    {
        "id": "mod05", "title": "Accrual vs. Cash Basis", "level": "beginner", "ascRefs": [],
        "keywords": ["accrual", "cash basis", "matching principle", "revenue recognition", "deferred revenue", "unearned revenue"],
        "concepts": ["Cash Basis", "Accrual Basis", "The Matching Principle", "Accrued Revenue", "Deferred (Unearned) Revenue"],
        "diagramType": "timeline-comparison",
        "relatedModules": ["mod04", "mod06"],
    },
    {
        "id": "mod06", "title": "Financial Statements", "level": "beginner", "ascRefs": ["220", "235"],
        "keywords": ["financial statements", "balance sheet", "income statement", "cash flow", "stockholders equity"],
        "concepts": ["Balance Sheet", "Income Statement", "Statement of Cash Flows", "Statement of Stockholders' Equity", "How They Connect"],
        "diagramType": "statement-flow",
        "relatedModules": ["mod01", "mod05", "mod18"],
    },
    {
        "id": "mod07", "title": "Bank Reconciliations", "level": "beginner", "ascRefs": ["305"],
        "keywords": ["bank reconciliation", "outstanding checks", "deposits in transit", "bank charges", "adjusted balance"],
        "concepts": ["Outstanding Checks", "Deposits in Transit", "Bank Charges & Credits", "Errors", "The Reconciliation Process"],
        "diagramType": "two-column-rec",
        "relatedModules": ["mod04", "mod10"],
    },
    {
        "id": "mod08", "title": "The Accounting Cycle", "level": "beginner", "ascRefs": [],
        "keywords": ["accounting cycle", "trial balance", "closing entries", "post-closing", "journalize", "ledger"],
        "concepts": ["Step 1: Analyze Transactions", "Step 2: Journalize", "Step 3: Post to the Ledger", "Step 4: Prepare Trial Balance", "Step 5: Adjusting Entries & Closing"],
        "diagramType": "circular-steps",
        "relatedModules": ["mod04", "mod06"],
    },
    {
        "id": "mod09", "title": "Depreciation & Amortization", "level": "intermediate", "ascRefs": ["360", "350"],
        "keywords": ["depreciation", "amortization", "straight line", "declining balance", "units of production", "macrs", "impairment"],
        "concepts": ["Straight-Line Method", "Declining Balance (Accelerated)", "Units of Production", "Tax Depreciation (MACRS)", "Impairment"],
        "diagramType": "depreciation-chart",
        "relatedModules": ["mod04", "mod06"],
    },
    {
        "id": "mod10", "title": "Internal Controls", "level": "intermediate", "ascRefs": [],
        "keywords": ["internal controls", "segregation of duties", "coso", "authorization", "reconciliation", "physical controls"],
        "concepts": ["Segregation of Duties", "Authorization & Approval", "Reconciliation & Review", "Physical Controls", "COSO Framework Components"],
        "diagramType": "coso-pyramid",
        "relatedModules": ["mod07", "mod08"],
    },
    {
        "id": "mod11", "title": "Revenue Recognition (ASC 606)", "level": "intermediate", "ascRefs": ["606"],
        "keywords": ["revenue recognition", "asc 606", "performance obligation", "transaction price", "contract"],
        "concepts": ["Step 1: Identify the Contract", "Step 2: Identify Performance Obligations", "Step 3: Determine the Transaction Price", "Step 4: Allocate the Transaction Price", "Step 5: Recognize Revenue"],
        "diagramType": "five-step-flow",
        "relatedModules": ["mod05", "mod23"],
    },
    {
        "id": "mod12", "title": "Inventory Methods & Costing", "level": "intermediate", "ascRefs": ["330"],
        "keywords": ["inventory", "fifo", "lifo", "weighted average", "cost of goods sold", "cogs", "net realizable value"],
        "concepts": ["FIFO (First-In, First-Out)", "LIFO (Last-In, First-Out)", "Weighted Average", "Lower of Cost or Net Realizable Value", "Periodic vs. Perpetual Systems"],
        "diagramType": "inventory-flow",
        "relatedModules": ["mod05", "mod22"],
    },
    {
        "id": "mod13", "title": "Accounts Receivable & Bad Debt", "level": "intermediate", "ascRefs": ["310", "326"],
        "keywords": ["accounts receivable", "bad debt", "allowance", "aging", "write off", "cecl", "doubtful accounts"],
        "concepts": ["Allowance Method", "Percentage of Sales Method", "Aging of Receivables Method", "Write-Offs and Recoveries", "Current Expected Credit Losses (CECL)"],
        "diagramType": "aging-buckets",
        "relatedModules": ["mod04", "mod06"],
    },
    {
        "id": "mod14", "title": "Payroll Accounting", "level": "intermediate", "ascRefs": ["710", "712"],
        "keywords": ["payroll", "wages", "withholding", "employer taxes", "fica", "benefits", "compensation"],
        "concepts": ["Gross Pay to Net Pay", "Employee Withholdings", "Employer Payroll Taxes", "Benefits & Accruals", "Payroll Journal Entries"],
        "diagramType": "payroll-flow",
        "relatedModules": ["mod04", "mod15"],
    },
    {
        "id": "mod15", "title": "Current Liabilities & Contingencies", "level": "intermediate", "ascRefs": ["450", "460"],
        "keywords": ["current liabilities", "contingencies", "accounts payable", "accrued expenses", "warranty", "contingent liability"],
        "concepts": ["Accounts Payable", "Accrued Liabilities", "Unearned Revenue", "Contingent Liabilities", "Warranty Obligations"],
        "diagramType": "liability-categories",
        "relatedModules": ["mod06", "mod16"],
    },
    {
        "id": "mod16", "title": "Long-Term Liabilities & Bonds", "level": "advanced", "ascRefs": ["470", "835"],
        "keywords": ["bonds", "long-term debt", "premium", "discount", "effective interest", "amortization", "covenant"],
        "concepts": ["Bond Basics", "Issuing at Premium vs. Discount", "Effective Interest Method", "Debt Covenants", "Early Retirement of Debt"],
        "diagramType": "bond-timeline",
        "relatedModules": ["mod15", "mod06"],
    },
    {
        "id": "mod17", "title": "Stockholders' Equity", "level": "advanced", "ascRefs": ["505"],
        "keywords": ["stockholders equity", "common stock", "preferred stock", "treasury stock", "dividends", "retained earnings", "stock split"],
        "concepts": ["Common vs. Preferred Stock", "Par Value & Paid-In Capital", "Treasury Stock", "Dividends", "Stock Splits & Reverse Splits"],
        "diagramType": "equity-components",
        "relatedModules": ["mod06", "mod01"],
    },
    {
        "id": "mod18", "title": "Statement of Cash Flows (Indirect Method)", "level": "advanced", "ascRefs": ["230"],
        "keywords": ["cash flow statement", "indirect method", "operating", "investing", "financing", "depreciation add back"],
        "concepts": ["Operating Activities (Indirect)", "Investing Activities", "Financing Activities", "Non-Cash Adjustments", "Free Cash Flow"],
        "diagramType": "cash-flow-waterfall",
        "relatedModules": ["mod06", "mod09"],
    },
    {
        "id": "mod19", "title": "Income Taxes (ASC 740 Basics)", "level": "advanced", "ascRefs": ["740"],
        "keywords": ["income tax", "deferred tax", "asc 740", "temporary difference", "permanent difference", "valuation allowance"],
        "concepts": ["Current vs. Deferred Tax", "Temporary Differences", "Permanent Differences", "Deferred Tax Assets & Liabilities", "Valuation Allowance"],
        "diagramType": "tax-flow",
        "relatedModules": ["mod06", "mod09"],
    },
    {
        "id": "mod20", "title": "Leases (ASC 842 Basics)", "level": "advanced", "ascRefs": ["842"],
        "keywords": ["lease", "asc 842", "operating lease", "finance lease", "right of use", "lease liability"],
        "concepts": ["Operating vs. Finance Leases", "Right-of-Use Asset", "Lease Liability", "Lease Classification Criteria", "Lease Disclosures"],
        "diagramType": "lease-classification",
        "relatedModules": ["mod09", "mod06"],
    },
    {
        "id": "mod21", "title": "Intercompany & Consolidations Intro", "level": "advanced", "ascRefs": ["810"],
        "keywords": ["consolidation", "intercompany", "elimination", "subsidiary", "parent", "noncontrolling interest"],
        "concepts": ["Parent & Subsidiary Relationships", "Consolidation Process", "Intercompany Eliminations", "Noncontrolling Interest", "Variable Interest Entities"],
        "diagramType": "org-structure",
        "relatedModules": ["mod06", "mod24"],
    },
    {
        "id": "mod22", "title": "Cost Accounting Fundamentals", "level": "advanced", "ascRefs": ["330"],
        "keywords": ["cost accounting", "job costing", "process costing", "overhead", "variance analysis", "standard cost"],
        "concepts": ["Job Costing vs. Process Costing", "Overhead Allocation", "Standard Costs & Variances", "Activity-Based Costing", "Cost-Volume-Profit Analysis"],
        "diagramType": "cost-flow",
        "relatedModules": ["mod12", "mod06"],
    },
    {
        "id": "mod23", "title": "Advanced Revenue Recognition", "level": "master", "ascRefs": ["606"],
        "keywords": ["revenue recognition advanced", "variable consideration", "contract modification", "principal agent", "licenses"],
        "concepts": ["Variable Consideration & Constraints", "Contract Modifications", "Principal vs. Agent", "Licenses & Royalties", "Bill-and-Hold Arrangements"],
        "diagramType": "revenue-decision-tree",
        "relatedModules": ["mod11", "mod06"],
    },
    {
        "id": "mod24", "title": "Business Combinations & Goodwill", "level": "master", "ascRefs": ["805", "350"],
        "keywords": ["business combination", "goodwill", "acquisition", "purchase price allocation", "bargain purchase"],
        "concepts": ["Acquisition Method", "Purchase Price Allocation", "Goodwill Calculation", "Goodwill Impairment Testing", "Bargain Purchases"],
        "diagramType": "acquisition-waterfall",
        "relatedModules": ["mod21", "mod09"],
    },
    {
        "id": "mod25", "title": "Foreign Currency Transactions", "level": "master", "ascRefs": ["830"],
        "keywords": ["foreign currency", "translation", "remeasurement", "functional currency", "exchange rate"],
        "concepts": ["Functional vs. Reporting Currency", "Transaction Gains & Losses", "Translation Methods", "Remeasurement", "Hedging Foreign Currency Risk"],
        "diagramType": "currency-flow",
        "relatedModules": ["mod06", "mod27"],
    },
    {
        "id": "mod26", "title": "Pension & Post-Retirement Benefits", "level": "master", "ascRefs": ["715"],
        "keywords": ["pension", "defined benefit", "defined contribution", "pbo", "post-retirement", "actuarial"],
        "concepts": ["Defined Benefit vs. Defined Contribution", "Projected Benefit Obligation (PBO)", "Plan Assets & Funded Status", "Pension Expense Components", "Other Post-Retirement Benefits"],
        "diagramType": "pension-components",
        "relatedModules": ["mod14", "mod06"],
    },
    {
        "id": "mod27", "title": "Fair Value Measurement (ASC 820)", "level": "master", "ascRefs": ["820"],
        "keywords": ["fair value", "asc 820", "level 1", "level 2", "level 3", "observable inputs", "mark to market"],
        "concepts": ["Fair Value Definition", "The Fair Value Hierarchy", "Level 1 Inputs", "Level 2 Inputs", "Level 3 Inputs"],
        "diagramType": "hierarchy-pyramid",
        "relatedModules": ["mod09", "mod24"],
    },
    {
        "id": "mod28", "title": "SEC Reporting & Financial Statement Analysis", "level": "master", "ascRefs": ["270", "280"],
        "keywords": ["sec reporting", "10-k", "10-q", "financial analysis", "ratio analysis", "horizontal analysis", "vertical analysis"],
        "concepts": ["SEC Filing Requirements", "Form 10-K & 10-Q", "Horizontal & Vertical Analysis", "Ratio Analysis Framework", "Segment Reporting"],
        "diagramType": "sec-filing-flow",
        "relatedModules": ["mod06", "mod10"],
    },
]


# ======================================================================
# SVG DIAGRAM TEMPLATES
# ======================================================================

SVG_TEMPLATES = {
    "equation-balance": """<svg viewBox="0 0 600 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:600px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.box{rx:8;ry:8;stroke:#CDAA7D;stroke-width:2}.label{font-size:14px;font-weight:700}.sublabel{font-size:11px;fill:#5A5F6B}</style></defs>
  <rect class="box" x="10" y="40" width="160" height="100" fill="#f8f7f4"/>
  <text class="label" x="90" y="80" text-anchor="middle">Assets</text>
  <text class="sublabel" x="90" y="100" text-anchor="middle">What you OWN</text>
  <text class="sublabel" x="90" y="116" text-anchor="middle">Cash, Equipment, AR</text>
  <text x="195" y="95" font-size="28" font-weight="700" fill="#CDAA7D">=</text>
  <rect class="box" x="220" y="40" width="160" height="100" fill="#f8f7f4"/>
  <text class="label" x="300" y="80" text-anchor="middle">Liabilities</text>
  <text class="sublabel" x="300" y="100" text-anchor="middle">What you OWE</text>
  <text class="sublabel" x="300" y="116" text-anchor="middle">Loans, AP, Taxes</text>
  <text x="400" y="95" font-size="28" font-weight="700" fill="#CDAA7D">+</text>
  <rect class="box" x="425" y="40" width="160" height="100" fill="#f8f7f4"/>
  <text class="label" x="505" y="80" text-anchor="middle">Equity</text>
  <text class="sublabel" x="505" y="100" text-anchor="middle">What's LEFT OVER</text>
  <text class="sublabel" x="505" y="116" text-anchor="middle">Owner's stake</text>
  <text x="300" y="175" text-anchor="middle" font-size="13" fill="#5A5F6B">This equation ALWAYS balances. Every transaction affects at least two of these.</text>
</svg>""",

    "t-account": """<svg viewBox="0 0 500 220" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:500px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.title{font-size:14px;font-weight:700}.item{font-size:12px}.hint{font-size:11px;fill:#5A5F6B}</style></defs>
  <text class="title" x="250" y="25" text-anchor="middle">Cash (T-Account)</text>
  <line x1="60" y1="45" x2="440" y2="45" stroke="#2A2D35" stroke-width="2"/>
  <line x1="250" y1="45" x2="250" y2="190" stroke="#2A2D35" stroke-width="2"/>
  <text class="title" x="155" y="65" text-anchor="middle" fill="#CDAA7D">DEBIT (Left)</text>
  <text class="title" x="345" y="65" text-anchor="middle" fill="#B87333">CREDIT (Right)</text>
  <text class="item" x="80" y="90">Customer pays $5,000</text>
  <text class="item" x="80" y="110">Owner invests $10,000</text>
  <text class="item" x="270" y="90">Pay rent $2,000</text>
  <text class="item" x="270" y="110">Buy supplies $500</text>
  <line x1="60" y1="140" x2="240" y2="140" stroke="#CDAA7D" stroke-width="1" stroke-dasharray="4"/>
  <line x1="260" y1="140" x2="440" y2="140" stroke="#B87333" stroke-width="1" stroke-dasharray="4"/>
  <text class="item" x="80" y="160" font-weight="700">Total: $15,000</text>
  <text class="item" x="270" y="160" font-weight="700">Total: $2,500</text>
  <text class="hint" x="250" y="200" text-anchor="middle">Balance = $12,500 (Debit side wins = normal for assets)</text>
</svg>""",

    "account-tree": """<svg viewBox="0 0 600 240" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:600px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.box{rx:6;ry:6;stroke:#CDAA7D;stroke-width:1.5}.cat{font-size:12px;font-weight:700}.num{font-size:10px;fill:#5A5F6B}</style></defs>
  <rect class="box" x="220" y="5" width="160" height="32" fill="#2A2D35"/>
  <text x="300" y="26" text-anchor="middle" font-size="13" font-weight="700" fill="#CDAA7D">Chart of Accounts</text>
  <line x1="300" y1="37" x2="300" y2="55" stroke="#ccc"/>
  <line x1="60" y1="55" x2="540" y2="55" stroke="#ccc"/>
  <g transform="translate(0,0)"><line x1="60" y1="55" x2="60" y2="70" stroke="#ccc"/>
    <rect class="box" x="10" y="70" width="100" height="48" fill="#f8f7f4"/>
    <text class="cat" x="60" y="89" text-anchor="middle">Assets</text>
    <text class="num" x="60" y="106" text-anchor="middle">1000-1999</text></g>
  <g transform="translate(120,0)"><line x1="60" y1="55" x2="60" y2="70" stroke="#ccc"/>
    <rect class="box" x="10" y="70" width="100" height="48" fill="#f8f7f4"/>
    <text class="cat" x="60" y="89" text-anchor="middle">Liabilities</text>
    <text class="num" x="60" y="106" text-anchor="middle">2000-2999</text></g>
  <g transform="translate(240,0)"><line x1="60" y1="55" x2="60" y2="70" stroke="#ccc"/>
    <rect class="box" x="10" y="70" width="100" height="48" fill="#f8f7f4"/>
    <text class="cat" x="60" y="89" text-anchor="middle">Equity</text>
    <text class="num" x="60" y="106" text-anchor="middle">3000-3999</text></g>
  <g transform="translate(360,0)"><line x1="60" y1="55" x2="60" y2="70" stroke="#ccc"/>
    <rect class="box" x="10" y="70" width="100" height="48" fill="#f8f7f4"/>
    <text class="cat" x="60" y="89" text-anchor="middle">Revenue</text>
    <text class="num" x="60" y="106" text-anchor="middle">4000-4999</text></g>
  <g transform="translate(480,0)"><line x1="60" y1="55" x2="60" y2="70" stroke="#ccc"/>
    <rect class="box" x="10" y="70" width="100" height="48" fill="#f8f7f4"/>
    <text class="cat" x="60" y="89" text-anchor="middle">Expenses</text>
    <text class="num" x="60" y="106" text-anchor="middle">5000-9999</text></g>
  <text x="300" y="155" text-anchor="middle" font-size="12" fill="#5A5F6B">Each account gets a number. The first digit tells you the category.</text>
  <text x="300" y="173" text-anchor="middle" font-size="12" fill="#5A5F6B">Example: 1010 = Cash (asset), 4010 = Service Revenue</text>
</svg>""",

    "journal-entry": """<svg viewBox="0 0 520 180" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:520px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.hdr{font-size:12px;font-weight:700;fill:#fff}.row{font-size:12px}.hint{font-size:11px;fill:#5A5F6B}</style></defs>
  <rect x="20" y="10" width="480" height="28" rx="6" fill="#2A2D35"/>
  <text class="hdr" x="40" y="29">Date</text><text class="hdr" x="140" y="29">Account</text><text class="hdr" x="340" y="29">Debit</text><text class="hdr" x="430" y="29">Credit</text>
  <rect x="20" y="42" width="480" height="28" rx="0" fill="#f8f7f4"/>
  <text class="row" x="40" y="61">Jan 15</text><text class="row" x="140" y="61" font-weight="600">Cash</text><text class="row" x="340" y="61" fill="#2d6a4f">$5,000</text><text class="row" x="430" y="61"></text>
  <rect x="20" y="70" width="480" height="28" rx="0" fill="#fff"/>
  <text class="row" x="40" y="89"></text><text class="row" x="160" y="89" font-style="italic">Service Revenue</text><text class="row" x="340" y="89"></text><text class="row" x="430" y="89" fill="#2d6a4f">$5,000</text>
  <rect x="20" y="102" width="480" height="24" rx="0" fill="#f8f7f4"/>
  <text class="hint" x="140" y="118">Received payment for consulting services</text>
  <text class="hint" x="260" y="150" text-anchor="middle">Debits are listed first. Credits are indented.</text>
  <text class="hint" x="260" y="168" text-anchor="middle">Total debits MUST equal total credits.</text>
</svg>""",

    "timeline-comparison": """<svg viewBox="0 0 600 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:600px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.title{font-size:13px;font-weight:700}.item{font-size:11px}.hint{font-size:11px;fill:#5A5F6B}</style></defs>
  <text class="title" x="300" y="20" text-anchor="middle">Cash Basis vs. Accrual Basis</text>
  <line x1="80" y1="60" x2="520" y2="60" stroke="#CDAA7D" stroke-width="2"/>
  <circle cx="180" cy="60" r="6" fill="#CDAA7D"/><text class="item" x="180" y="50" text-anchor="middle">Dec: Work Done</text>
  <circle cx="420" cy="60" r="6" fill="#CDAA7D"/><text class="item" x="420" y="50" text-anchor="middle">Jan: Cash Received</text>
  <rect x="40" y="80" width="240" height="36" rx="6" fill="#2A2D35"/>
  <text x="160" y="103" text-anchor="middle" font-size="12" font-weight="600" fill="#CDAA7D">Accrual: Revenue in DEC</text>
  <rect x="320" y="80" width="240" height="36" rx="6" fill="#353840"/>
  <text x="440" y="103" text-anchor="middle" font-size="12" font-weight="600" fill="#CDAA7D">Cash: Revenue in JAN</text>
  <text class="hint" x="300" y="145" text-anchor="middle">Accrual records revenue when you EARN it (Dec).</text>
  <text class="hint" x="300" y="163" text-anchor="middle">Cash records revenue when you GET PAID (Jan).</text>
  <text class="hint" x="300" y="181" text-anchor="middle">Most businesses should use accrual -- it's more accurate.</text>
</svg>""",

    "statement-flow": """<svg viewBox="0 0 600 260" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:600px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.box{rx:8;ry:8;stroke:#CDAA7D;stroke-width:1.5}.label{font-size:12px;font-weight:700}.sub{font-size:10px;fill:#5A5F6B}</style></defs>
  <rect class="box" x="200" y="10" width="200" height="50" fill="#2A2D35"/>
  <text x="300" y="32" text-anchor="middle" font-size="13" font-weight="700" fill="#CDAA7D">Income Statement</text>
  <text x="300" y="48" text-anchor="middle" font-size="10" fill="rgba(255,255,255,0.6)">Revenue - Expenses = Net Income</text>
  <line x1="300" y1="60" x2="300" y2="80" stroke="#CDAA7D" stroke-width="1.5" marker-end="url(#arrow)"/>
  <rect class="box" x="200" y="80" width="200" height="50" fill="#353840"/>
  <text x="300" y="102" text-anchor="middle" font-size="13" font-weight="700" fill="#CDAA7D">Retained Earnings</text>
  <text x="300" y="118" text-anchor="middle" font-size="10" fill="rgba(255,255,255,0.6)">+ Net Income - Dividends</text>
  <line x1="300" y1="130" x2="150" y2="160" stroke="#CDAA7D" stroke-width="1.5"/>
  <line x1="300" y1="130" x2="450" y2="160" stroke="#CDAA7D" stroke-width="1.5"/>
  <rect class="box" x="40" y="160" width="200" height="50" fill="#f8f7f4"/>
  <text class="label" x="140" y="182" text-anchor="middle">Balance Sheet</text>
  <text class="sub" x="140" y="198" text-anchor="middle">Assets = Liab + Equity</text>
  <rect class="box" x="360" y="160" width="200" height="50" fill="#f8f7f4"/>
  <text class="label" x="460" y="182" text-anchor="middle">Cash Flow Statement</text>
  <text class="sub" x="460" y="198" text-anchor="middle">Where the cash went</text>
  <text x="300" y="240" text-anchor="middle" font-size="11" fill="#5A5F6B">Net income flows into retained earnings, which appears on the balance sheet.</text>
  <text x="300" y="255" text-anchor="middle" font-size="11" fill="#5A5F6B">The cash flow statement explains changes in the cash balance (a BS asset).</text>
</svg>""",

    "two-column-rec": """<svg viewBox="0 0 600 240" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:600px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.hdr{font-size:12px;font-weight:700;fill:#fff}.row{font-size:11px}.amt{font-size:11px;text-anchor:end}</style></defs>
  <rect x="20" y="10" width="260" height="28" rx="6" fill="#2A2D35"/>
  <text class="hdr" x="150" y="29" text-anchor="middle">Your Books (Book Balance)</text>
  <rect x="320" y="10" width="260" height="28" rx="6" fill="#2A2D35"/>
  <text class="hdr" x="450" y="29" text-anchor="middle">Bank Statement</text>
  <text class="row" x="30" y="58">Starting balance</text><text class="amt" x="270" y="58">$10,000</text>
  <text class="row" x="330" y="58">Starting balance</text><text class="amt" x="570" y="58">$10,500</text>
  <text class="row" x="30" y="78" fill="#2d6a4f">+ Bank credited interest</text><text class="amt" x="270" y="78" fill="#2d6a4f">+$25</text>
  <text class="row" x="330" y="78" fill="#dc2626">- Outstanding checks</text><text class="amt" x="570" y="78" fill="#dc2626">-$800</text>
  <text class="row" x="30" y="98" fill="#dc2626">- Bank service fee</text><text class="amt" x="270" y="98" fill="#dc2626">-$15</text>
  <text class="row" x="330" y="98" fill="#2d6a4f">+ Deposits in transit</text><text class="amt" x="570" y="98" fill="#2d6a4f">+$310</text>
  <line x1="20" y1="112" x2="280" y2="112" stroke="#CDAA7D" stroke-width="1.5"/>
  <line x1="320" y1="112" x2="580" y2="112" stroke="#CDAA7D" stroke-width="1.5"/>
  <text x="30" y="132" font-size="12" font-weight="700">Adjusted: $10,010</text>
  <text x="330" y="132" font-size="12" font-weight="700">Adjusted: $10,010</text>
  <text x="300" y="160" text-anchor="middle" font-size="24" fill="#CDAA7D" font-weight="700">=</text>
  <text x="300" y="190" text-anchor="middle" font-size="12" fill="#5A5F6B">Both sides must match. If they don't, something's missing.</text>
</svg>""",

    "circular-steps": """<svg viewBox="0 0 500 280" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:500px">
  <defs><style>text{font-family:system-ui,sans-serif;fill:#2A2D35}.step{font-size:11px;font-weight:600}.num{font-size:16px;font-weight:700;fill:#CDAA7D}</style></defs>
  <text x="250" y="25" text-anchor="middle" font-size="14" font-weight="700">The Accounting Cycle</text>
  <g transform="translate(250,155)">
    <circle cx="0" cy="0" r="100" fill="none" stroke="#e5e2d9" stroke-width="2" stroke-dasharray="8,4"/>
    <g transform="translate(0,-100)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">1</text><text class="step" x="0" y="-30" text-anchor="middle">Analyze</text></g>
    <g transform="translate(87,-50)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">2</text><text class="step" x="30" y="5" text-anchor="start">Record</text></g>
    <g transform="translate(87,50)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">3</text><text class="step" x="30" y="5" text-anchor="start">Post</text></g>
    <g transform="translate(0,100)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">4</text><text class="step" x="0" y="35" text-anchor="middle">Trial Balance</text></g>
    <g transform="translate(-87,50)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">5</text><text class="step" x="-30" y="5" text-anchor="end">Adjust</text></g>
    <g transform="translate(-87,-50)"><circle r="22" fill="#2A2D35"/><text class="num" x="0" y="5" text-anchor="middle" fill="#CDAA7D">6</text><text class="step" x="-30" y="5" text-anchor="end">Close</text></g>
  </g>
</svg>""",
}

# For modules without a specific SVG template, generate a generic one
def get_generic_diagram(module_title):
    return f"""<svg viewBox="0 0 500 80" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:500px">
  <rect x="0" y="0" width="500" height="80" rx="8" fill="#f8f7f4" stroke="#CDAA7D" stroke-width="1.5"/>
  <text x="250" y="35" text-anchor="middle" font-family="system-ui,sans-serif" font-size="14" font-weight="700" fill="#2A2D35">{module_title}</text>
  <text x="250" y="58" text-anchor="middle" font-family="system-ui,sans-serif" font-size="11" fill="#5A5F6B">Visual diagram coming soon</text>
</svg>"""


# ======================================================================
# KNOWLEDGE MATCHING
# ======================================================================

def load_knowledge():
    """Load all knowledge entries from both files."""
    entries = []
    for path in [KNOWLEDGE_FILE, ASU_FILE]:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    entries.extend(data)
    log.info(f"Loaded {len(entries)} total knowledge entries")
    return entries


def score_entry_for_module(entry, module):
    """Score how relevant a knowledge entry is to a module. Higher = better match."""
    score = 0
    entry_text = ' '.join(entry.get('patterns', [])).lower() + ' ' + entry.get('response', '').lower()[:200]

    # Match against module keywords
    for kw in module['keywords']:
        if kw.lower() in entry_text:
            score += 3

    # Match against concept names
    for concept in module['concepts']:
        concept_lower = concept.lower()
        # Exact concept match in patterns
        for pat in entry.get('patterns', []):
            if concept_lower in pat.lower() or pat.lower() in concept_lower:
                score += 5
        # Concept terms in response
        if concept_lower in entry_text:
            score += 2

    # Match against module title
    title_words = [w.lower() for w in module['title'].split() if len(w) > 3]
    for tw in title_words:
        if tw in entry_text:
            score += 1

    # ASC reference matching
    for ref in module.get('ascRefs', []):
        if f"asc {ref}" in entry_text or f"asc{ref}" in entry_text:
            score += 4

    return score


def find_best_entries(module, knowledge, max_per_concept=3, max_general=5):
    """Find the best knowledge entries for each concept and for the module overall."""
    concept_entries = {}
    general_entries = []

    # Score all entries
    scored = []
    for entry in knowledge:
        s = score_entry_for_module(entry, module)
        if s > 0:
            scored.append((s, entry))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Assign to concepts
    used_responses = set()
    for concept in module['concepts']:
        concept_lower = concept.lower()
        matches = []
        for s, entry in scored:
            resp_hash = entry.get('response', '')[:100]
            if resp_hash in used_responses:
                continue
            # Check if this entry is relevant to this specific concept
            entry_text = ' '.join(entry.get('patterns', [])).lower() + ' ' + entry.get('response', '').lower()[:200]
            if concept_lower in entry_text or any(concept_lower in p.lower() for p in entry.get('patterns', [])):
                matches.append(entry)
                used_responses.add(resp_hash)
                if len(matches) >= max_per_concept:
                    break
        concept_entries[concept] = matches

    # General entries (top scored not yet used)
    for s, entry in scored:
        resp_hash = entry.get('response', '')[:100]
        if resp_hash not in used_responses:
            general_entries.append(entry)
            used_responses.add(resp_hash)
            if len(general_entries) >= max_general:
                break

    return concept_entries, general_entries


# ======================================================================
# CONTENT GENERATION (plain-language, down-to-earth style)
# ======================================================================

def simplify_text(text, max_len=400):
    """Clean up and truncate text."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > max_len:
        # Cut at sentence boundary
        cut = text[:max_len].rfind('.')
        if cut > max_len // 2:
            text = text[:cut + 1]
        else:
            text = text[:max_len] + '...'
    return text


def build_concept_details(concept_name, matched_entries):
    """Build bullet-point details from matched knowledge entries."""
    details = []
    for entry in matched_entries:
        resp = entry.get('response', '')
        if not resp:
            continue
        # Extract useful sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', resp) if len(s.strip()) > 30]
        for sent in sentences[:2]:
            clean = simplify_text(sent, 200)
            if clean and clean not in details:
                details.append(clean)
    return details[:4]  # Max 4 bullet points per concept


def build_example(concept_name, matched_entries):
    """Try to extract or construct a real-world example."""
    for entry in matched_entries:
        resp = entry.get('response', '').lower()
        # Look for example-like content
        for marker in ['example:', 'for example', 'for instance', 'such as', 'e.g.']:
            idx = resp.find(marker)
            if idx != -1:
                example_text = entry['response'][idx:idx + 250]
                # Clean up
                end = example_text.find('.', 50)
                if end > 0:
                    example_text = example_text[:end + 1]
                return {"scenario": simplify_text(example_text, 250)}
    return None


def build_callout(concept_name, module_level):
    """Generate a tip or common-mistake callout based on the concept."""
    # Common mistakes and tips by concept keyword
    tips = {
        "assets": {"type": "tip", "text": "Remember: just because you paid for something doesn't always make it an asset. It has to provide future benefit. A month's rent you already used? That's an expense, not an asset."},
        "liabilities": {"type": "warning", "text": "Don't confuse liabilities with expenses. A liability is something you still owe. An expense is money already spent. Unpaid bills are liabilities until you pay them."},
        "equity": {"type": "tip", "text": "Think of equity as your business's net worth. If you sold everything and paid off all debts, equity is what's left. It's the owner's slice of the pie."},
        "debits": {"type": "tip", "text": "Here's a cheat sheet: Debits increase assets and expenses. Credits increase liabilities, equity, and revenue. When in doubt, ask: 'What type of account is this?'"},
        "credits": {"type": "tip", "text": "Credits aren't 'good' and debits aren't 'bad.' They're just left (debit) and right (credit) sides of the accounting equation. Both are necessary for every transaction."},
        "fifo": {"type": "warning", "text": "FIFO and LIFO can produce very different profit numbers when prices are changing. If costs are rising, FIFO shows higher profits (and higher taxes). LIFO shows lower profits (and lower taxes)."},
        "depreciation": {"type": "tip", "text": "Depreciation doesn't mean an asset is literally losing value. It's just spreading the cost over time. Your building might actually be worth MORE than you paid, but you still depreciate it on your books."},
        "accrual": {"type": "warning", "text": "The #1 mistake small businesses make: mixing up cash and accrual accounting. Pick one method and stick with it. Switching mid-year creates a mess."},
        "revenue recognition": {"type": "tip", "text": "The golden rule: you don't record revenue when you get the cash. You record it when you've done the work. Got paid in advance? That's a liability (unearned revenue) until you deliver."},
        "bank reconciliation": {"type": "warning", "text": "Never skip your monthly bank rec. It's the single best way to catch errors, fraud, and forgotten transactions. If the numbers don't match, something is wrong."},
        "internal controls": {"type": "tip", "text": "The most important control is segregation of duties: don't let one person handle money AND record the transactions. It's not about trust -- it's about protecting everyone."},
        "journal entry": {"type": "tip", "text": "Always write a description with your journal entries. Future you (or your auditor) will thank you. A journal entry without context is useless six months later."},
    }

    concept_lower = concept_name.lower()
    for keyword, callout in tips.items():
        if keyword in concept_lower:
            return callout

    # Generic tip for concepts without a specific callout
    if module_level in ('beginner', 'intermediate'):
        return {"type": "tip", "text": "If this concept feels confusing, don't worry. Most accountants didn't fully 'get it' until they saw it in practice. Focus on the big idea first, then the details will click."}
    return None


def build_sources(matched_entries):
    """Extract source citations from knowledge entries."""
    sources = []
    seen_urls = set()
    for entry in matched_entries:
        url = entry.get('_url', '')
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        source_name = entry.get('_source', '')
        # Build a readable title
        if 'wikipedia' in source_name:
            title = 'Wikipedia'
        elif 'accountingtools' in source_name:
            title = 'AccountingTools'
        elif 'cfi' in source_name:
            title = 'Corporate Finance Institute'
        elif 'irs' in source_name:
            title = 'IRS.gov'
        else:
            title = source_name.replace('_', ' ').title()

        # Extract topic from URL
        slug = url.rstrip('/').split('/')[-1].replace('_', ' ').replace('-', ' ')
        slug = re.sub(r'\.html?$', '', slug)
        if len(slug) > 3:
            title = f"{title} -- {slug.title()}"

        sources.append({
            "title": title[:80],
            "url": url,
            "retrieved": entry.get('_date', date.today().isoformat())
        })
    return sources[:6]  # Max 6 sources per concept


# ======================================================================
# MAIN ENHANCEMENT PIPELINE
# ======================================================================

def enhance_module(module, knowledge):
    """Build the enhanced content for a single module."""
    log.info(f"Enhancing {module['id']}: {module['title']}")

    concept_entries, general_entries = find_best_entries(module, knowledge)

    # Build enhanced concepts
    enhanced_concepts = []
    all_sources = []

    for concept_name in module['concepts']:
        matched = concept_entries.get(concept_name, [])
        details = build_concept_details(concept_name, matched)
        example = build_example(concept_name, matched)
        callout = build_callout(concept_name, module['level'])
        sources = build_sources(matched)
        all_sources.extend(sources)

        enhanced_concepts.append({
            "term": concept_name,
            "details": details,
            "example": example,
            "callout": callout,
            "sources": sources,
        })

    # Deduplicate all_sources
    seen = set()
    unique_sources = []
    for s in all_sources + build_sources(general_entries):
        if s['url'] not in seen:
            seen.add(s['url'])
            unique_sources.append(s)

    # Get SVG diagram
    diagram_type = module.get('diagramType', '')
    svg = SVG_TEMPLATES.get(diagram_type, get_generic_diagram(module['title']))

    # Build key takeaways
    takeaways = generate_takeaways(module, concept_entries)

    return {
        "lastEnhanced": date.today().isoformat(),
        "enhancementVersion": 1,
        "diagram": {
            "type": diagram_type,
            "svg": svg
        },
        "concepts": enhanced_concepts,
        "keyTakeaways": takeaways,
        "relatedModules": module.get('relatedModules', []),
        "sources": unique_sources[:10],
    }


def generate_takeaways(module, concept_entries):
    """Generate 3-5 key takeaway bullets for the module."""
    takeaways = []

    # Module-specific takeaways
    takeaway_map = {
        "mod01": [
            "Assets = Liabilities + Equity. This equation is the foundation of ALL accounting.",
            "Every transaction affects at least two accounts -- that's why it always balances.",
            "If someone asks 'where did the money go?' this equation is your starting point.",
        ],
        "mod02": [
            "Every transaction needs at least one debit and one credit of equal amounts.",
            "Debits aren't bad and credits aren't good -- they're just left and right.",
            "Assets and expenses normally have debit balances. Liabilities, equity, and revenue normally have credit balances.",
        ],
        "mod03": [
            "Your chart of accounts is like a filing system -- every dollar goes into a numbered folder.",
            "The general ledger is the master record. If it's not in the GL, it didn't happen (financially speaking).",
            "Sub-ledgers handle the details (each customer, each vendor). The GL just shows the totals.",
        ],
        "mod04": [
            "Journal entries are the atomic unit of accounting -- every financial event gets one.",
            "Debits always go first, credits are indented. Total debits must equal total credits.",
            "Always include a description. Your future self and your auditor will thank you.",
        ],
        "mod05": [
            "Accrual = record when earned/incurred. Cash = record when money moves. That's the core difference.",
            "GAAP requires accrual accounting because it gives a more accurate picture.",
            "The matching principle: expenses should show up in the same period as the revenue they helped generate.",
        ],
        "mod06": [
            "Four statements tell the full story: Balance Sheet, Income Statement, Cash Flow, and Equity.",
            "Net income from the Income Statement flows into Retained Earnings on the Balance Sheet.",
            "The Cash Flow Statement explains why your cash balance changed -- even if you were profitable, you might be short on cash.",
        ],
        "mod07": [
            "Bank recs catch errors, fraud, and forgotten transactions. Do them monthly, no exceptions.",
            "The goal: adjusted book balance = adjusted bank balance. If they don't match, keep digging.",
            "Outstanding checks and deposits in transit are the most common reconciling items.",
        ],
        "mod08": [
            "The accounting cycle repeats every period: Analyze, Record, Post, Adjust, Report, Close.",
            "Closing entries zero out revenue and expense accounts so you start fresh next period.",
            "The post-closing trial balance should only have balance sheet accounts (assets, liabilities, equity).",
        ],
    }

    if module['id'] in takeaway_map:
        return takeaway_map[module['id']]

    # Generic takeaways for modules without specific ones
    return [
        f"Understanding {module['title'].lower()} is essential for accurate financial reporting.",
        "Practice with real numbers to build your confidence with these concepts.",
        "When in doubt, trace the transaction back to its journal entry -- that's where the logic lives.",
    ]


# ======================================================================
# STATE MANAGEMENT
# ======================================================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"next_module_index": 0, "last_run": None, "history": []}


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)


def load_enhanced():
    if os.path.exists(ENHANCED_FILE):
        with open(ENHANCED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_enhanced(data):
    with open(ENHANCED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ======================================================================
# ENTRY POINT
# ======================================================================

def main():
    log.info("=" * 60)
    log.info(f"Vera Module Enhancer -- {datetime.now().isoformat()}")
    log.info("=" * 60)

    state = load_state()
    enhanced = load_enhanced()
    knowledge = load_knowledge()

    idx = state['next_module_index']
    if idx >= len(MODULES):
        idx = 0  # Loop back

    module = MODULES[idx]
    log.info(f"Processing module {idx + 1}/{len(MODULES)}: {module['id']} - {module['title']}")

    # Check existing version
    existing = enhanced.get(module['id'], {})
    existing_version = existing.get('enhancementVersion', 0)

    # Enhance
    result = enhance_module(module, knowledge)
    result['enhancementVersion'] = existing_version + 1

    # Merge -- preserve any manually added content
    if existing:
        # Keep manual overrides if they exist
        for key in ['manualNotes', 'customDiagram']:
            if key in existing:
                result[key] = existing[key]

    enhanced[module['id']] = result
    save_enhanced(enhanced)

    # Update state
    state['next_module_index'] = idx + 1
    state['last_run'] = datetime.now().isoformat()
    state['history'].append({
        "date": date.today().isoformat(),
        "module": module['id'],
        "version": result['enhancementVersion'],
        "concepts_enriched": len(result['concepts']),
        "sources_found": len(result['sources']),
    })
    # Keep last 100 history entries
    state['history'] = state['history'][-100:]
    save_state(state)

    log.info(f"Enhanced {module['id']} (v{result['enhancementVersion']}): "
             f"{len(result['concepts'])} concepts, {len(result['sources'])} sources")
    log.info(f"Next run will process: {MODULES[(idx + 1) % len(MODULES)]['id']}")
    log.info("Enhancer complete.")

    return module['id']


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
