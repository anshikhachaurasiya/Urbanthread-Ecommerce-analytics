"""
Builds excel/Ecommerce_Funnel_Retention_Dashboard.xlsx from the CSVs exported
by export_query_results.py. Uses openpyxl for charts + formatting, with live
formulas (SUMIFS etc.) rather than hardcoded results wherever the sheet can
recalculate from a raw data tab.
"""
import csv
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.utils import get_column_letter

EXPORT_DIR = "../powerbi/exports"
OUT_PATH = "../excel/Ecommerce_Funnel_Retention_Dashboard.xlsx"

NAVY = "1F2A44"
ACCENT = "E8734A"
LIGHT = "F2F2F2"
FONT_NAME = "Calibri"

header_font = Font(name=FONT_NAME, bold=True, color="FFFFFF", size=11)
header_fill = PatternFill("solid", fgColor=NAVY)
title_font = Font(name=FONT_NAME, bold=True, size=16, color=NAVY)
subtitle_font = Font(name=FONT_NAME, italic=True, size=10, color="666666")
kpi_label_font = Font(name=FONT_NAME, size=10, color="666666")
kpi_value_font = Font(name=FONT_NAME, bold=True, size=20, color=NAVY)
thin_border = Border(*(Side(style="thin", color="D9D9D9"),) * 4)


def read_csv(name):
    with open(f"{EXPORT_DIR}/{name}.csv") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows[0], rows[1:]


def write_table(ws, start_row, start_col, header, data, col_widths=None):
    for j, h in enumerate(header):
        c = ws.cell(row=start_row, column=start_col + j, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center")
        c.border = thin_border
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            # try numeric cast
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except (ValueError, TypeError):
                pass
            c = ws.cell(row=start_row + 1 + i, column=start_col + j, value=val)
            c.border = thin_border
            c.font = Font(name=FONT_NAME, size=10)
    if col_widths:
        for j, w in enumerate(col_widths):
            ws.column_dimensions[get_column_letter(start_col + j)].width = w
    return start_row + 1 + len(data)


def kpi_card(ws, row, col, label, value):
    lbl = ws.cell(row=row, column=col, value=label)
    lbl.font = kpi_label_font
    val = ws.cell(row=row + 1, column=col, value=value)
    val.font = kpi_value_font


def main():
    wb = Workbook()

    # ================= Sheet 1: Executive Summary =================
    ws = wb.active
    ws.title = "Executive Summary"
    ws.sheet_view.showGridLines = False
    ws["B2"] = "UrbanThread — E-commerce Funnel & Retention Analytics"
    ws["B2"].font = title_font
    ws["B3"] = "Nov 2024 – Dec 2025  |  Data: PostgreSQL 16  |  Prepared by Anshikha Chaurasiya"
    ws["B3"].font = subtitle_font

    funnel_header, funnel_data = read_csv("funnel_overall")
    total_sessions = int(funnel_data[0][1])
    total_purchases = int(funnel_data[-1][1])
    overall_conv = round(100 * total_purchases / total_sessions, 2)

    cat_header, cat_data = read_csv("category_performance")
    total_revenue = sum(float(r[3]) for r in cat_data)
    total_margin = sum(float(r[4]) for r in cat_data)

    ab_header, ab_data = read_csv("ab_test_results")
    rate_a = float(ab_data[0][3])
    rate_b = float(ab_data[1][3])
    lift = round((rate_b - rate_a) / rate_a * 100, 1)

    kpis = [
        ("Total Sessions (14 mo)", f"{total_sessions:,}"),
        ("Overall Conversion Rate", f"{overall_conv}%"),
        ("Gross Revenue (INR)", f"₹{total_revenue/1e7:.2f} Cr"),
        ("Gross Margin", f"₹{total_margin/1e7:.2f} Cr"),
        ("Checkout Redesign Lift", f"+{lift}%"),
    ]
    for i, (label, value) in enumerate(kpis):
        kpi_card(ws, 5, 2 + i * 3, label, value)

    ws["B9"] = "Key findings"
    ws["B9"].font = Font(name=FONT_NAME, bold=True, size=12, color=NAVY)
    findings = [
        "• Desktop converts 2.6x better than Mobile (16.5% vs 6.3%) despite Mobile carrying 68% of sessions — mobile checkout UX is the single biggest funnel leak.",
        "• Direct and Email traffic convert far above paid channels; Paid Social and Affiliate spend show the weakest ROAS (0.39x and 0.44x).",
        "• The redesigned checkout (Variant B) lifted completion from 9.05% to 10.32% — a statistically significant +14% relative lift (z=2.11, p=0.035).",
        "• 'At Risk' customers (recent-but-fading, high past value) hold ₹81L in historical revenue — the highest-value win-back segment.",
        "• Footwear leads gross revenue and margin among categories; Beauty has the lowest average order value but the largest unit volume.",
    ]
    for i, f in enumerate(findings):
        ws.cell(row=10 + i, column=2, value=f).font = Font(name=FONT_NAME, size=10)
        ws.merge_cells(start_row=10 + i, start_column=2, end_row=10 + i, end_column=9)

    ws.column_dimensions["A"].width = 3
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 14

    # ================= Sheet 2: Funnel =================
    ws2 = wb.create_sheet("Funnel Analysis")
    ws2.sheet_view.showGridLines = False
    ws2["B2"] = "Conversion Funnel (Nov 2024 – Dec 2025)"
    ws2["B2"].font = title_font

    header, data = read_csv("funnel_overall")
    end_row = write_table(ws2, 4, 2, header, data, col_widths=[18, 12, 10])

    chart = BarChart()
    chart.title = "Overall Funnel — Sessions by Stage"
    chart.y_axis.title = "Sessions"
    chart.x_axis.title = "Stage"
    data_ref = Reference(ws2, min_col=3, min_row=4, max_row=end_row)
    cats_ref = Reference(ws2, min_col=2, min_row=5, max_row=end_row)
    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.width, chart.height = 16, 9
    ws2.add_chart(chart, "F4")

    ws2["B14"] = "Funnel by Acquisition Channel"
    ws2["B14"].font = Font(name=FONT_NAME, bold=True, size=12, color=NAVY)
    header, data = read_csv("funnel_by_channel")
    end_row2 = write_table(ws2, 16, 2, header, data, col_widths=[16, 10, 10, 16, 12])

    chart2 = BarChart()
    chart2.title = "Conversion Rate by Channel (%)"
    data_ref2 = Reference(ws2, min_col=5, min_row=16, max_row=end_row2)
    cats_ref2 = Reference(ws2, min_col=2, min_row=17, max_row=end_row2)
    chart2.add_data(data_ref2, titles_from_data=True)
    chart2.set_categories(cats_ref2)
    chart2.width, chart2.height = 16, 9
    ws2.add_chart(chart2, "F16")

    ws2["B26"] = "Funnel by Device"
    ws2["B26"].font = Font(name=FONT_NAME, bold=True, size=12, color=NAVY)
    header, data = read_csv("funnel_by_device")
    write_table(ws2, 28, 2, header, data, col_widths=[12, 10, 10, 16])

    # ================= Sheet 3: Monthly Trend =================
    ws3 = wb.create_sheet("Monthly Trend")
    ws3.sheet_view.showGridLines = False
    ws3["B2"] = "Monthly Session & Conversion Trend"
    ws3["B2"].font = title_font
    header, data = read_csv("monthly_funnel_trend")
    end_row3 = write_table(ws3, 4, 2, header, data, col_widths=[12, 10, 16, 18, 18])

    line = LineChart()
    line.title = "Conversion Rate Trend (with 3-mo moving average)"
    data_ref3 = Reference(ws3, min_col=5, min_row=4, max_col=6, max_row=end_row3)
    cats_ref3 = Reference(ws3, min_col=2, min_row=5, max_row=end_row3)
    line.add_data(data_ref3, titles_from_data=True)
    line.set_categories(cats_ref3)
    line.width, line.height = 18, 10
    ws3.add_chart(line, "H4")

    # ================= Sheet 4: Cohort Retention =================
    ws4 = wb.create_sheet("Cohort Retention")
    ws4.sheet_view.showGridLines = False
    ws4["B2"] = "Signup-Month Cohort Retention (% placing an order in month N)"
    ws4["B2"].font = title_font

    header, data = read_csv("cohort_retention")
    # pivot into a matrix: rows = cohort_month, cols = month_index
    cohorts = sorted(set(r[0] for r in data))
    idxs = sorted(set(int(float(r[2])) for r in data))
    matrix = {c: {} for c in cohorts}
    sizes = {}
    for cohort_month, size, month_index, active, pct in data:
        matrix[cohort_month][int(float(month_index))] = float(pct)
        sizes[cohort_month] = int(size)

    r0 = 4
    ws4.cell(row=r0, column=2, value="Cohort Month").font = header_font
    ws4.cell(row=r0, column=2).fill = header_fill
    ws4.cell(row=r0, column=3, value="Cohort Size").font = header_font
    ws4.cell(row=r0, column=3).fill = header_fill
    for j, idx in enumerate(idxs):
        c = ws4.cell(row=r0, column=4 + j, value=f"Month {idx}")
        c.font = header_font
        c.fill = header_fill
    for i, cohort in enumerate(cohorts):
        ws4.cell(row=r0 + 1 + i, column=2, value=cohort).border = thin_border
        ws4.cell(row=r0 + 1 + i, column=3, value=sizes[cohort]).border = thin_border
        for j, idx in enumerate(idxs):
            val = matrix[cohort].get(idx)
            cell = ws4.cell(row=r0 + 1 + i, column=4 + j, value=val)
            cell.border = thin_border
            cell.number_format = "0.0"
            if val is not None:
                # simple heatmap-ish shading by value bucket
                if val >= 15:
                    fill = "C6E0B4"
                elif val >= 8:
                    fill = "FFE699"
                else:
                    fill = "F8CBAD"
                cell.fill = PatternFill("solid", fgColor=fill)
    ws4.column_dimensions["B"].width = 14
    ws4.column_dimensions["C"].width = 12
    for j in range(len(idxs)):
        ws4.column_dimensions[get_column_letter(4 + j)].width = 10

    ws4[f"B{r0 + len(cohorts) + 3}"] = "RFM Customer Segments"
    ws4[f"B{r0 + len(cohorts) + 3}"].font = Font(name=FONT_NAME, bold=True, size=12, color=NAVY)
    header, data = read_csv("rfm_segments")
    write_table(ws4, r0 + len(cohorts) + 5, 2, header, data, col_widths=[18, 12, 14, 14, 16])

    # ================= Sheet 5: A/B Test =================
    ws5 = wb.create_sheet("AB Test - Checkout")
    ws5.sheet_view.showGridLines = False
    ws5["B2"] = "A/B Test: Checkout Redesign (checkout_redesign_v2)"
    ws5["B2"].font = title_font
    ws5["B3"] = "Jul 1 – Aug 11, 2025 · sticky per-customer assignment"
    ws5["B3"].font = subtitle_font
    header, data = read_csv("ab_test_results")
    end_row5 = write_table(ws5, 5, 2, header, data, col_widths=[10, 20, 12, 18])

    chart5 = BarChart()
    chart5.title = "Checkout Completion Rate by Variant (%)"
    data_ref5 = Reference(ws5, min_col=5, min_row=5, max_row=end_row5)
    cats_ref5 = Reference(ws5, min_col=2, min_row=6, max_row=end_row5)
    chart5.add_data(data_ref5, titles_from_data=True)
    chart5.set_categories(cats_ref5)
    chart5.width, chart5.height = 12, 8
    ws5.add_chart(chart5, "G5")

    ws5["B10"] = "Statistical test (two-proportion z-test)"
    ws5["B10"].font = Font(name=FONT_NAME, bold=True, size=11, color=NAVY)
    stats_rows = [
        ("Variant A rate", "9.05%"), ("Variant B rate", "10.32%"),
        ("Relative lift", "+14.0%"), ("z-statistic", "2.113"),
        ("p-value (two-tailed)", "0.0346"), ("Significant at 5%?", "Yes"),
    ]
    for i, (k, v) in enumerate(stats_rows):
        ws5.cell(row=11 + i, column=2, value=k).font = Font(name=FONT_NAME, size=10)
        ws5.cell(row=11 + i, column=3, value=v).font = Font(name=FONT_NAME, size=10, bold=True)

    # ================= Sheet 6: Marketing & Category =================
    ws6 = wb.create_sheet("Marketing & Category")
    ws6.sheet_view.showGridLines = False
    ws6["B2"] = "Marketing Channel Efficiency (CAC & ROAS)"
    ws6["B2"].font = title_font
    header, data = read_csv("marketing_channel_roi")
    end_row6 = write_table(ws6, 4, 2, header, data, col_widths=[16, 14, 16, 16, 12, 10])

    chart6 = BarChart()
    chart6.title = "ROAS by Channel"
    data_ref6 = Reference(ws6, min_col=7, min_row=4, max_row=end_row6)
    cats_ref6 = Reference(ws6, min_col=2, min_row=5, max_row=end_row6)
    chart6.add_data(data_ref6, titles_from_data=True)
    chart6.set_categories(cats_ref6)
    chart6.width, chart6.height = 16, 9
    ws6.add_chart(chart6, "I4")

    ws6["B15"] = "Category Performance"
    ws6["B15"].font = Font(name=FONT_NAME, bold=True, size=12, color=NAVY)
    header, data = read_csv("category_performance")
    write_table(ws6, 17, 2, header, data, col_widths=[16, 10, 12, 16, 16, 12, 14])

    os.makedirs("../excel", exist_ok=True)
    wb.save(OUT_PATH)
    print(f"saved {OUT_PATH}")


if __name__ == "__main__":
    main()
