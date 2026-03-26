"""
Vera Knowledge Gatherer — Aggressive daily automated script
Fetches accounting, GAAP, ASC, and finance knowledge from reputable public sources,
extracts MULTIPLE entries per page (section-by-section), deduplicates, and appends.

Goal: Match the completeness of the ASC Codification and authoritative finance sources.
Auto-slows to weekly once saturated.

Sources (ALL hit every run):
  - Wikipedia (ASC topics, GAAP, finance, tax — ~80 URLs)
  - AccountingTools (accounting mechanics — ~50 URLs)
  - Corporate Finance Institute (finance & valuation — ~40 URLs)
  - IRS.gov (tax compliance — ~20 URLs)

Scheduled: Daily at 9:15 AM via Windows Task Scheduler
"""

import json
import os
import re
import sys
import logging
from datetime import datetime, date
from difflib import SequenceMatcher
from hashlib import md5

import requests
from bs4 import BeautifulSoup

# ── Paths ──
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
KNOWLEDGE_FILE = os.path.join(DATA_DIR, 'vera-knowledge.json')
SCHEDULE_FILE = os.path.join(ROOT, 'scripts', 'source_schedule.json')
LOG_DIR = os.path.join(ROOT, 'scripts', 'logs')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ── Logging ──
log_file = os.path.join(LOG_DIR, f'gatherer_{date.today().isoformat()}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('vera_gatherer')

# ── HTTP Session ──
SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
})
TIMEOUT = 20


# ═══════════════════════════════════════════════════════════════════
# SOURCE DEFINITIONS — comprehensive coverage
# ═══════════════════════════════════════════════════════════════════

_AT = "https://www.accountingtools.com/articles/"
_WK = "https://en.wikipedia.org/wiki/"
_CFI = "https://corporatefinanceinstitute.com/resources/"
_IRS = "https://www.irs.gov/"

SOURCES = [
    # ── Wikipedia: ASC Codification Topics ──
    {
        "name": "wikipedia_asc_codification",
        "urls": [
            _WK + s for s in [
                "Accounting_Standards_Codification",
                "Financial_Accounting_Standards_Board",
                "Generally_accepted_accounting_principles_(United_States)",
                # ASC 205-260: Presentation
                "Financial_statement", "Income_statement", "Balance_sheet",
                "Cash_flow_statement", "Statement_of_changes_in_equity",
                "Earnings_per_share", "Comprehensive_income",
                "Discontinued_operations", "Interim_financial_reporting",
                # ASC 310-360: Assets
                "Accounts_receivable", "Loan", "Investment",
                "Inventory", "Inventory_valuation",
                "Fixed_asset", "Property,_plant,_and_equipment",
                "Depreciation", "Asset_impairment",
                # ASC 350: Intangibles & Goodwill
                "Intangible_asset", "Goodwill_(accounting)",
                "Amortization_(business)", "Research_and_development",
                # ASC 405-480: Liabilities
                "Liability_(financial_accounting)", "Accounts_payable",
                "Contingent_liability", "Asset_retirement_obligation",
                "Debt", "Bond_(finance)", "Convertible_bond",
                "Preferred_stock", "Mezzanine_capital",
                # ASC 505-520: Equity
                "Stockholders%27_equity", "Treasury_stock",
                "Stock_split", "Dividend", "Retained_earnings",
                # ASC 606: Revenue
                "Revenue_recognition", "Revenue", "Contract",
                "Percentage-of-completion_method", "Deferred_revenue",
                # ASC 710-718: Compensation
                "Employee_stock_option", "Stock_option",
                "Restricted_stock", "Employee_benefits",
                "Pension", "Defined_benefit_pension_plan",
                "Defined_contribution_plan", "Postretirement_benefits",
                # ASC 740: Income Taxes
                "Deferred_tax", "Income_tax_in_the_United_States",
                "Tax_deduction", "Tax_credit",
                "Net_operating_loss", "Valuation_allowance",
                # ASC 805-810: Business Combinations & Consolidation
                "Business_combination", "Mergers_and_acquisitions",
                "Consolidated_financial_statement",
                "Variable_interest_entity", "Minority_interest",
                # ASC 815-825: Financial Instruments
                "Derivative_(finance)", "Hedge_(finance)",
                "Fair_value", "Financial_instrument",
                "Interest_rate_swap", "Option_(finance)", "Futures_contract",
                # ASC 820: Fair Value
                "Fair_value_accounting", "Mark-to-market_accounting",
                # ASC 830-835: Foreign Currency & Interest
                "Foreign_currency_translation", "Foreign_exchange_risk",
                "Interest", "Capitalization_of_interest",
                # ASC 840-842: Leases
                "Lease", "Lease_accounting", "Operating_lease", "Finance_lease",
                # ASC 845-860: Other
                "Barter", "Transfer_pricing",
                "Securitization", "Factoring_(finance)",
                # ASC 855-860: Subsequent Events
                "Subsequent_event",
                # ASC 326: Credit Losses (CECL)
                "Expected_credit_loss",
                # Audit & Controls
                "Auditing", "Internal_audit", "External_auditor",
                "Internal_control", "Sarbanes%E2%80%93Oxley_Act",
                "Segregation_of_duties", "Materiality_(auditing)",
                # ASC 230: Cash Flows (deep)
                "Operating_cash_flow", "Cash_flow_forecasting",
                # ASC 250: Accounting Changes & Error Corrections
                "Accounting_methods", "Prior_period_adjustment",
                "Change_in_accounting_estimate",
                # ASC 270-280: Segment Reporting
                "Segment_reporting", "Operating_segment",
                # ASC 320-325: Investments
                "Held-to-maturity_security", "Available-for-sale_security",
                "Trading_security", "Equity_method",
                "Cost_method_(investments)", "Marketable_security",
                # ASC 330: Inventory (deep)
                "FIFO_and_LIFO_accounting", "Weighted_average_cost",
                "Specific_identification_(inventories)",
                "Lower_of_cost_or_market", "Inventory_turnover",
                "Just-in-time_manufacturing", "Economic_order_quantity",
                # ASC 340: Deferred Costs
                "Deferred_cost", "Prepaid_expense",
                # ASC 360: PP&E (deep)
                "Useful_life", "Salvage_value",
                "Straight-line_depreciation", "Declining-balance_method",
                "Sum-of-years-digits_method", "Units-of-production_depreciation",
                "Capital_expenditure", "Revenue_expenditure",
                "Capitalization_(accounting)",
                # ASC 410-420: Exit/Disposal & ARO
                "Restructuring", "Exit_strategy",
                # ASC 440-460: Commitments & Guarantees
                "Commitment_(accounting)", "Guarantee",
                "Letter_of_credit", "Surety_bond",
                # ASC 470: Debt (deep)
                "Term_loan", "Revolving_credit",
                "Subordinated_debt", "Senior_debt",
                "Debt_covenant", "Amortizing_loan",
                "Zero-coupon_bond", "Callable_bond", "Junk_bond",
                # ASC 480: Distinguishing Liabilities from Equity
                "Redeemable_preferred_stock", "Warrant_(finance)",
                # ASC 606: Revenue (deep)
                "Bill-and-hold", "Consignment",
                "Franchise_disclosure_document", "Royalty_payment",
                "Subscription_business_model", "License",
                # ASC 715: Pensions (deep)
                "Pension_fund", "Actuarial_science",
                "Projected_benefit_obligation", "Pension_plan",
                "401(k)", "Individual_retirement_account",
                # ASC 718: Stock Comp (deep)
                "Employee_stock_purchase_plan", "Stock_appreciation_right",
                "Phantom_stock", "Vesting",
                "Black%E2%80%93Scholes_model",
                # ASC 740: Income Taxes (deep)
                "Temporary_difference", "Permanent_difference",
                "Effective_tax_rate", "Statutory_tax_rate",
                "Tax_provision", "Uncertain_tax_position",
                # ASC 815: Derivatives & Hedging (deep)
                "Forward_contract", "Swap_(finance)",
                "Credit_default_swap", "Currency_swap",
                "Collar_(finance)", "Straddle",
                "Put_option", "Call_option",
                "Notional_amount", "Mark-to-market_accounting",
                # ASC 820: Fair Value (deep)
                "Level_1,_2,_and_3_assets",
                "Observable_input", "Unobservable_input",
                # ASC 842: Leases (deep)
                "Sale_and_leaseback", "Sublease",
                "Right-of-use_asset", "Lease_liability",
                # ASC 850: Related Party Transactions
                "Related_party_transaction", "Transfer_pricing",
                # ASC 855: Subsequent Events (deep)
                "Going_concern",
                # Accounting Principles & Frameworks
                "Accrual_accounting", "Cash_method_of_accounting",
                "Revenue_recognition_principle", "Matching_principle",
                "Historical_cost", "Conservatism_(accounting)",
                "Full_disclosure_principle", "Consistency_principle",
                "Monetary_unit_assumption", "Economic_entity_assumption",
                "Going_concern_principle", "Periodicity_assumption",
                # Financial Statement Analysis
                "Horizontal_analysis", "Vertical_analysis",
                "Trend_analysis", "Common_size_financial_statement",
                "Ratio_analysis",
                # Accounting Information Systems
                "Accounting_information_system", "Enterprise_resource_planning",
                "Chart_of_accounts", "General_journal",
                "Special_journal", "Subsidiary_ledger",
                # Government & Nonprofit Accounting
                "Governmental_accounting", "Fund_accounting",
                "Governmental_Accounting_Standards_Board",
                "Nonprofit_organization", "Form_990",
                # International
                "International_Financial_Reporting_Standards",
                "IFRS_and_US_GAAP_convergence",
                # Managerial & Cost Accounting
                "Management_accounting", "Cost_accounting",
                "Activity-based_costing", "Job_costing", "Process_costing",
                "Standard_cost_accounting", "Throughput_accounting",
                "Target_costing", "Kaizen_costing", "Life-cycle_cost_analysis",
                "Variance_analysis_(accounting)", "Budget_variance",
                "Cost_allocation", "Overhead_(business)", "Cost_driver",
                "Cost_center", "Profit_center", "Responsibility_accounting",
                "Transfer_pricing", "Absorption_costing", "Variable_costing",
                "Contribution_margin", "Break-even_(economics)",
                "Cost%E2%80%93volume%E2%80%93profit_analysis",
                "Marginal_cost", "Opportunity_cost", "Sunk_cost",
                # Bookkeeping & Accounting Cycle
                "Bookkeeping", "Double-entry_bookkeeping",
                "Single-entry_bookkeeping", "Accounting_cycle",
                "Trial_balance", "Adjusting_entries", "Closing_entry",
                "Post-closing_trial_balance", "Worksheet_(accounting)",
                "Journal_entry", "Ledger", "T-account",
                "Debits_and_credits", "Accrual", "Deferral",
                # Specific Account Types
                "Unearned_revenue", "Accrued_expense", "Accrued_interest",
                "Provision_(accounting)", "Reserve_(accounting)",
                "Allowance_for_doubtful_accounts", "Bad_debt",
                "Write-off", "Write-down",
                "Capital_surplus", "Additional_paid-in_capital",
                "Par_value", "Book_value", "Carrying_value",
                # Consolidation & Combinations Deep
                "Acquisition_accounting", "Pooling-of-interests_method",
                "Purchase_price_allocation", "Bargain_purchase",
                "Non-controlling_interest", "Equity_method",
                "Proportionate_consolidation",
                # Revenue & Expenses Deep
                "Cost_of_goods_sold", "Gross_profit", "Operating_expense",
                "Selling,_general_and_administrative_expenses",
                "Extraordinary_item", "Other_comprehensive_income",
                "Unrealized_gain", "Realized_gain",
                # SEC & Regulatory
                "U.S._Securities_and_Exchange_Commission",
                "Securities_Act_of_1933", "Securities_Exchange_Act_of_1934",
                "Form_10-K", "Form_10-Q", "Form_8-K",
                "Annual_report", "Proxy_statement",
                "Public_Company_Accounting_Oversight_Board",
                "American_Institute_of_Certified_Public_Accountants",
                # Fraud & Ethics
                "Accounting_fraud", "Creative_accounting",
                "Earnings_management", "Window_dressing_(accounting)",
                "Forensic_accounting", "Benford%27s_law",
                "Enron_scandal", "WorldCom_scandal",
                # Specialized Industries
                "Bank_accounting", "Insurance_accounting",
                "Construction_accounting", "Oil_and_gas_accounting",
                "Real_estate_accounting", "Healthcare_accounting",
                "Retail_accounting", "Agriculture_accounting",
                # Sustainability & ESG
                "Environmental,_social,_and_corporate_governance",
                "Sustainability_accounting", "Carbon_accounting",
                "Integrated_reporting", "Triple_bottom_line",
                # Accounting Theory & History
                "Accounting_theory", "Positive_accounting_theory",
                "Agency_theory", "Stewardship_theory",
                "Conceptual_framework_(financial_reporting)",
                "Accounting_equation", "Matching_principle",
                "Realization_(accounting)", "Recognition_(accounting)",
                "Measurement_basis_(accounting)",
                "Historical_cost_accounting", "Current_cost_accounting",
                "Fair_value_measurement",
                # More ASC Subtopics
                "Compensating_balance", "Restricted_cash",
                "Cash_and_cash_equivalents", "Short-term_investment",
                "Note_receivable", "Note_payable",
                "Mortgage_loan", "Line_of_credit",
                "Commercial_paper", "Repurchase_agreement",
                "Factoring_(finance)", "Assignment_(law)",
                # Depreciation & Amortization Deep
                "Accumulated_depreciation", "Depletion_(accounting)",
                "Amortization_(tax_law)", "Section_197_intangible",
                "Bonus_depreciation", "Modified_Accelerated_Cost_Recovery_System",
                # More Financial Instruments
                "Embedded_derivative", "Bifurcation_(finance)",
                "Beneficial_conversion_feature",
                "Debt_issuance_cost", "Original_issue_discount",
                "Debt_modification", "Debt_extinguishment",
                "Troubled_debt_restructuring",
                # Share-Based Payment Deep
                "Intrinsic_value_(finance)", "Time_value_(finance)",
                "Exercise_price", "Grant_date",
                "Measurement_date", "Service_period",
                "Performance_condition", "Market_condition",
                "Modification_(stock_options)",
                # Lease Accounting Deep
                "Incremental_borrowing_rate", "Lease_term",
                "Variable_lease_payment", "Residual_value_guarantee",
                "Lease_incentive", "Initial_direct_cost",
                # Business Combinations Deep
                "Contingent_consideration", "Measurement_period_(acquisitions)",
                "In-process_research_and_development",
                "Customer_relationship_(intangible)",
                "Assembled_workforce", "Non-compete_agreement",
                # More Specialized
                "Earnings_quality", "Accruals_anomaly",
                "Cash_flow_quality", "Revenue_quality",
                "Accounting_conservatism", "Big_bath_(accounting)",
                "Cookie_jar_reserves", "Channel_stuffing",
                "Round-tripping_(finance)", "Bill-and-hold",
                # Banking & Financial Services Accounting
                "Loan_loss_provision", "Non-performing_loan",
                "Loan_origination", "Mortgage_servicing",
                "Deposit_(finance)", "Certificate_of_deposit",
                "Letters_of_credit", "Standby_letter_of_credit",
                "Bank_capital", "Basel_III", "Tier_1_capital",
                "Risk-weighted_asset", "Capital_adequacy_ratio",
                # Payroll & HR Accounting
                "Payroll", "Payroll_tax", "Gross_income",
                "Net_income", "Withholding_tax", "Pay_stub",
                "Overtime", "Minimum_wage", "Fair_Labor_Standards_Act",
                "Workers%27_compensation", "Unemployment_benefits",
                "Severance_package", "Golden_handshake",
                "Employee_stock_ownership_plan", "Profit_sharing",
                "Deferred_compensation", "Nonqualified_deferred_compensation",
                "Cafeteria_plan", "Flexible_spending_account",
                "Health_savings_account", "Health_Reimbursement_Arrangement",
                # Internal Controls & SOX Deep
                "COSO", "Committee_of_Sponsoring_Organizations_of_the_Treadway_Commission",
                "Enterprise_risk_management", "Control_environment",
                "Risk_assessment", "Control_activities",
                "Information_and_communication_(COSO)",
                "Monitoring_(internal_control)",
                "Internal_control_over_financial_reporting",
                "Material_weakness", "Significant_deficiency",
                "Audit_committee", "Whistleblower",
                # Audit Deep
                "Financial_audit", "Operational_audit", "Compliance_audit",
                "Information_technology_audit", "Forensic_audit",
                "Audit_evidence", "Audit_risk", "Inherent_risk",
                "Control_risk", "Detection_risk",
                "Audit_sampling", "Substantive_procedure",
                "Analytical_procedure", "Confirmation_(accounting)",
                "Audit_report", "Qualified_opinion", "Adverse_opinion",
                "Disclaimer_of_opinion", "Emphasis_of_matter",
                "Going_concern_opinion", "Management_representation_letter",
                "Engagement_letter", "Audit_planning",
                # Governmental Accounting Deep
                "Government_Accountability_Office",
                "Single_Audit", "OMB_Uniform_Guidance",
                "Modified_accrual_accounting", "Full_accrual_accounting",
                "General_fund", "Special_revenue_fund",
                "Capital_projects_fund", "Debt_service_fund",
                "Enterprise_fund_(government)", "Internal_service_fund",
                "Fiduciary_fund", "Pension_trust_fund",
                "Government-wide_financial_statements",
                "Comprehensive_annual_financial_report",
                # Nonprofit Deep
                "Statement_of_financial_position_(nonprofit)",
                "Statement_of_activities_(nonprofit)",
                "Statement_of_functional_expenses",
                "Donor_restriction", "Net_assets_without_donor_restrictions",
                "Net_assets_with_donor_restrictions",
                "In-kind_donation", "Pledge_(law)",
                "Conditional_vs_unconditional_promise",
                "Endowment", "Spending_policy",
                # International Accounting Standards
                "IAS_1", "IAS_2", "IAS_7", "IAS_8",
                "IAS_10", "IAS_12", "IAS_16", "IAS_17",
                "IAS_18", "IAS_19", "IAS_21", "IAS_23",
                "IAS_24", "IAS_27", "IAS_28", "IAS_32",
                "IAS_33", "IAS_36", "IAS_37", "IAS_38",
                "IAS_39", "IAS_40", "IAS_41",
                "IFRS_1", "IFRS_2", "IFRS_3", "IFRS_5",
                "IFRS_7", "IFRS_9", "IFRS_10", "IFRS_11",
                "IFRS_12", "IFRS_13", "IFRS_15", "IFRS_16",
                # More Specialized Industry
                "Software_capitalization", "Cloud_computing_(accounting)",
                "Subscription_economy", "Software_as_a_service",
                "Platform_as_a_service",
                "Cryptocurrency_accounting",
                "Digital_asset", "Non-fungible_token",
                "Revenue_recognition_for_software",
                "Construction_accounting", "Percentage_of_completion",
                "Completed_contract_method",
                "Long-term_contract", "Retainage",
                "Oil_and_gas_accounting",
                "Full_cost_method", "Successful_efforts_method",
                "Depletion_(oil_and_gas)", "Proved_reserves",
            ]
        ],
    },
    # ── Wikipedia: Finance & Valuation ──
    {
        "name": "wikipedia_finance",
        "urls": [
            _WK + s for s in [
                "Net_present_value", "Internal_rate_of_return",
                "Weighted_average_cost_of_capital", "Capital_asset_pricing_model",
                "Discounted_cash_flow", "Free_cash_flow",
                "Enterprise_value", "Market_capitalization",
                "Price%E2%80%93earnings_ratio", "Price-to-book_ratio",
                "Dividend_yield", "Return_on_equity", "Return_on_assets",
                "Earnings_before_interest,_taxes,_depreciation_and_amortization",
                "Economic_value_added", "Residual_income_valuation",
                "Beta_(finance)", "Systematic_risk", "Unsystematic_risk",
                "Sharpe_ratio", "Treynor_ratio", "Jensen%27s_alpha",
                "Efficient-market_hypothesis", "Modern_portfolio_theory",
                "Capital_structure", "Modigliani%E2%80%93Miller_theorem",
                "Leverage_(finance)", "Debt-to-equity_ratio",
                "Current_ratio", "Quick_ratio", "Cash_ratio",
                "Working_capital", "Cash_conversion_cycle",
                "Compound_interest", "Time_value_of_money", "Annuity",
                "Perpetuity", "Bond_valuation", "Yield_to_maturity",
                "Duration_(finance)", "Convexity_(finance)",
                "Cost_of_equity", "Cost_of_debt", "Hurdle_rate",
                "Payback_period", "Profitability_index",
                "Mergers_and_acquisitions", "Leveraged_buyout",
                "Initial_public_offering", "Venture_capital",
                "Private_equity", "Corporate_governance",
                "Bankruptcy", "Chapter_11,_Title_11,_United_States_Code",
                "Financial_ratio", "DuPont_analysis",
                "Altman_Z-score", "Operating_leverage",
                # Banking & Financial Institutions
                "Commercial_bank", "Investment_banking", "Central_bank",
                "Federal_Reserve", "Fractional-reserve_banking",
                "Money_market", "Capital_market", "Securities_market",
                "Stock_exchange", "Bond_market", "Foreign_exchange_market",
                # Risk Management
                "Financial_risk_management", "Credit_risk", "Market_risk",
                "Liquidity_risk", "Operational_risk", "Interest_rate_risk",
                "Value_at_risk", "Stress_testing_(financial)",
                "Risk-adjusted_return_on_capital",
                # Corporate Finance Deep
                "Dividend_policy", "Share_repurchase", "Rights_issue",
                "Secondary_offering", "Underwriting",
                "Due_diligence", "Earnout", "Letter_of_intent",
                "Poison_pill_(finance)", "Golden_parachute",
                "Corporate_finance", "Agency_cost", "Pecking_order_theory",
                "Trade-off_theory_of_capital_structure",
                # Financial Planning & Analysis
                "Financial_planning_(business)", "Budget",
                "Forecasting", "Scenario_analysis", "Sensitivity_analysis",
                "Monte_Carlo_methods_in_finance",
                # Fixed Income Deep
                "Yield_curve", "Term_structure_of_interest_rates",
                "Credit_rating", "Bond_credit_rating",
                "Municipal_bond", "Government_bond", "Corporate_bond",
                "Mortgage-backed_security", "Collateralized_debt_obligation",
                "Credit_spread_(bond)", "Coupon_(bond)",
                # Equity Markets
                "Stock_valuation", "Fundamental_analysis", "Technical_analysis",
                "Equity_research", "Market_maker", "Short_selling",
                "Margin_(finance)", "Stock_market_index",
                # Derivatives Deep
                "Options_strategy", "Binomial_options_pricing_model",
                "Greeks_(finance)", "Implied_volatility",
                "Volatility_smile", "Risk-neutral_measure",
                # Real Estate Finance
                "Real_estate_investment_trust", "Mortgage",
                "Amortization_schedule", "Loan-to-value_ratio",
                "Capitalization_rate", "Cash-on-cash_return",
                # Behavioral Finance
                "Behavioral_economics", "Prospect_theory",
                "Confirmation_bias", "Anchoring_(cognitive_bias)",
                "Herd_behavior", "Market_bubble",
                # International Finance
                "Exchange_rate", "Purchasing_power_parity",
                "Interest_rate_parity", "Balance_of_payments",
                "Foreign_direct_investment", "Currency_risk",
                # Insurance & Pensions
                "Actuarial_science", "Life_insurance", "Annuity_(finance_theory)",
                "Endowment_policy", "Reinsurance", "Underwriting",
                "Insurance_premium", "Deductible",
                # Asset Classes & Alternatives
                "Alternative_investment", "Hedge_fund", "Mutual_fund",
                "Index_fund", "Exchange-traded_fund",
                "Money_market_fund", "Sovereign_wealth_fund",
                "Commodity_market", "Gold_as_an_investment",
                "Cryptocurrency", "Bitcoin", "Blockchain",
                # Quantitative Finance
                "Quantitative_finance", "Financial_engineering",
                "Algorithmic_trading", "High-frequency_trading",
                "Black%E2%80%93Scholes_model", "Stochastic_calculus",
                "Brownian_motion", "Ito%27s_lemma",
                # Personal Finance (relevant to advisory)
                "Personal_finance", "Financial_planning",
                "Asset_allocation", "Diversification_(finance)",
                "Retirement_planning", "Estate_planning",
                "Trust_law", "Fiduciary", "Wealth_management",
                "Tax-advantaged", "Tax-deferred",
                # Economics Foundations
                "Inflation", "Deflation", "Gross_domestic_product",
                "Monetary_policy", "Fiscal_policy",
                "Supply_and_demand", "Elasticity_(economics)",
                "Business_cycle", "Recession", "Economic_growth",
                "Unemployment", "Consumer_price_index",
                "Federal_funds_rate", "Prime_rate",
                "Quantitative_easing", "Money_supply",
                # Fintech & Modern Finance
                "Financial_technology", "Peer-to-peer_lending",
                "Crowdfunding", "Digital_currency",
                "Payment_system", "Mobile_payment",
                "Open_banking", "Neobank",
                "Decentralized_finance", "Smart_contract",
                # Corporate Restructuring & Distress
                "Restructuring", "Turnaround_management",
                "Distressed_securities", "Debtor-in-possession_financing",
                "Chapter_7,_Title_11,_United_States_Code",
                "Liquidation", "Voluntary_administration",
                "Creditor", "Secured_creditor", "Unsecured_debt",
                "Priority_of_claims", "Automatic_stay",
                "Fraudulent_conveyance", "Preference_(insolvency)",
                # Mergers & Acquisitions Deep
                "Takeover", "Hostile_takeover", "Tender_offer",
                "Merger_of_equals", "Reverse_merger",
                "Spin-off_(corporate)", "Carve-out",
                "Divestiture", "Management_buyout",
                "Strategic_buyer", "Financial_buyer",
                "Synergy", "Accretion/dilution_analysis",
                # Private Markets
                "Venture_capital_financing", "Series_A_round",
                "Angel_investor", "Seed_money",
                "Mezzanine_financing", "Bridge_loan",
                "Term_sheet", "Cap_table",
                "Pre-money_valuation", "Post-money_valuation",
                "Liquidation_preference", "Anti-dilution_provision",
                "Drag-along_right", "Tag-along_right",
                # Treasury & Cash Management
                "Treasury_management", "Cash_management",
                "Cash_pooling", "Netting", "Cash_concentration",
                "Bank_account_management", "Payment_processing",
                "Lockbox_(banking)", "Sweep_account",
                "Money_market_account", "Repurchase_agreement",
                # Financial Regulation
                "Dodd%E2%80%93Frank_Wall_Street_Reform_and_Consumer_Protection_Act",
                "Glass%E2%80%93Steagall_legislation",
                "Basel_Accords", "MiFID_II",
                "Know_your_customer", "Anti-money_laundering",
                "Bank_Secrecy_Act", "Foreign_Account_Tax_Compliance_Act",
                # Project Finance & Infrastructure
                "Project_finance", "Public%E2%80%93private_partnership",
                "Build%E2%80%93operate%E2%80%93transfer",
                "Special-purpose_entity", "Ring-fencing_(finance)",
                "Infrastructure_fund",
                # Trade Finance
                "Trade_finance", "Documentary_collection",
                "Bill_of_exchange", "Promissory_note",
                "Banker%27s_acceptance", "Forfaiting",
                "Export_credit_agency", "Trade_credit",
                # Wealth & Asset Management
                "Asset_management", "Portfolio_management",
                "Active_management", "Passive_management",
                "Index_investing", "Value_investing",
                "Growth_investing", "Momentum_investing",
                "Contrarian_investing", "Income_investing",
                "Dollar-cost_averaging", "Rebalancing_investments",
                "Asset_class", "Correlation_(finance)",
                "Modern_portfolio_theory", "Efficient_frontier",
                "Capital_allocation_line", "Security_market_line",
                "Arbitrage_pricing_theory", "Fama%E2%80%93French_three-factor_model",
                # Commodities & Real Assets
                "Commodity", "Futures_exchange", "Spot_contract",
                "Contango", "Backwardation", "Commodity_trading_advisor",
                "Precious_metal", "Base_metal",
                "Energy_trading", "Emissions_trading",
                "Carbon_credit", "Renewable_energy_certificate",
                # Structured Finance
                "Structured_finance", "Asset-backed_security",
                "Collateralized_loan_obligation",
                "Credit_enhancement", "Tranching",
                "Waterfall_(finance)", "Special-purpose_vehicle",
                "Covered_bond", "Whole_loan",
                # Corporate Governance & Ethics
                "Board_of_directors", "Independent_director",
                "Executive_compensation", "Say_on_pay",
                "Shareholder_activism", "Proxy_fight",
                "Staggered_board_of_directors", "Poison_pill_(finance)",
                "White_knight_(business)", "Crown_jewel_defense",
                "Greenmail", "Pac-Man_defense",
                # Financial Crises & History
                "Financial_crisis_of_2007%E2%80%932008",
                "Dot-com_bubble", "Black_Monday_(1987)",
                "Asian_financial_crisis", "European_debt_crisis",
                "Savings_and_loan_crisis", "Long-Term_Capital_Management",
                "Too_big_to_fail", "Systemic_risk",
                "Moral_hazard", "Adverse_selection",
                "Bank_run", "Contagion_(finance)",
            ]
        ],
    },
    # ── Wikipedia: Tax ──
    {
        "name": "wikipedia_tax",
        "urls": [
            _WK + s for s in [
                "Income_tax_in_the_United_States",
                "Corporate_tax_in_the_United_States",
                "Capital_gains_tax_in_the_United_States",
                "Payroll_tax", "Self-employment_tax",
                "Sales_tax", "Value-added_tax",
                "Estate_tax_in_the_United_States",
                "Alternative_minimum_tax",
                "Tax_deduction", "Itemized_deduction",
                "Standard_deduction", "Tax_credit",
                "Earned_income_tax_credit",
                "Depreciation_(tax)", "Section_179_depreciation_deduction",
                "MACRS", "Bonus_depreciation",
                "S_corporation", "C_corporation",
                "Limited_liability_company",
                "Partnership_taxation_in_the_United_States",
                "Sole_proprietorship", "Pass-through_entity",
                "Form_W-2", "Form_1099", "Form_1040",
                "Quarterly_estimated_tax",
                # Tax Deep Dive
                "Tax_bracket", "Marginal_tax_rate", "Progressive_tax",
                "Regressive_tax", "Flat_tax", "Tax_incidence",
                "Double_taxation", "Tax_treaty", "Tax_haven",
                "Transfer_pricing", "Tax_avoidance", "Tax_evasion",
                # Business Tax Topics
                "Qualified_business_income_deduction",
                "Like-kind_exchange", "Installment_sale",
                "Passive_activity_loss_rules", "At-risk_rules",
                "Net_investment_income_tax", "Accumulated_earnings_tax",
                "Personal_holding_company", "Constructive_receipt",
                # Retirement & Benefits Tax
                "Traditional_IRA", "Roth_IRA", "SEP-IRA",
                "Solo_401(k)", "Health_savings_account",
                "Flexible_spending_account", "Cafeteria_plan",
                # Property & Wealth Tax
                "Property_tax_in_the_United_States",
                "Gift_tax_in_the_United_States",
                "Generation-skipping_transfer_tax",
                "Step-up_in_basis", "Cost_basis",
                # International Tax
                "Controlled_foreign_corporation",
                "Subpart_F_income", "Global_intangible_low-taxed_income",
                "Foreign_tax_credit", "Tax_Cuts_and_Jobs_Act_of_2017",
                # State & Local Tax
                "State_income_tax", "Sales_taxes_in_the_United_States",
                "Use_tax", "Nexus_(tax)", "Multistate_Tax_Commission",
                "Franchise_tax", "Excise_tax_in_the_United_States",
                # Tax Accounting Methods
                "Cash_method_of_accounting", "Accrual_method_of_accounting",
                "Completed-contract_method", "Percentage-of-completion_method",
                "Installment_sales_method", "Cost_recovery_method",
                # Tax Planning & Structures
                "Tax_planning", "Tax_shelter", "Charitable_remainder_trust",
                "Grantor_retained_annuity_trust", "Family_limited_partnership",
                "Qualified_opportunity_zone", "1031_exchange",
                "Wash_sale", "Constructive_sale",
                # Employment & Payroll Tax Deep
                "Federal_Insurance_Contributions_Act",
                "Federal_Unemployment_Tax_Act",
                "Worker_classification", "Independent_contractor",
                "Employee_misclassification", "Statutory_employee",
                # Exempt Organizations
                "501(c)(3)_organization", "501(c)(4)_organization",
                "Unrelated_business_income_tax", "Private_foundation",
                "Public_charity", "Donor-advised_fund",
                # More Tax Deep Dive
                "Hobby_loss_rule", "Home_sale_exclusion",
                "Kiddie_tax", "Marriage_penalty",
                "Filing_status", "Head_of_household",
                "Earned_income", "Unearned_income",
                "Adjusted_gross_income", "Modified_adjusted_gross_income",
                "Taxable_income", "Above-the-line_deduction",
                "Below-the-line_deduction",
                "Nonrefundable_tax_credit", "Refundable_tax_credit",
                "Child_tax_credit", "American_Opportunity_Tax_Credit",
                "Lifetime_Learning_Credit", "Saver%27s_Credit",
                # Business Tax Credits & Incentives
                "Research_and_development_tax_credit",
                "Work_opportunity_tax_credit",
                "New_Markets_Tax_Credit", "Low-Income_Housing_Tax_Credit",
                "Historic_preservation_tax_credit",
                "Investment_tax_credit", "Production_tax_credit",
                "Small_business_health_care_tax_credit",
                # Trusts & Estates Taxation
                "Trust_(law)", "Revocable_trust", "Irrevocable_trust",
                "Grantor_trust", "Simple_trust", "Complex_trust",
                "Estate_(law)", "Probate", "Will_and_testament",
                "Unified_credit", "Portability_(estate_tax)",
                "Generation-skipping_transfer_tax",
                "Crummey_trust", "Bypass_trust",
                # More International Tax
                "Base_erosion_and_profit_shifting",
                "OECD_Model_Tax_Convention", "Permanent_establishment",
                "Withholding_tax", "Transfer_pricing",
                "Advance_pricing_agreement", "Mutual_agreement_procedure",
                "Country-by-country_reporting",
                "Digital_services_tax", "Pillar_Two_(taxation)",
                # Tax Procedure & Administration
                "Internal_Revenue_Code", "Treasury_regulations",
                "Revenue_ruling", "Revenue_procedure",
                "Private_letter_ruling", "Technical_advice_memorandum",
                "Tax_court", "IRS_audit", "Statute_of_limitations_(taxes)",
                "Penalty_(taxation)", "Interest_on_tax",
                "Offer_in_compromise", "Innocent_spouse_relief",
                "Tax_lien", "Tax_levy",
                # Cryptocurrency & Digital Asset Tax
                "Cryptocurrency_and_taxation",
                "Virtual_currency_(IRS)", "Mining_(cryptocurrency)",
                "Staking_(cryptocurrency)", "Airdrop_(cryptocurrency)",
                "Hard_fork", "Decentralized_exchange",
            ]
        ],
    },
    # ── AccountingTools: Comprehensive ──
    {
        "name": "accountingtools",
        "urls": [
            _AT + s for s in [
                # Fundamentals
                "what-is-gaap.html", "balance-sheet", "income-statement",
                "general-ledger", "double-entry-accounting",
                "cost-of-goods-sold", "working-capital", "depreciation",
                "accounts-payable", "accounts-receivable", "goodwill",
                "fair-value", "contingent-liability", "impairment",
                "bank-reconciliation", "materiality", "market-value",
                # Advanced accounting
                "net-present-value", "earnings-per-share", "sales-tax",
                "accrued-liability", "operating-lease", "current-ratio",
                "debt-to-equity-ratio", "gross-margin", "variable-cost",
                "fixed-cost", "revenue-recognition", "deferred-revenue",
                # Cost accounting & budgeting
                "job-costing", "process-costing", "activity-based-costing",
                "standard-costing", "variance-analysis", "budget",
                "flexible-budget", "master-budget", "capital-budgeting",
                "break-even-point", "contribution-margin",
                "cost-volume-profit-analysis", "marginal-cost",
                "absorption-costing", "direct-costing",
                # Financial statement items
                "retained-earnings", "stockholders-equity", "treasury-stock",
                "preferred-stock", "common-stock", "paid-in-capital",
                "accumulated-other-comprehensive-income",
                "minority-interest", "intercompany-transactions",
                # Closing & adjusting
                "adjusting-entries", "closing-entries", "accrued-revenue",
                "prepaid-expenses", "unearned-revenue",
                # Inventory
                "fifo", "lifo", "weighted-average-method",
                "inventory-turnover", "days-sales-in-inventory",
                "lower-of-cost-or-market", "inventory-write-down",
                # Receivables
                "bad-debt-expense", "allowance-for-doubtful-accounts",
                "factoring", "aging-of-accounts-receivable",
                "days-sales-outstanding",
                # Payroll & tax
                "form-1099", "form-w-2", "payroll-taxes",
                "s-corporation", "c-corporation", "limited-liability-company",
                "tax-deduction", "tax-credit",
                # Audit & controls
                "audit-procedures", "substantive-testing",
                "internal-controls", "segregation-of-duties",
                "audit-opinion", "going-concern",
                # Advanced topics
                "lease-accounting", "right-of-use-asset", "lease-liability",
                "deferred-tax-asset", "deferred-tax-liability",
                "stock-based-compensation", "stock-options",
                "business-combination", "purchase-price-allocation",
                "consolidation-accounting", "intercompany-elimination",
                "foreign-currency-translation", "functional-currency",
                "derivative-accounting", "hedge-accounting",
                "fair-value-hierarchy", "level-1-inputs", "level-2-inputs",
                # Cash flow & working capital
                "cash-flow-statement", "direct-method", "indirect-method",
                "free-cash-flow", "cash-conversion-cycle",
                "days-payable-outstanding", "operating-cycle",
                # Ratios & analysis
                "acid-test-ratio", "interest-coverage-ratio",
                "asset-turnover-ratio", "return-on-equity",
                "return-on-assets", "profit-margin", "operating-margin",
                "gross-profit-ratio", "price-earnings-ratio",
                # Debt & equity instruments
                "bond-accounting", "bond-premium", "bond-discount",
                "effective-interest-method", "straight-line-amortization",
                "convertible-debt", "debt-covenant",
                "par-value", "book-value", "market-value-of-equity",
                # Revenue recognition deep
                "contract-asset", "contract-liability",
                "performance-obligation", "transaction-price",
                "variable-consideration", "contract-modification",
                "principal-vs-agent", "bill-and-hold",
                # Nonprofit & government
                "nonprofit-accounting", "fund-accounting",
                "restricted-fund", "unrestricted-fund",
                "net-assets", "statement-of-activities",
                # Managerial accounting
                "job-order-costing", "process-costing", "activity-based-costing",
                "standard-cost", "overhead-rate", "cost-allocation",
                "cost-pool", "cost-driver", "direct-cost", "indirect-cost",
                "period-cost", "product-cost",
                "transfer-price", "responsibility-center",
                # Bookkeeping & cycle
                "accounting-cycle", "trial-balance", "adjusting-entry",
                "closing-entry", "reversing-entry", "post-closing-trial-balance",
                "journal-entry-examples", "t-account", "debit-and-credit",
                "single-entry-system", "double-entry-system",
                # Financial analysis
                "horizontal-analysis", "vertical-analysis",
                "trend-analysis", "common-size-financial-statement",
                "dupont-analysis", "altman-z-score",
                "times-interest-earned-ratio", "debt-service-coverage-ratio",
                "fixed-charge-coverage-ratio", "cash-flow-to-debt-ratio",
                # Specific topics
                "troubled-debt-restructuring", "debt-extinguishment",
                "capital-lease", "sale-leaseback",
                "earnings-per-share", "diluted-earnings-per-share",
                "segment-reporting", "related-party-transaction",
                "subsequent-event", "contingency",
                "change-in-accounting-principle", "change-in-accounting-estimate",
                "error-correction", "restatement",
                # Payroll deep
                "gross-pay", "net-pay", "payroll-journal-entry",
                "employer-payroll-taxes", "payroll-accrual",
                "fringe-benefits", "compensated-absences",
                # SEC & reporting
                "form-10k", "form-10q", "sec-filing",
                "management-discussion-and-analysis",
                "annual-report", "proxy-statement",
                # More advanced accounting
                "push-down-accounting", "fresh-start-accounting",
                "quasi-reorganization", "spin-off-accounting",
                "variable-interest-entity", "special-purpose-entity",
                "joint-venture-accounting", "equity-method-investment",
                "cost-method-investment", "trading-securities",
                "available-for-sale-securities", "held-to-maturity-securities",
                "unrealized-gain", "realized-gain",
                "other-comprehensive-income", "accumulated-other-comprehensive-income",
                # More ratios & metrics
                "return-on-invested-capital", "economic-value-added",
                "free-cash-flow", "enterprise-value",
                "ev-to-ebitda", "price-to-sales-ratio",
                "price-to-cash-flow-ratio", "dividend-payout-ratio",
                "dividend-yield", "earnings-yield",
                "book-value-per-share", "tangible-book-value",
                # More cost accounting
                "equivalent-unit", "spoilage", "scrap",
                "byproduct-accounting", "joint-cost-allocation",
                "service-department-cost-allocation",
                "reciprocal-method", "step-down-method", "direct-method-cost-allocation",
                # More tax topics
                "deferred-tax-asset", "deferred-tax-liability",
                "temporary-difference", "permanent-difference",
                "valuation-allowance", "uncertain-tax-position",
                "effective-tax-rate", "statutory-tax-rate",
                "income-tax-provision", "tax-rate-reconciliation",
                # More specialized AccountingTools
                "percentage-of-completion-method", "completed-contract-method",
                "installment-method", "cost-recovery-method",
                "consignment-accounting", "franchise-accounting",
                "construction-accounting", "real-estate-accounting",
                "insurance-accounting", "banking-accounting",
                "oil-and-gas-accounting", "mining-accounting",
                "agriculture-accounting", "healthcare-accounting",
                "software-capitalization", "website-development-costs",
                "cloud-computing-costs", "startup-costs",
                "organization-costs", "research-and-development-costs",
                # More financial instruments
                "interest-rate-swap", "currency-swap",
                "forward-contract", "futures-contract",
                "option-accounting", "collar-accounting",
                "embedded-derivative", "bifurcation",
                "beneficial-conversion-feature",
                "original-issue-discount", "debt-issuance-costs",
                # More consolidation
                "elimination-entry", "intercompany-profit",
                "noncontrolling-interest", "step-acquisition",
                "deconsolidation", "disposal-of-subsidiary",
                # Ethics & fraud
                "fraud-triangle", "occupational-fraud",
                "financial-statement-fraud", "asset-misappropriation",
                "corruption-fraud", "whistleblower-protection",
                "code-of-ethics", "professional-skepticism",
            ]
        ],
    },
    # ── CFI: Finance & Valuation ──
    {
        "name": "cfi_finance",
        "urls": [
            _CFI + s for s in [
                "accounting/balance-sheet/",
                "accounting/income-statement/",
                "valuation/net-present-value-npv/",
                "valuation/internal-rate-of-return-irr/",
                "valuation/wacc/",
                "accounting/ebitda/",
                "accounting/earnings-per-share-eps/",
                "valuation/price-earnings-ratio/",
                "accounting/return-on-assets-roa/",
                "capital-markets/beta-coefficient/",
                "accounting/financial-ratios/",
                "accounting/dupont-analysis/",
                "valuation/dcf-formula/",
                "accounting/current-ratio/",
                "accounting/quick-ratio-acid-test/",
                "accounting/debt-to-equity-ratio/",
                "accounting/inventory-turnover/",
                "accounting/asset-turnover-ratio/",
                "accounting/operating-cash-flow-ratio/",
                "accounting/gross-profit-margin/",
                "accounting/operating-profit-margin/",
                "accounting/net-profit-margin/",
                "valuation/terminal-value/",
                "valuation/comparable-company-analysis/",
                "valuation/precedent-transaction-analysis/",
                "valuation/leveraged-buyout-lbo/",
                "accounting/cash-flow-from-operations/",
                "accounting/cash-flow-from-investing/",
                "accounting/cash-flow-from-financing/",
                "accounting/straight-line-depreciation/",
                "accounting/double-declining-balance/",
                "accounting/sum-of-years-digits/",
                "accounting/units-of-production-depreciation/",
                "accounting/journal-entry/",
                "accounting/trial-balance/",
                "accounting/general-ledger/",
                "accounting/chart-of-accounts/",
                "accounting/accrual-accounting/",
                "accounting/cash-basis-accounting/",
                # Valuation & M&A
                "valuation/enterprise-value/",
                "valuation/equity-value/",
                "valuation/market-capitalization/",
                "valuation/ev-to-ebitda/",
                "valuation/price-to-book-ratio/",
                "valuation/dividend-discount-model/",
                "valuation/gordon-growth-model/",
                "valuation/free-cash-flow-to-firm/",
                "valuation/free-cash-flow-to-equity/",
                "valuation/unlevered-beta/",
                # Fixed Income & Credit
                "capital-markets/yield-to-maturity/",
                "capital-markets/coupon-rate/",
                "capital-markets/bond-pricing/",
                "capital-markets/yield-curve/",
                "capital-markets/credit-spread/",
                "capital-markets/duration/",
                "capital-markets/convexity/",
                # Corporate Finance
                "accounting/working-capital/",
                "accounting/cash-conversion-cycle/",
                "accounting/days-sales-outstanding/",
                "accounting/days-payable-outstanding/",
                "accounting/days-inventory-outstanding/",
                "accounting/capital-structure/",
                "accounting/cost-of-equity/",
                "accounting/cost-of-debt/",
                # Financial Modeling
                "valuation/types-of-financial-models/",
                "valuation/sensitivity-analysis/",
                "valuation/scenario-analysis/",
                "valuation/monte-carlo-simulation/",
                # Accounting Standards
                "accounting/revenue-recognition/",
                "accounting/lease-accounting/",
                "accounting/stock-based-compensation/",
                "accounting/goodwill-impairment/",
                "accounting/deferred-tax/",
                "accounting/fair-value-accounting/",
                "accounting/hedge-accounting/",
                "accounting/consolidation-accounting/",
                # More CFI topics
                "accounting/accounts-receivable-turnover/",
                "accounting/fixed-asset-turnover/",
                "accounting/equity-multiplier/",
                "accounting/interest-coverage-ratio/",
                "accounting/debt-service-coverage-ratio/",
                "accounting/operating-cycle/",
                "accounting/net-working-capital/",
                "accounting/cash-ratio/",
                "accounting/defensive-interval-ratio/",
                "valuation/asset-based-valuation/",
                "valuation/sum-of-the-parts-valuation/",
                "valuation/football-field-chart/",
                "valuation/cap-rate/",
                "valuation/relative-valuation/",
                "valuation/intrinsic-value/",
                "capital-markets/risk-free-rate/",
                "capital-markets/equity-risk-premium/",
                "capital-markets/market-risk-premium/",
                "capital-markets/systematic-risk/",
                "capital-markets/unsystematic-risk/",
                "capital-markets/sharpe-ratio/",
                "capital-markets/treynor-ratio/",
                "capital-markets/sortino-ratio/",
                "capital-markets/information-ratio/",
                # M&A and restructuring
                "valuation/merger-model/",
                "valuation/accretion-dilution/",
                "valuation/pro-forma-financial-statements/",
                "valuation/purchase-price-allocation/",
                "valuation/goodwill-calculation/",
                "accounting/restructuring-charges/",
                "accounting/impairment-of-goodwill/",
                "accounting/asset-write-down/",
                # Banking & credit
                "capital-markets/commercial-banking/",
                "capital-markets/investment-banking-overview/",
                "capital-markets/credit-analysis/",
                "capital-markets/five-cs-of-credit/",
                "capital-markets/loan-covenant/",
                "capital-markets/leverage-ratio/",
                "capital-markets/debt-to-capital-ratio/",
                # Private equity & venture
                "capital-markets/private-equity/",
                "capital-markets/venture-capital/",
                "capital-markets/leveraged-buyout/",
                "capital-markets/management-buyout/",
                "capital-markets/mezzanine-financing/",
                "capital-markets/initial-public-offering/",
                "capital-markets/secondary-offering/",
                "capital-markets/direct-listing/",
                "capital-markets/spac/",
                # Risk management
                "capital-markets/value-at-risk/",
                "capital-markets/expected-shortfall/",
                "capital-markets/stress-testing/",
                "capital-markets/hedging/",
                "capital-markets/interest-rate-risk/",
                "capital-markets/currency-risk/",
                "capital-markets/counterparty-risk/",
                "capital-markets/operational-risk/",
                # Economics & macro
                "accounting/inflation-accounting/",
                "capital-markets/monetary-policy/",
                "capital-markets/fiscal-policy/",
                "capital-markets/gdp/",
                "capital-markets/consumer-price-index/",
                "capital-markets/purchasing-power-parity/",
                "capital-markets/interest-rate-parity/",
                "capital-markets/fisher-effect/",
                # ESG & sustainability
                "accounting/esg-reporting/",
                "accounting/sustainability-reporting/",
                "accounting/carbon-accounting/",
                "accounting/integrated-reporting/",
                # Real estate finance
                "valuation/real-estate-valuation/",
                "valuation/cap-rate/",
                "valuation/net-operating-income/",
                "valuation/cash-on-cash-return/",
                "valuation/debt-yield/",
                "valuation/loan-to-value/",
            ]
        ],
    },
    # ── IRS: Tax Compliance ──
    {
        "name": "irs_tax",
        "urls": [
            _IRS + s for s in [
                "businesses/small-businesses-self-employed/deducting-business-expenses",
                "businesses/small-businesses-self-employed/estimated-taxes",
                "businesses/small-businesses-self-employed/self-employment-tax-social-security-and-medicare-taxes",
                "businesses/small-businesses-self-employed/business-structures",
                "businesses/small-businesses-self-employed/understanding-employment-taxes",
                "credits-deductions/individuals/earned-income-tax-credit-eitc",
                "businesses/small-businesses-self-employed/managing-business-records",
                "businesses/small-businesses-self-employed/business-expenses",
                "businesses/small-businesses-self-employed/tangible-property-final-regulations",
                "businesses/small-businesses-self-employed/what-is-taxable-and-nontaxable-income",
                "businesses/small-businesses-self-employed/filing-past-due-tax-returns",
                "individuals/international-taxpayers/classification-of-taxpayers-for-us-tax-purposes",
                "businesses/small-businesses-self-employed/choosing-a-business-structure",
                "businesses/small-businesses-self-employed/sole-proprietorships",
                "businesses/small-businesses-self-employed/partnerships",
                "businesses/small-businesses-self-employed/limited-liability-company-llc",
                "businesses/small-businesses-self-employed/s-corporations",
                "businesses/small-businesses-self-employed/corporations",
                "businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee",
                "businesses/small-businesses-self-employed/business-tax-credits",
                "businesses/small-businesses-self-employed/business-income",
                "retirement-plans/plan-sponsor/types-of-retirement-plans",
                "businesses/small-businesses-self-employed/depreciation-of-business-assets",
                "businesses/small-businesses-self-employed/home-office-deduction",
                "businesses/small-businesses-self-employed/deducting-travel-entertainment-gift-and-car-expenses",
                "businesses/small-businesses-self-employed/virtual-currencies",
                "individuals/international-taxpayers/foreign-earned-income-exclusion",
                "businesses/small-businesses-self-employed/inventory",
                "businesses/small-businesses-self-employed/accounting-periods-and-methods",
                "businesses/small-businesses-self-employed/installment-sales",
                "businesses/small-businesses-self-employed/like-kind-exchanges-real-estate-tax-tips",
            ]
        ],
    },
]


# ── Schedule / State ──

def load_schedule():
    if os.path.exists(SCHEDULE_FILE):
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"fetched_urls": {}, "low_yield_streak": 0}

def save_schedule(sched):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(sched, f, indent=2)


# ═══════════════════════════════════════════════════════════════════
# PARSERS — all extract MULTIPLE entries per page (section-by-section)
# ═══════════════════════════════════════════════════════════════════

def fetch_page(url):
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        log.warning(f"Failed to fetch {url}: {e}")
        return None

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\[\d+\]', '', text)  # Remove Wikipedia citation markers
    return text

def _get_page_title(soup):
    """Extract and clean the page title from h1."""
    tag = soup.find('h1', {'id': 'firstHeading'}) or soup.find('h1')
    if not tag:
        return None
    title = clean_text(tag.get_text())
    title = re.sub(r'\s*\(.*?\)\s*$', '', title)  # Remove disambiguation
    title = re.sub(r'\s*[—\-|]\s*(AccountingTools|Wikipedia|CFI).*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^What (is|are) (a |an |the )?', '', title, flags=re.IGNORECASE)
    return title.rstrip('?').strip()

def _section_to_entry(page_title, section_title, content_text, source, url):
    """Build a knowledge entry from a page section, with page-topic context in patterns."""
    if not content_text or len(content_text) < 50:
        return None
    if len(content_text) > 500:
        content_text = content_text[:497] + '...'

    # Generate patterns from section title, with page title context
    patterns = generate_patterns(section_title)
    if not patterns:
        return None

    # Add page-level context patterns if section title differs from page title
    if page_title and page_title.lower() != section_title.lower():
        page_patterns = generate_patterns(page_title)
        # Add the page topic as an extra pattern for searchability
        for pp in page_patterns[:2]:
            combo = f"{pp} {patterns[0]}" if len(pp) + len(patterns[0]) < 50 else pp
            if combo not in patterns:
                patterns.append(combo)

    return {
        "patterns": patterns[:6],
        "response": content_text,
        "action": None,
        "_source": source,
        "_url": url,
        "_date": date.today().isoformat()
    }

def _collect_section_text(header, limit_paragraphs=4):
    """Collect paragraph text following a header until the next header."""
    parts = []
    for sib in header.find_next_siblings():
        if sib.name in ['h1', 'h2', 'h3']:
            break
        if sib.name in ['p', 'li']:
            text = clean_text(sib.get_text())
            if len(text) > 25:
                parts.append(text)
        if len(parts) >= limit_paragraphs:
            break
    return ' '.join(parts)

NOISE_TITLES = {'see also', 'references', 'external links', 'notes', 'further reading',
                'contents', 'navigation menu', 'bibliography', 'categories', 'sources',
                'related articles', 'related topics', 'cookie', 'privacy', 'about',
                'footer', 'sidebar', 'advertisement', 'sign up', 'subscribe', 'edit'}

def _is_noise_title(title):
    return title.lower().strip() in NOISE_TITLES or len(title) < 3 or len(title) > 100


def extract_deep_entries(soup, url, source):
    """Universal deep extractor — gets intro + every h2/h3 section as separate entries."""
    page_title = _get_page_title(soup)
    if not page_title:
        return []

    entries = []

    # 1. Intro entry — first meaningful paragraphs before any h2
    intro_parts = []
    # For Wikipedia, look inside mw-parser-output; for others, use body
    content_root = soup.find('div', {'class': 'mw-parser-output'}) or soup.find('article') or soup.find('main') or soup
    for el in content_root.children if hasattr(content_root, 'children') else []:
        if hasattr(el, 'name'):
            if el.name in ['h2', 'h3']:
                break
            if el.name == 'p':
                text = clean_text(el.get_text())
                if len(text) > 60 and 'cookie' not in text.lower():
                    intro_parts.append(text)
                if len(intro_parts) >= 2:
                    break
    if intro_parts:
        intro_text = ' '.join(intro_parts)
        if len(intro_text) > 500:
            intro_text = intro_text[:497] + '...'
        intro_entry = _section_to_entry(None, page_title, intro_text, source, url)
        if intro_entry:
            entries.append(intro_entry)

    # 2. Section entries — every h2 and h3
    for header in content_root.find_all(['h2', 'h3'], limit=25):
        section_title = clean_text(header.get_text())
        # Remove Wikipedia [edit] links
        section_title = re.sub(r'\[edit\]', '', section_title).strip()
        if _is_noise_title(section_title):
            continue

        section_text = _collect_section_text(header)
        entry = _section_to_entry(page_title, section_title, section_text, source, url)
        if entry:
            entries.append(entry)

    return entries


# ═══════════════════════════════════════════════════════════════════
# PATTERN GENERATION
# ═══════════════════════════════════════════════════════════════════

STOP_WORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
              'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
              'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
              'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'between',
              'through', 'during', 'before', 'after', 'above', 'below', 'and', 'or',
              'but', 'not', 'no', 'so', 'if', 'than', 'too', 'very', 'just', 'also',
              'how', 'what', 'when', 'where', 'why', 'which', 'who', 'whom', 'this',
              'that', 'these', 'those', 'it', 'its', 'your', 'you', 'we', 'they',
              'their', 'our', 'my', 'his', 'her', 'all', 'each', 'every', 'both',
              'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same',
              'then', 'now', 'here', 'there', 'up', 'out', 'over', 'under'}

KNOWN_ABBREVIATIONS = {
    'gaap', 'ifrs', 'fasb', 'asc', 'sec', 'irs', 'cpa', 'cfo', 'ceo',
    'npv', 'irr', 'roi', 'roe', 'roa', 'eps', 'ebitda', 'wacc', 'capm',
    'pe', 'ev', 'fcf', 'dcf', 'tvm', 'apr', 'apy', 'ytm',
    'ap', 'ar', 'gl', 'coa', 'cogs', 'opex', 'capex', 'ppe',
    'fifo', 'lifo', 'cecl', 'llc', 'llp', 'lbo',
    'fica', 'futa', 'suta', 'ein', 'tin', 'ssn',
    'sox', 'pcaob', 'aicpa', 'gasb', 'iasb',
    'erp', 'crm', 'saas', 'etf', 'ipo',
    'ebit', 'nopat', 'roic', 'mirr', 'dso', 'dio', 'dpo', 'ccc',
    'bps', 'nav', 'aum', 'macrs', 'amt', 'eitc', 'eva',
}

SITE_NOISE = {'accountingtools', 'corporatefinanceinstitute', 'wikipedia',
              'investopedia', 'irs', 'sec', 'cfi', 'www'}

def generate_patterns(title):
    if not title or len(title) < 3:
        return []

    patterns = []
    full = re.sub(r'[^\w\s&\'-]', '', title.lower()).strip()
    if len(full) >= 3 and full not in SITE_NOISE:
        patterns.append(full)

    words = [w for w in full.split() if w not in STOP_WORDS and len(w) > 2]

    # Known abbreviations only
    if len(words) >= 2:
        abbrev = ''.join(w[0] for w in words).lower()
        if abbrev in KNOWN_ABBREVIATIONS:
            patterns.append(abbrev)
    for w in full.split():
        w_lower = w.lower().strip("'-")
        if w_lower in KNOWN_ABBREVIATIONS and w_lower not in patterns:
            patterns.append(w_lower)

    # Two-word phrases
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i+1]}"
        if phrase not in patterns and phrase not in SITE_NOISE:
            patterns.append(phrase)

    # Individual important words (5+ chars)
    for w in words:
        if len(w) >= 5 and w not in patterns and w not in SITE_NOISE:
            patterns.append(w)

    # Filter out any site noise that slipped through
    patterns = [p for p in patterns if p.lower() not in SITE_NOISE]
    return patterns[:6]


# ═══════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ═══════════════════════════════════════════════════════════════════

def is_duplicate(new_entry, existing_entries):
    new_patterns = set(p.lower() for p in new_entry['patterns'])

    for existing in existing_entries:
        ex_patterns = set(p.lower() for p in existing['patterns'])

        # Direct pattern overlap
        if new_patterns & ex_patterns:
            return True

        # Fuzzy match on response text
        similarity = SequenceMatcher(
            None,
            new_entry['response'][:200].lower(),
            existing['response'][:200].lower()
        ).ratio()
        if similarity > 0.7:
            return True

    return False


# ═══════════════════════════════════════════════════════════════════
# MAIN GATHER PIPELINE
# ═══════════════════════════════════════════════════════════════════

def gather():
    log.info("=" * 60)
    log.info(f"Vera Knowledge Gatherer — {datetime.now().isoformat()}")
    log.info("=" * 60)

    # Load existing knowledge
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge = json.load(f)
    else:
        knowledge = []
    log.info(f"Existing knowledge entries: {len(knowledge)}")

    sched = load_schedule()
    fetched_urls = sched.get("fetched_urls", {})
    new_entries = []
    pages_fetched = 0

    # Hit ALL sources every run
    for source in SOURCES:
        log.info(f"\n--- {source['name']} ({len(source['urls'])} URLs) ---")

        for url in source['urls']:
            url_hash = md5(url.encode()).hexdigest()[:12]
            if url_hash in fetched_urls:
                continue  # Already fetched — skip silently

            log.info(f"  Fetching: {url}")
            soup = fetch_page(url)
            if not soup:
                continue
            pages_fetched += 1

            # Universal deep extraction for all sources
            entries = extract_deep_entries(soup, url, source['name'])
            log.info(f"    Extracted {len(entries)} sections")

            for entry in entries:
                # Skip entries with no useful patterns
                if not entry['patterns']:
                    continue
                if not is_duplicate(entry, knowledge + new_entries):
                    new_entries.append(entry)
                    log.info(f"    + {entry['patterns'][:2]}")
                # Don't log every duplicate — too noisy at scale

            fetched_urls[url_hash] = {"url": url, "date": date.today().isoformat()}

    # Append new entries
    if new_entries:
        knowledge.extend(new_entries)
        with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)
        log.info(f"\nAdded {len(new_entries)} new entries. Total: {len(knowledge)}")
    else:
        log.info("\nNo new entries to add today.")

    # Saturation detection
    low_yield = sched.get("low_yield_streak", 0)
    if pages_fetched > 20 and len(new_entries) < 5:
        low_yield += 1
        log.info(f"Low yield run ({len(new_entries)} from {pages_fetched} pages). Streak: {low_yield}")
        if low_yield >= 3:
            log.info("SATURATED — Knowledge base matches authoritative sources. Consider switching to weekly.")
            sched["saturated"] = True
    else:
        low_yield = 0

    sched["fetched_urls"] = fetched_urls
    sched["low_yield_streak"] = low_yield
    sched["last_run"] = datetime.now().isoformat()
    sched["last_added"] = len(new_entries)
    sched["total_entries"] = len(knowledge)
    save_schedule(sched)

    log.info("Gatherer complete.")
    return len(new_entries)


if __name__ == '__main__':
    try:
        added = gather()
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
