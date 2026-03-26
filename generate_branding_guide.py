"""Generate Veracity Branding Guide PDF."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "Veracity_Branding_Guide.pdf")

# Try to register Google Fonts if available locally
try:
    pdfmetrics.registerFont(TTFont('PlayfairDisplay', 'C:/Users/ConnorFinuf/AppData/Local/Microsoft/Windows/Fonts/PlayfairDisplay-Bold.ttf'))
    BRAND_FONT = 'PlayfairDisplay'
except:
    BRAND_FONT = 'Times-Bold'

try:
    pdfmetrics.registerFont(TTFont('Inter', 'C:/Users/ConnorFinuf/AppData/Local/Microsoft/Windows/Fonts/Inter-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('Inter-Bold', 'C:/Users/ConnorFinuf/AppData/Local/Microsoft/Windows/Fonts/Inter-Bold.ttf'))
    BODY_FONT = 'Inter'
    BODY_BOLD = 'Inter-Bold'
except:
    BODY_FONT = 'Helvetica'
    BODY_BOLD = 'Helvetica-Bold'


def hex_color(h):
    return HexColor(h)


def draw_swatch(c, x, y, hex_val, name, role, swatch_w=36, swatch_h=24):
    """Draw a color swatch with label."""
    # Swatch rectangle
    color = hex_color(hex_val)
    c.setFillColor(color)
    c.setStrokeColor(HexColor('#D1D5DB'))
    c.setLineWidth(0.5)
    c.roundRect(x, y - 2, swatch_w, swatch_h, 4, fill=1, stroke=1)

    # Name
    c.setFillColor(HexColor('#1F2937'))
    c.setFont(BODY_BOLD, 10)
    c.drawString(x + swatch_w + 12, y + 12, name)

    # Hex
    c.setFont(BODY_FONT, 9)
    c.setFillColor(HexColor('#5A5F6B'))
    c.drawString(x + swatch_w + 12, y, hex_val)

    # Role
    c.setFont(BODY_FONT, 8.5)
    c.setFillColor(HexColor('#6B7280'))
    c.drawString(x + swatch_w + 140, y + 6, role)


def draw_section_header(c, y, title):
    """Draw a section header with copper underline."""
    c.setFont(BODY_BOLD, 14)
    c.setFillColor(HexColor('#2A2D35'))
    c.drawString(60, y, title)
    c.setStrokeColor(HexColor('#CDAA7D'))
    c.setLineWidth(1.5)
    c.line(60, y - 6, 552, y - 6)
    return y - 28


def new_page_if_needed(c, y, needed=100):
    if y < needed:
        c.showPage()
        return 720
    return y


def build_pdf():
    c = canvas.Canvas(OUTPUT, pagesize=letter)
    w, h = letter  # 612 x 792

    # ===== COVER PAGE =====
    # Dark charcoal background
    c.setFillColor(HexColor('#2A2D35'))
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Copper accent bar
    c.setFillColor(HexColor('#CDAA7D'))
    c.rect(0, h * 0.48, w, 4, fill=1, stroke=0)

    # Brand name
    c.setFillColor(white)
    c.setFont(BRAND_FONT, 52)
    c.drawCentredString(w / 2, h * 0.62, "Veracity")

    # Tagline
    c.setFillColor(HexColor('#CDAA7D'))
    c.setFont(BODY_FONT, 13)
    c.drawCentredString(w / 2, h * 0.56, "Your All-in-One Small Business Financial Toolkit")

    # Subtitle
    c.setFillColor(HexColor('#a0a4ae'))
    c.setFont(BODY_BOLD, 20)
    c.drawCentredString(w / 2, h * 0.40, "Branding Guide")

    # Bottom accent
    c.setFillColor(HexColor('#B87333'))
    c.rect(0, 0, w, 6, fill=1, stroke=0)

    # Date
    c.setFillColor(HexColor('#6B7280'))
    c.setFont(BODY_FONT, 9)
    c.drawCentredString(w / 2, 24, "March 2026")

    c.showPage()

    # ===== PAGE 2: Primary Brand Colors =====
    y = 720
    y = draw_section_header(c, y, "Primary Brand Colors")

    primary = [
        ('#2A2D35', 'Dark Charcoal', 'Primary dark — nav rail, buttons, accent backgrounds'),
        ('#353840', 'Dark Charcoal Hover', 'Hover/active state for primary elements'),
        ('#CDAA7D', 'Light Tan', 'Secondary brand color — logo accent, highlights, badges'),
        ('#B87333', 'Copper', 'Accent color — explainer boxes, deeper emphasis, CTA hover'),
    ]
    for hex_val, name, role in primary:
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    y -= 16
    y = draw_section_header(c, y, "Neutral Palette")

    neutrals = [
        ('#5A5F6B', 'Charcoal Slate', 'Accent text, headings, muted text'),
        ('#1F2937', 'Charcoal', 'Body text, deep UI elements'),
        ('#6B7280', 'Muted Grey', 'Secondary/placeholder text'),
        ('#D5D7DC', 'Navbar Gray', 'Top navigation bar background'),
        ('#E2E5E9', 'Border', 'Default border color'),
        ('#D1D5DB', 'Border Strong', 'Emphasized borders'),
        ('#F1F3F5', 'Surface 2', 'Slightly elevated surfaces'),
        ('#F9FAFB', 'Off White', 'Surface/card backgrounds'),
        ('#F7F8F6', 'Background', 'Page background'),
        ('#FFFFFF', 'White', 'Card/panel backgrounds'),
    ]
    for hex_val, name, role in neutrals:
        y = new_page_if_needed(c, y)
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    # ===== Section Icon Colors =====
    y -= 16
    y = new_page_if_needed(c, y, 180)
    y = draw_section_header(c, y, "Section Icon Colors")

    c.setFont(BODY_FONT, 10)
    c.setFillColor(HexColor('#5A5F6B'))
    c.drawString(60, y + 4, "Each navigation section has a distinct icon color for quick visual identification.")
    y -= 24

    sections = [
        ('#16a34a', 'Accounting', 'Green — Academy, ASC, Calendar, JE Practice, Lease Classifier'),
        ('#3b82f6', 'Finance', 'Blue — Amortization, Break-Even, Depreciation, Ratios, Markup, TVM'),
        ('#ef4444', 'Project Trackers', 'Red — Solar Tracker'),
    ]
    for hex_val, name, role in sections:
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    # ===== Tool Accent Colors =====
    y -= 16
    y = new_page_if_needed(c, y, 420)
    y = draw_section_header(c, y, "Tool Accent Colors")

    c.setFont(BODY_FONT, 10)
    c.setFillColor(HexColor('#5A5F6B'))
    c.drawString(60, y + 4, "Each tool has a unique accent tinted toward its section color (green/blue/red).")
    y -= 24

    # Accounting — Modules (green family)
    c.setFont(BODY_BOLD, 10)
    c.setFillColor(HexColor('#16a34a'))
    c.drawString(60, y + 4, "Accounting — Modules")
    y -= 22

    acct_modules = [
        ('#16a34a', 'AP Management', 'Green — vendor bills and payments'),
        ('#059669', 'AR Management', 'Emerald — customer invoices and collections'),
        ('#0d9488', 'General Ledger', 'Teal — master transaction record'),
    ]
    for hex_val, name, role in acct_modules:
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    y -= 8
    c.setFont(BODY_BOLD, 10)
    c.setFillColor(HexColor('#16a34a'))
    c.drawString(60, y + 4, "Accounting — Tools & Reference")
    y -= 22

    acct_tools = [
        ('#22c55e', 'Academy', 'Lime-green — beginner accounting lessons'),
        ('#10b981', 'Acct Calendar', 'Seafoam — fiscal year deadlines'),
        ('#15803d', 'ASC Codification', 'Forest — GAAP standards reference'),
        ('#0ea5e9', 'JE Practice', 'Sky — journal entry training'),
        ('#14b8a6', 'Lease Classifier', 'Teal-green — ASC 842 lease classification'),
    ]
    for hex_val, name, role in acct_tools:
        y = new_page_if_needed(c, y)
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    y -= 8
    c.setFont(BODY_BOLD, 10)
    c.setFillColor(HexColor('#3b82f6'))
    c.drawString(60, y + 4, "Finance (blue family)")
    y -= 22

    tools = [
        ('#6366f1', 'TVM Calculator', 'Indigo — time value of money'),
        ('#3b82f6', 'Amortization', 'Blue — loan payment schedules'),
        ('#8b5cf6', 'Depreciation', 'Violet — asset value tracking'),
        ('#2563eb', 'Break-Even', 'Royal Blue — profit threshold analysis'),
        ('#06b6d4', 'Markup vs Margin', 'Cyan — pricing calculations'),
        ('#7c3aed', 'Financial Ratios', 'Purple — financial health checks'),
    ]
    for hex_val, name, role in tools:
        y = new_page_if_needed(c, y)
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    # ===== Dark Mode Palette =====
    c.showPage()
    y = 720

    # Dark background demo strip
    c.setFillColor(HexColor('#1a1d24'))
    c.roundRect(60, y - 60, 492, 70, 8, fill=1, stroke=0)
    c.setFillColor(HexColor('#CDAA7D'))
    c.setFont(BRAND_FONT, 22)
    c.drawString(80, y - 20, "Veracity")
    c.setFillColor(HexColor('#e2e4e9'))
    c.setFont(BODY_FONT, 11)
    c.drawString(80, y - 44, "Dark mode preserves brand identity with adjusted values for readability.")
    y -= 90

    y = draw_section_header(c, y, "Dark Mode Palette")

    dark_colors = [
        ('#1a1d24', 'Dark BG', 'Page background in dark mode'),
        ('#22252d', 'Dark Surface', 'Card/panel backgrounds'),
        ('#2a2d35', 'Dark Surface 2', 'Elevated surfaces'),
        ('#32353d', 'Dark Surface 3', 'Highest elevation surfaces'),
        ('#151820', 'Dark Nav Rail', 'Navigation rail background'),
        ('#2e3240', 'Dark Border', 'Default borders in dark mode'),
        ('#3a3e4c', 'Dark Border Strong', 'Emphasized borders in dark mode'),
        ('#e2e4e9', 'Dark Text', 'Primary text in dark mode'),
        ('#8b8f9a', 'Dark Text Muted', 'Secondary text in dark mode'),
        ('#c4c7ce', 'Dark Accent Text', 'Headings in dark mode'),
        ('#a0a4ae', 'Dark Charcoal Slate', 'Adjusted charcoal slate for dark bg'),
    ]
    for hex_val, name, role in dark_colors:
        y = new_page_if_needed(c, y)
        # Use dark bg behind light swatches for contrast
        is_light = hex_val in ('#e2e4e9', '#8b8f9a', '#c4c7ce', '#a0a4ae')
        if not is_light:
            c.setFillColor(HexColor('#0e1015'))
            c.roundRect(56, y - 5, 44, 30, 4, fill=1, stroke=0)
        draw_swatch(c, 60, y, hex_val, name, role)
        y -= 38

    # ===== Typography =====
    y -= 16
    y = new_page_if_needed(c, y, 200)
    y = draw_section_header(c, y, "Typography")

    # Brand font
    c.setFont(BRAND_FONT, 28)
    c.setFillColor(HexColor('#2A2D35'))
    c.drawString(60, y, "Playfair Display")
    c.setFont(BODY_FONT, 10)
    c.setFillColor(HexColor('#5A5F6B'))
    c.drawString(60, y - 18, "Brand / Logo — serif, used for the Veracity wordmark and decorative headings")
    y -= 50

    c.setFont(BODY_FONT, 22)
    c.setFillColor(HexColor('#2A2D35'))
    c.drawString(60, y, "Inter")
    c.setFont(BODY_FONT, 10)
    c.setFillColor(HexColor('#5A5F6B'))
    c.drawString(60, y - 18, "Body / UI — sans-serif, used for all interface text, labels, and descriptions")
    y -= 50

    # Font scale
    c.setFont(BODY_BOLD, 11)
    c.setFillColor(HexColor('#2A2D35'))
    c.drawString(60, y, "Type Scale")
    y -= 20
    scales = [
        (22, 'Page Title — 22px bold'),
        (16, 'Section Header — 16px bold'),
        (14, 'Card Title — 14px semi-bold'),
        (13, 'Body Text — 13px regular'),
        (12, 'Nav Labels — 12px medium'),
        (11, 'Captions — 11px regular'),
        (10, 'Badges / Tags — 10px semi-bold'),
    ]
    for size, label in scales:
        y = new_page_if_needed(c, y)
        c.setFont(BODY_FONT, size)
        c.setFillColor(HexColor('#2A2D35'))
        c.drawString(60, y, label)
        y -= size + 10

    # ===== Usage Guidelines =====
    y -= 20
    y = new_page_if_needed(c, y, 200)
    y = draw_section_header(c, y, "Usage Guidelines")

    guidelines = [
        "Use Dark Charcoal (#2A2D35) for primary actions, nav rail, and button backgrounds.",
        "Use Light Tan (#CDAA7D) as the secondary highlight — toggles, active states, and badges.",
        "Use Copper (#B87333) sparingly for emphasis — explainer boxes, hover accents, and CTAs.",
        "Reserve section colors (green/blue/red) exclusively for their navigation category icons.",
        "Each tool's accent color is tinted toward its section (green for Accounting, blue for Finance, red for Trackers).",
        "In dark mode, use the adjusted palette — never place light-mode colors on dark backgrounds.",
        "Maintain sufficient contrast: light text on dark surfaces, dark text on light surfaces.",
        "The Veracity wordmark always uses Playfair Display. Never substitute with a sans-serif.",
    ]
    for g in guidelines:
        y = new_page_if_needed(c, y, 40)
        # Copper bullet
        c.setFillColor(HexColor('#B87333'))
        c.circle(68, y + 4, 3, fill=1, stroke=0)
        c.setFillColor(HexColor('#1F2937'))
        c.setFont(BODY_FONT, 10)
        c.drawString(80, y, g)
        y -= 22

    # Footer on last page
    c.setFillColor(HexColor('#CDAA7D'))
    c.rect(0, 0, w, 4, fill=1, stroke=0)
    c.setFillColor(HexColor('#6B7280'))
    c.setFont(BODY_FONT, 8)
    c.drawCentredString(w / 2, 12, "Veracity Branding Guide — Confidential — March 2026")

    c.save()
    print(f"PDF saved to: {OUTPUT}")


if __name__ == '__main__':
    build_pdf()
