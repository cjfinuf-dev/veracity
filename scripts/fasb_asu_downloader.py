"""
FASB ASU Downloader & Knowledge Extractor
Downloads ASU PDFs from fasb.org via Playwright (Cloudflare-protected),
extracts ASC codification references and text, generates layperson translations,
and stores them in the Vera knowledge base with outbound FASB links.

Usage: python fasb_asu_downloader.py [--limit N]
"""

import json
import os
import re
import sys
import time
import logging
from datetime import date
from urllib.parse import unquote

# ── Paths ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
PDF_DIR = os.path.join(DATA_DIR, 'asu_pdfs')
ASU_KNOWLEDGE_FILE = os.path.join(DATA_DIR, 'asu-knowledge.json')
ASU_INDEX_FILE = os.path.join(DATA_DIR, 'asu-index.json')
LOG_DIR = os.path.join(ROOT, 'scripts', 'logs')

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f'asu_downloader_{date.today().isoformat()}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('asu_downloader')

# ── All ASU PDF URLs (scraped from fasb.org/standards/accounting-standard-updates) ──
# Format: (asu_number, pdf_url, title_hint)
# These are the official FASB download links.

FASB_BASE = "https://www.fasb.org"

ASU_CATALOG = [
    # 2025
    ("2025-12", "/Page/Document?pdf=ASU%202025-12.pdf&title=Accounting%20Standards%20Update%202025-12%E2%80%94Codification%20Improvements"),
    ("2025-11", "/Page/Document?pdf=ASU%202025-11.pdf&title=Accounting%20Standards%20Update%202025-11%E2%80%94Interim%20Reporting"),
    ("2025-10", "/Page/Document?pdf=ASU%202025-10.pdf&title=Accounting%20Standards%20Update%202025-10%E2%80%94Government%20Assistance"),
    ("2025-09", "/Page/Document?pdf=ASU%202025-09.pdf&title=Accounting%20Standards%20Update%202025-09%E2%80%94Derivatives%20and%20Hedging"),
    ("2025-08", "/Page/Document?pdf=ASU%202025-08.pdf&title=Accounting%20Standards%20Update%202025-08%E2%80%94Financial%20Instruments"),
    ("2025-07", "/Page/Document?pdf=ASU%202025-07.pdf&title=Accounting%20Standards%20Update%202025-07%E2%80%94Derivatives%20and%20Hedging"),
    ("2025-06", "/Page/Document?pdf=ASU%202025-06.pdf&title=Accounting%20Standards%20Update%202025-06%E2%80%94Intangibles"),
    ("2025-05", "/Page/Document?pdf=ASU%202025-05.pdf&title=Accounting%20Standards%20Update%202025-05%E2%80%94Financial%20Instruments"),
    ("2025-04", "/Page/Document?pdf=ASU%202025-04.pdf&title=ASU%202025-04%E2%80%94Compensation%E2%80%94Stock%20Compensation"),
    ("2025-03", "/Page/Document?pdf=ASU%202025-03.pdf&title=Accounting%20Standards%20Update%20No.%202025-03%20Business%20Combinations"),
    ("2025-02", "/Page/Document?pdf=ASU%202025-02.pdf&title=Accounting%20Standards%20Update%202025-02%E2%80%94Liabilities"),
    ("2025-01", "/Page/Document?pdf=ASU%202025-01.pdf&title=Accounting%20Standards%20Update%202025-01%E2%80%94Income%20Taxes"),
    # 2024
    ("2024-04", "/Page/Document?pdf=ASU%202024-04.pdf&title=Accounting%20Standards%20Update%202024-04%E2%80%94Debt"),
    ("2024-03", "/Page/Document?pdf=ASU%202024-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202024-03%E2%80%94Income%20Taxes"),
    ("2024-02", "/Page/Document?pdf=ASU%202024-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202024-02%E2%80%94Codification%20Improvements"),
    ("2024-01", "/Page/Document?pdf=ASU%202024-01.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202024-01%E2%80%94Compensation"),
    # 2023
    ("2023-09", "/page/document?pdf=ASU%202023-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-09%E2%80%94Income%20Taxes"),
    ("2023-08", "/page/Document?pdf=ASU%202023-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-08%E2%80%94Intangibles"),
    ("2023-07", "/page/Document?pdf=ASU%202023-07.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-07%E2%80%94Segment%20Reporting"),
    ("2023-06", "/page/Document?pdf=ASU%202023-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-06%E2%80%94Disclosure%20Improvements"),
    ("2023-05", "/page/Document?pdf=ASU%202023-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-05%E2%80%94Business%20Combinations"),
    ("2023-04", "/page/Document?pdf=ASU%202023-04.pdf&title=Accounting%20Standards%20Update%202023-04%E2%80%94Liabilities"),
    ("2023-03", "/page/Document?pdf=ASU%202023-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202023-03%E2%80%94Presentation"),
    ("2023-02", "/page/Document?pdf=ASU%202023-02%E2%80%94Investments%E2%80%94Equity%20Method%20and%20Joint%20Ventures"),
    ("2023-01", "/page/Document?pdf=ASU%202023-01%E2%80%94Leases%20(Topic%20842)%E2%80%94Common%20Control%20Arrangements"),
    # 2022
    ("2022-06", "/page/document?pdf=ASU%202022-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-06%E2%80%94Reference%20Rate%20Reform"),
    ("2022-05", "/page/document?pdf=ASU%202022-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-05%E2%80%94Financial%20Services"),
    ("2022-04", "/page/document?pdf=ASU%202022-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-04%E2%80%94LIABILITIES"),
    ("2022-03", "/page/document?pdf=ASU%202022-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-03%E2%80%94Fair%20Value"),
    ("2022-02", "/page/document?pdf=ASU%202022-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-02%E2%80%94FINANCIAL%20INSTRUMENTS"),
    ("2022-01", "/page/document?pdf=ASU%202022-01.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202022-01%E2%80%94DERIVATIVES"),
    # 2021
    ("2021-10", "/page/document?pdf=ASU_2021-10.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-10%E2%80%94GOVERNMENT%20ASSISTANCE"),
    ("2021-09", "/page/document?pdf=ASU_2021-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-09%E2%80%94LEASES"),
    ("2021-08", "/page/document?pdf=ASU_2021-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-08%E2%80%94BUSINESS%20COMBINATIONS"),
    ("2021-07", "/page/document?pdf=ASU_2021-07.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-07%E2%80%94COMPENSATION"),
    ("2021-06", "/page/document?pdf=ASU+2021-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-06%E2%80%94PRESENTATION"),
    ("2021-05", "/page/document?pdf=ASU+2021-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-05%E2%80%94LEASES"),
    ("2021-04", "/page/document?pdf=ASU+2021-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-04%E2%80%94EARNINGS%20PER%20SHARE"),
    ("2021-03", "/page/document?pdf=ASU+2021-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-03%E2%80%94INTANGIBLES"),
    ("2021-02", "/page/document?pdf=ASU+2021-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-02%E2%80%94FRANCHISORS"),
    ("2021-01", "/page/document?pdf=ASU+2021-01.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202021-01%E2%80%94REFERENCE%20RATE%20REFORM"),
    # 2020
    ("2020-11", "/page/document?pdf=ASU+2020-11.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-11%E2%80%94FINANCIAL%20SERVICES"),
    ("2020-10", "/page/document?pdf=ASU+2020-10.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-10%E2%80%94CODIFICATION%20IMPROVEMENTS"),
    ("2020-09", "/page/document?pdf=ASU+2020-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-09%E2%80%94DEBT"),
    ("2020-08", "/page/document?pdf=ASU+2020-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-08%E2%80%94CODIFICATION%20IMPROVEMENTS"),
    ("2020-07", "/page/document?pdf=ASU+2020-07.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-07%E2%80%94NOT-FOR-PROFIT"),
    ("2020-06", "/page/document?pdf=ASU+2020-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-06%E2%80%94DEBT"),
    ("2020-05", "/page/document?pdf=ASU+2020-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-05%E2%80%94REVENUE"),
    ("2020-04", "/page/document?pdf=ASU+2020-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-04%E2%80%94REFERENCE%20RATE%20REFORM"),
    ("2020-03", "/page/document?pdf=ASU+2020-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-03%E2%80%94CODIFICATION%20IMPROVEMENTS"),
    ("2020-02", "/page/document?pdf=ASU+2020-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-02%E2%80%94FINANCIAL%20INSTRUMENTS"),
    ("2020-01", "/page/document?pdf=ASU+2020-01%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202020-01%E2%80%94INVESTMENTS"),
    # 2019
    ("2019-12", "/page/document?pdf=ASU+2019-12.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-12%E2%80%94INCOME%20TAXES"),
    ("2019-11", "/page/document?pdf=ASU+2019-11.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-11%E2%80%94CODIFICATION%20IMPROVEMENTS"),
    ("2019-10", "/page/document?pdf=ASU+2019-10.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-10%E2%80%94FINANCIAL%20INSTRUMENTS"),
    ("2019-09", "/page/document?pdf=ASU+2019-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-09%E2%80%94FINANCIAL%20SERVICES"),
    ("2019-08", "/page/document?pdf=ASU+2019-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-08%E2%80%94COMPENSATION"),
    ("2019-07", "/page/document?pdf=ASU+2019-07%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-07%E2%80%94CODIFICATION"),
    ("2019-06", "/page/document?pdf=ASU+2019-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-06%E2%80%94INTANGIBLES"),
    ("2019-05", "/page/document?pdf=ASU+2019-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-05%E2%80%94FINANCIAL%20INSTRUMENTS"),
    ("2019-04", "/page/document?pdf=ASU+2019-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-04%E2%80%94CODIFICATION%20IMPROVEMENTS"),
    ("2019-03", "/page/document?pdf=ASU+2019-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-03%E2%80%94NOT-FOR-PROFIT"),
    ("2019-02", "/page/document?pdf=ASU+2019-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-02%E2%80%94ENTERTAINMENT"),
    ("2019-01", "/page/document?pdf=ASU+2019-01%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202019-01%E2%80%94LEASES"),
    # 2018
    ("2018-20", "/page/document?pdf=ASU+2018-20%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-20%E2%80%94LEASES"),
    ("2018-19", "/page/document?pdf=ASU+2018-19.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-19%E2%80%94CODIFICATION"),
    ("2018-18", "/page/document?pdf=ASU+2018-18.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-18%E2%80%94COLLABORATIVE%20ARRANGEMENTS"),
    ("2018-17", "/page/document?pdf=ASU+2018-17.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-17%E2%80%94CONSOLIDATION"),
    ("2018-16", "/page/document?pdf=ASU+2018-16%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-16%E2%80%94DERIVATIVES"),
    ("2018-15", "/page/document?pdf=ASU+2018-15.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-15%E2%80%94INTANGIBLES"),
    ("2018-14", "/page/document?pdf=ASU+2018-14.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-14%E2%80%94COMPENSATION"),
    ("2018-13", "/page/document?pdf=ASU+2018-13.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-13%E2%80%94FAIR%20VALUE"),
    ("2018-12", "/page/document?pdf=ASU+2018-12.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-12%E2%80%94FINANCIAL%20SERVICES"),
    ("2018-11", "/page/document?pdf=ASU+2018-11.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-11%E2%80%94LEASES"),
    ("2018-10", "/page/document?pdf=ASU+2018-10%2c0.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-10%E2%80%94CODIFICATION"),
    ("2018-09", "/page/document?pdf=ASU+2018-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-09%E2%80%94CODIFICATION"),
    ("2018-08", "/page/document?pdf=ASU+2018-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-08%E2%80%94NOT-FOR-PROFIT"),
    ("2018-07", "/page/document?pdf=ASU+2018-07.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-07%E2%80%94COMPENSATION"),
    ("2018-06", "/page/document?pdf=ASU_2018-06-Codification_Improvements_to_Topic_942.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-06"),
    ("2018-05", "/page/document?pdf=ASU+2018-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-05%E2%80%94INCOME%20TAXES"),
    ("2018-04", "/page/document?pdf=ASU+2018-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-04%E2%80%94INVESTMENTS"),
    ("2018-03", "/page/document?pdf=ASU+2018-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-03%E2%80%94TECHNICAL%20CORRECTIONS"),
    ("2018-02", "/page/document?pdf=ASU+2018-02.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-02%E2%80%94INCOME%20TAXES"),
    ("2018-01", "/page/document?pdf=ASU+2018-01.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202018-01%E2%80%94LEASES"),
    # 2017
    ("2017-15", "/page/document?pdf=ASU+2017-15.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%20NO.%202017-15%E2%80%94CODIFICATION"),
    ("2017-14", "/page/document?pdf=ASU2017-14.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%20NO.%202017-14%E2%80%94INCOME%20TAXES"),
    ("2017-13", "/page/document?pdf=ASU+2017-13.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%20NO.%202017-13%E2%80%94REVENUE"),
    ("2017-12", "/page/document?pdf=ASU+2017-12.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%20NO.%202017-12%E2%80%94DERIVATIVES"),
    ("2017-11", "/page/document?pdf=ASU+2017-11.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%20NO.%202017-11%E2%80%94EARNINGS%20PER%20SHARE"),
    ("2017-10", "/page/document?pdf=ASU+2017-10.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-10%E2%80%94SERVICE%20CONCESSION"),
    ("2017-09", "/page/document?pdf=ASU+2017-09.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-09%E2%80%94COMPENSATION"),
    ("2017-08", "/page/document?pdf=ASU+2017-08.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-08%E2%80%94RECEIVABLES"),
    ("2017-07", "/page/document?pdf=ASU+2017-07.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-07%E2%80%94COMPENSATION"),
    ("2017-06", "/page/document?pdf=ASU+2017-06.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-06%E2%80%94PLAN%20ACCOUNTING"),
    ("2017-05", "/page/document?pdf=ASU+2017-05.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-05%E2%80%94OTHER%20INCOME"),
    ("2017-04", "/page/document?pdf=ASU2017-04.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-04%E2%80%94INTANGIBLES"),
    ("2017-03", "/page/document?pdf=ASU+2017-03.pdf&title=ACCOUNTING%20STANDARDS%20UPDATE%202017-03%E2%80%94ACCOUNTING%20CHANGES"),
    ("2017-02", "/page/document?pdf=ASU+2017-02.pdf&title=UPDATE%202017-02%E2%80%94NOT-FOR-PROFIT"),
    ("2017-01", "/page/document?pdf=ASU+2017-01.pdf&title=UPDATE%202017-01%E2%80%94BUSINESS%20COMBINATIONS"),
    # 2016
    ("2016-20", "/page/document?pdf=ASU+2016-20.pdf&title=UPDATE%202016-20%E2%80%94TECHNICAL%20CORRECTIONS"),
    ("2016-19", "/page/document?pdf=ASU+2016-19.pdf&title=UPDATE%202016-19%E2%80%94TECHNICAL%20CORRECTIONS"),
    ("2016-18", "/page/document?pdf=ASU+2016-18.pdf&title=UPDATE%202016-18%E2%80%94STATEMENT%20OF%20CASH%20FLOWS"),
    ("2016-17", "/page/document?pdf=ASU+2016-17.pdf&title=UPDATE%202016-17%E2%80%94CONSOLIDATION"),
    ("2016-16", "/page/document?pdf=ASU+2016-16.pdf&title=UPDATE%202016-16%E2%80%94INCOME%20TAXES"),
    ("2016-15", "/page/document?pdf=ASU+2016-15.pdf&title=UPDATE%202016-15%E2%80%94STATEMENT%20OF%20CASH%20FLOWS"),
    ("2016-14", "/page/document?pdf=ASU+2016-14.pdf&title=UPDATE%202016-14%E2%80%94NOT-FOR-PROFIT"),
    ("2016-13", "/page/document?pdf=ASU+2016-13.pdf&title=UPDATE%202016-13%E2%80%94FINANCIAL%20INSTRUMENTS%E2%80%94CREDIT%20LOSSES"),
    ("2016-12", "/page/document?pdf=ASU+2016-12.pdf&title=UPDATE-2016-12-REVENUE-FROM-CONTRACTS-WITH-CUSTOMERS"),
    ("2016-11", "/page/document?pdf=ASU+2016-11.pdf&title=UPDATE%202016-11%E2%80%94REVENUE%20RECOGNITION"),
    ("2016-10", "/page/document?pdf=ASU%202016-10.pdf&title=UPDATE-2016-10-REVENUE-FROM-CONTRACTS-WITH-CUSTOMERS"),
    ("2016-09", "/page/document?pdf=ASU+2016-09.pdf&title=UPDATE%202016-09%E2%80%94COMPENSATION%E2%80%94STOCK%20COMPENSATION"),
    ("2016-08", "/page/document?pdf=ASU%202016-08.pdf&title=UPDATE-2016-08-REVENUE-FROM-CONTRACTS-WITH-CUSTOMERS"),
    ("2016-07", "/page/document?pdf=ASU+2016-07.pdf&title=UPDATE%202016-07%E2%80%94INVESTMENTS%E2%80%94EQUITY%20METHOD"),
    ("2016-06", "/page/document?pdf=ASU+2016-06.pdf&title=UPDATE%202016-06%E2%80%94DERIVATIVES%20AND%20HEDGING"),
    ("2016-05", "/page/document?pdf=ASU+2016-05.pdf&title=UPDATE%202016-05%E2%80%94DERIVATIVES%20AND%20HEDGING"),
    ("2016-04", "/page/document?pdf=ASU+2016-04.pdf&title=UPDATE%202016-04%E2%80%94LIABILITIES%E2%80%94EXTINGUISHMENTS"),
    ("2016-03", "/page/document?pdf=ASU+2016-03.pdf&title=UPDATE%202016-03%E2%80%94INTANGIBLES%E2%80%94GOODWILL"),
    ("2016-02A", "/page/document?pdf=ASU+2016-02_Section+A.pdf&title=UPDATE%202016-02%E2%80%94LEASES"),
    ("2016-02B", "/page/document?pdf=ASU+2016-02_Section+B.pdf&title=UPDATE%202016-02%E2%80%94LEASES"),
    ("2016-02C", "/page/document?pdf=ASU+2016-02_Section+C.pdf&title=UPDATE%202016-02%E2%80%94LEASES"),
    ("2016-01", "/page/document?pdf=ASU+2016-01.pdf&title=UPDATE%202016-01%E2%80%94FINANCIAL%20INSTRUMENTS%E2%80%94OVERALL"),
    # 2015
    ("2015-17", "/page/document?pdf=ASU+2015-17.pdf&title=UPDATE%202015-17%E2%80%94INCOME%20TAXES"),
    ("2015-16", "/page/document?pdf=ASU+2015-16.pdf&title=UPDATE%202015-16%E2%80%94BUSINESS%20COMBINATIONS"),
    ("2015-15", "/page/document?pdf=ASU+2015-15.pdf&title=UPDATE%202015-15%E2%80%94INTEREST"),
    ("2015-14", "/page/document?pdf=ASU%202015-14.pdf&title=UPDATE-2015-14-REVENUE-FROM-CONTRACTS-WITH-CUSTOMERS"),
    ("2015-11", "/page/document?pdf=ASU+2015-11.pdf&title=UPDATE%202015-11%E2%80%94INVENTORY"),
    ("2015-07", "/page/document?pdf=ASU+2015-07_2.pdf&title=UPDATE%202015-07%E2%80%94FAIR%20VALUE%20MEASUREMENT"),
    ("2015-03", "/page/document?pdf=ASU+2015-03.pdf&title=UPDATE%20NO.%202015-03%E2%80%94INTEREST%E2%80%94IMPUTATION"),
    ("2015-02", "/page/document?pdf=ASU+2015-02.pdf&title=UPDATE%20NO.%202015-02%E2%80%94CONSOLIDATION"),
    ("2015-01", "/page/document?pdf=ASU+2015-01.pdf&title=UPDATE%20NO.%202015-01%E2%80%94INCOME%20STATEMENT"),
    # 2014 (key ones)
    ("2014-18", "/page/document?pdf=ASU+2014-18.pdf&title=UPDATE%20NO.%202014-18%E2%80%94BUSINESS%20COMBINATIONS"),
    ("2014-16", "/page/document?pdf=ASU+2014-16.pdf&title=UPDATE%20NO.%202014-16%E2%80%94DERIVATIVES%20AND%20HEDGING"),
    ("2014-15", "/page/document?pdf=ASU+2014-15.pdf&title=UPDATE%20NO.%202014-15%E2%80%94PRESENTATION%20OF%20FINANCIAL%20STATEMENTS"),
    ("2014-12", "/page/document?pdf=ASU+2014-12.pdf&title=UPDATE%20NO.%202014-12%E2%80%94COMPENSATION%E2%80%94STOCK"),
    ("2014-09A", "/page/document?pdf=ASU+2014-09_Section+A.pdf&title=UPDATE%20NO.%202014-09%E2%80%94REVENUE%20FROM%20CONTRACTS%20WITH%20CUSTOMERS"),
    ("2014-09BC", "/page/document?pdf=ASU+2014-09_Sections-B-and-C.pdf&title=UPDATE%20NO.%202014-09%E2%80%94REVENUE%20FROM%20CONTRACTS"),
    ("2014-09D", "/page/document?pdf=ASU+2014-09_Section+D.pdf&title=UPDATE%20NO.%202014-09%E2%80%94REVENUE%20FROM%20CONTRACTS"),
]


def decode_title(url_path):
    """Extract a readable title from the URL title parameter."""
    m = re.search(r'title=([^&]+)', url_path)
    if m:
        title = unquote(m.group(1))
        # Clean up em-dashes and formatting
        title = title.replace('\u2014', ' — ').replace('%E2%80%94', ' — ')
        return title
    return None


STORAGE_BASE = "https://storage.fasb.org/"

def _get_storage_filename(url_path):
    """Extract the PDF filename from the FASB URL path for storage.fasb.org."""
    m = re.search(r'pdf=([^&]+)', url_path)
    if not m:
        return None
    return unquote(m.group(1))


def download_pdfs(limit=None):
    """Download ASU PDFs from storage.fasb.org (no auth needed)."""
    import requests as req

    session = req.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,*/*',
    })

    catalog = ASU_CATALOG[:limit] if limit else ASU_CATALOG
    downloaded = []
    skipped = 0
    failed = 0

    log.info(f"Starting PDF download for {len(catalog)} ASUs from storage.fasb.org...")

    for asu_num, url_path in catalog:
        pdf_path = os.path.join(PDF_DIR, f"ASU_{asu_num}.pdf")
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 5000:
            skipped += 1
            continue

        filename = _get_storage_filename(url_path)
        if not filename:
            log.warning(f"  No filename for ASU {asu_num}")
            failed += 1
            continue

        storage_url = STORAGE_BASE + filename
        log.info(f"  ASU {asu_num}: {filename}")

        try:
            resp = session.get(storage_url, timeout=30)
            if resp.status_code == 200 and resp.content[:4] == b'%PDF':
                with open(pdf_path, 'wb') as f:
                    f.write(resp.content)
                log.info(f"    OK: {len(resp.content):,} bytes")
                downloaded.append(asu_num)
            else:
                log.warning(f"    Failed: status={resp.status_code}, size={len(resp.content)}")
                failed += 1
            time.sleep(0.5)  # Be polite
        except Exception as e:
            log.warning(f"    Error: {e}")
            failed += 1

    log.info(f"Downloaded {len(downloaded)}, skipped {skipped} existing, {failed} failed.")
    return downloaded


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using PyMuPDF."""
    import fitz  # pymupdf
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        log.warning(f"Failed to extract text from {pdf_path}: {e}")
        return ""


def parse_asu_sections(text, asu_num):
    """Parse an ASU's text into structured sections with ASC references."""
    sections = []

    # Extract the ASU title from the document
    title_match = re.search(
        r'Accounting Standards Update (?:No\. )?(\d{4}-\d{2})\s*[—\-\u2014]\s*(.+?)(?:\n|$)',
        text, re.IGNORECASE
    )
    asu_title = title_match.group(2).strip() if title_match else f"ASU {asu_num}"

    # Find ASC topic references (e.g., "Topic 606", "Subtopic 842-10")
    topic_refs = set(re.findall(r'(?:Topic|Subtopic)\s+(\d{3}(?:-\d{2})?)', text))

    # Extract the Summary section (most useful for layperson understanding)
    summary_match = re.search(
        r'(?:Summary|SUMMARY)\s*\n(.+?)(?=\n(?:Amendments|AMENDMENTS|Background|BACKGROUND|Objective|OBJECTIVE))',
        text, re.DOTALL
    )
    if summary_match:
        summary_text = re.sub(r'\s+', ' ', summary_match.group(1)).strip()
        if len(summary_text) > 100:
            sections.append({
                "type": "summary",
                "title": f"ASU {asu_num} Summary",
                "full_title": asu_title,
                "text": summary_text[:2000],
                "asc_topics": list(topic_refs),
            })

    # Extract paragraphs with ASC codification references
    # Pattern: ###-##-##-# (e.g., 606-10-25-1)
    asc_pattern = re.compile(
        r'(\d{3}-\d{2}-\d{2}-\d+(?:\s+through\s+\d{3}-\d{2}-\d{2}-\d+)?)'
    )

    # Find paragraph-level amendments
    for m in asc_pattern.finditer(text):
        asc_ref = m.group(1)
        # Get surrounding context (up to 500 chars after the reference)
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 500)
        context = text[start:end].strip()
        context = re.sub(r'\s+', ' ', context)

        if len(context) > 80:
            sections.append({
                "type": "paragraph",
                "asc_ref": asc_ref,
                "text": context[:600],
                "asc_topics": list(topic_refs),
            })

    # Extract "Background" or "Why" sections
    bg_match = re.search(
        r'(?:Background|BACKGROUND|Why Is the FASB Issuing This Update\?)\s*\n(.+?)(?=\n(?:Main Provisions|Who Is Affected|How Does|Amendments|AMENDMENTS))',
        text, re.DOTALL
    )
    if bg_match:
        bg_text = re.sub(r'\s+', ' ', bg_match.group(1)).strip()
        if len(bg_text) > 100:
            sections.append({
                "type": "background",
                "title": f"ASU {asu_num} Background",
                "text": bg_text[:2000],
                "asc_topics": list(topic_refs),
            })

    return {
        "asu_number": asu_num,
        "title": asu_title,
        "asc_topics": list(topic_refs),
        "sections": sections,
        "fasb_link": f"https://www.fasb.org/standards/accounting-standard-updates",
    }


def generate_layperson_entry(section, asu_data):
    """Convert an ASU section into a Vera knowledge entry with layperson language."""
    asu_num = asu_data["asu_number"]
    fasb_link = asu_data["fasb_link"]

    if section["type"] == "summary":
        # Truncate to fit knowledge base format
        text = section["text"]
        if len(text) > 450:
            text = text[:447] + "..."

        patterns = [f"asu {asu_num}"]
        # Add topic-level patterns
        for topic in section.get("asc_topics", [])[:3]:
            patterns.append(f"asc {topic}")
            patterns.append(f"topic {topic}")

        # Add keyword patterns from the title
        title_words = re.sub(r'[^\w\s]', '', section["full_title"].lower()).split()
        important_words = [w for w in title_words if len(w) >= 5 and w not in
                          {'topic', 'update', 'accounting', 'standards', 'subtopic'}]
        for w in important_words[:3]:
            if w not in patterns:
                patterns.append(w)

        response = (
            f"ASU {asu_num} — {section['full_title']}: {text}\n\n"
            f"📎 Official text: {fasb_link}"
        )
        if len(response) > 500:
            response = response[:497] + "..."

        return {
            "patterns": patterns[:6],
            "response": response,
            "action": None,
            "_source": "fasb_asu",
            "_asu": asu_num,
            "_date": date.today().isoformat(),
        }

    elif section["type"] == "paragraph" and "asc_ref" in section:
        asc_ref = section["asc_ref"]
        text = section["text"]
        if len(text) > 400:
            text = text[:397] + "..."

        patterns = [f"asc {asc_ref}", asc_ref]
        # Add the topic number
        topic_num = asc_ref.split('-')[0]
        if f"topic {topic_num}" not in patterns:
            patterns.append(f"topic {topic_num}")

        response = (
            f"ASC {asc_ref} (from ASU {asu_num}): {text}\n\n"
            f"📎 Official text: {fasb_link}"
        )
        if len(response) > 500:
            response = response[:497] + "..."

        return {
            "patterns": patterns[:6],
            "response": response,
            "action": None,
            "_source": "fasb_asu",
            "_asu": asu_num,
            "_asc_ref": asc_ref,
            "_date": date.today().isoformat(),
        }

    elif section["type"] == "background":
        text = section["text"]
        if len(text) > 450:
            text = text[:447] + "..."

        patterns = [f"asu {asu_num} background", f"why asu {asu_num}"]
        for topic in section.get("asc_topics", [])[:2]:
            patterns.append(f"asc {topic} changes")

        response = (
            f"Why ASU {asu_num} was issued: {text}\n\n"
            f"📎 Official text: {fasb_link}"
        )
        if len(response) > 500:
            response = response[:497] + "..."

        return {
            "patterns": patterns[:6],
            "response": response,
            "action": None,
            "_source": "fasb_asu",
            "_asu": asu_num,
            "_date": date.today().isoformat(),
        }

    return None


def process_all_pdfs():
    """Extract knowledge from all downloaded PDFs."""
    import glob
    pdf_files = sorted(glob.glob(os.path.join(PDF_DIR, "ASU_*.pdf")))
    log.info(f"Processing {len(pdf_files)} PDFs...")

    all_asu_data = []
    all_entries = []

    for pdf_path in pdf_files:
        asu_num = os.path.basename(pdf_path).replace("ASU_", "").replace(".pdf", "")
        log.info(f"  Parsing ASU {asu_num}...")

        text = extract_text_from_pdf(pdf_path)
        if not text or len(text) < 200:
            log.warning(f"    Skipped — insufficient text extracted")
            continue

        asu_data = parse_asu_sections(text, asu_num)
        all_asu_data.append(asu_data)

        entries_for_asu = 0
        for section in asu_data["sections"]:
            entry = generate_layperson_entry(section, asu_data)
            if entry:
                all_entries.append(entry)
                entries_for_asu += 1

        log.info(f"    {entries_for_asu} entries from {len(asu_data['sections'])} sections")

    # Save ASU index
    with open(ASU_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_asu_data, f, indent=2, ensure_ascii=False)
    log.info(f"Saved ASU index: {len(all_asu_data)} ASUs -> {ASU_INDEX_FILE}")

    # Deduplicate entries (by ASC ref or ASU pattern)
    seen = set()
    unique_entries = []
    for entry in all_entries:
        key = entry["patterns"][0]
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    # Save ASU knowledge
    with open(ASU_KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(unique_entries, f, indent=2, ensure_ascii=False)
    log.info(f"Saved {len(unique_entries)} unique ASU knowledge entries -> {ASU_KNOWLEDGE_FILE}")

    return unique_entries


def main():
    limit = None
    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        limit = int(sys.argv[idx + 1])

    log.info("=" * 60)
    log.info("FASB ASU Downloader & Knowledge Extractor")
    log.info("=" * 60)

    # Step 1: Download PDFs
    downloaded = download_pdfs(limit=limit)

    # Step 2: Extract and process
    entries = process_all_pdfs()

    log.info(f"\nDone. {len(entries)} ASU knowledge entries ready.")
    log.info(f"  PDFs: {PDF_DIR}")
    log.info(f"  Knowledge: {ASU_KNOWLEDGE_FILE}")
    log.info(f"  Index: {ASU_INDEX_FILE}")


if __name__ == '__main__':
    main()
