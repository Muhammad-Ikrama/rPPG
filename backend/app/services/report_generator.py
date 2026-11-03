"""
Biomedical Measurement Report Generator (PDF and CSV).

Outputs structured reports conforming to scientific documentation standards.
Explicitly separates algorithm estimates from measured reference values and
includes statutory research disclaimers.
"""

from typing import Dict, Any, Optional
import os
import io
import csv
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings


class ReportGenerator:

    @staticmethod
    def generate_csv_report(data: Dict[str, Any]) -> str:
        """
        Generates CSV format measurement report string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["=== rPPG VITAL SIGNS MONITORING SYSTEM MEASUREMENT REPORT ==="])
        writer.writerow(["Generated At", datetime.utcnow().isoformat()])
        writer.writerow(["Session ID", data.get("session_id")])
        writer.writerow(["Participant Pseudonym", data.get("pseudonym_id", "N/A")])
        writer.writerow(["Algorithm Version", data.get("algorithm_version", "POS-v1.0.0")])
        writer.writerow([])

        writer.writerow(["--- VIDEO ACQUISITION METADATA ---"])
        writer.writerow(["Camera Type", data.get("camera_type")])
        writer.writerow(["Resolution", data.get("resolution")])
        writer.writerow(["Frame Rate (FPS)", data.get("fps")])
        writer.writerow(["Duration (seconds)", data.get("duration_sec")])
        writer.writerow(["Total Frames", data.get("total_frames")])
        writer.writerow(["Dropped Frames", data.get("dropped_frames")])
        writer.writerow([])

        writer.writerow(["--- ESTIMATED PHYSIOLOGICAL PARAMETERS ---"])
        writer.writerow(["Parameter", "Estimated Value", "Unit", "Confidence (0-1)", "Status", "Uncertainty / Notes"])
        writer.writerow([
            "Heart Rate (HR)",
            data.get("hr_bpm", "N/A"),
            "BPM",
            data.get("hr_confidence", "N/A"),
            data.get("hr_status", "N/A"),
            f"SNR: {data.get('snr_db')} dB",
        ])
        writer.writerow([
            "Respiratory Rate (RR)",
            data.get("rr_brpm", "N/A"),
            "BrPM",
            data.get("rr_confidence", "N/A"),
            data.get("rr_status", "N/A"),
            "Modulation: RBM/RAM",
        ])
        writer.writerow([
            "Oxygen Saturation (SpO2)",
            data.get("spo2_percent", "N/A"),
            "%",
            data.get("spo2_confidence", "N/A"),
            data.get("spo2_status", "N/A"),
            "Experimental / Uncalibrated Optical RoR",
        ])
        writer.writerow([
            "Systolic Blood Pressure (SBP)",
            data.get("sbp_mmhg", "N/A"),
            "mmHg",
            data.get("bp_confidence", "N/A"),
            data.get("bp_status", "N/A"),
            "Experimental Research Index",
        ])
        writer.writerow([
            "Diastolic Blood Pressure (DBP)",
            data.get("dbp_mmhg", "N/A"),
            "mmHg",
            data.get("bp_confidence", "N/A"),
            data.get("bp_status", "N/A"),
            "Experimental Research Index",
        ])
        writer.writerow([])

        writer.writerow(["--- SIGNAL QUALITY & STABILITY ASSESSMENT ---"])
        writer.writerow(["Composite Signal Quality Index (SQI)", data.get("sqi_score", "N/A")])
        writer.writerow(["SQI Status", data.get("sqi_status", "N/A")])
        writer.writerow(["Motion Stability", data.get("motion_stability", "N/A")])
        writer.writerow(["Illumination Stability", data.get("illumination_stability", "N/A")])
        writer.writerow(["Guidance", data.get("quality_guidance", "N/A")])
        writer.writerow([])

        writer.writerow(["--- PAIRED REFERENCE GROUND TRUTH (IF AVAILABLE) ---"])
        writer.writerow(["Reference HR (BPM)", data.get("reference_hr", "Not Provided")])
        writer.writerow(["Reference RR (BrPM)", data.get("reference_rr", "Not Provided")])
        writer.writerow(["Reference SpO2 (%)", data.get("reference_spo2", "Not Provided")])
        writer.writerow(["Reference SBP (mmHg)", data.get("reference_sbp", "Not Provided")])
        writer.writerow(["Reference DBP (mmHg)", data.get("reference_dbp", "Not Provided")])
        writer.writerow([])

        writer.writerow(["--- SCIENTIFIC RESEARCH LIMITATIONS ---"])
        writer.writerow([
            "DISCLAIMER",
            "This software is a research engineering prototype for non-contact vital sign estimation. "
            "It is not cleared by medical regulatory bodies (FDA, CE-MDR) for medical diagnosis. "
            "Blood pressure and SpO2 estimations are experimental research modules subject to optical and sensor limitations.",
        ])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(data: Dict[str, Any], output_path: str) -> str:
        """
        Generates a publication-grade biomedical PDF report using ReportLab.
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0B192C")
        secondary_color = colors.HexColor("#1E3E62")
        teal_accent = colors.HexColor("#00ADB5")
        text_dark = colors.HexColor("#222831")

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=primary_color,
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "SubTitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
        )
        section_style = ParagraphStyle(
            "SectionStyle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=secondary_color,
            fontName="Helvetica-Bold",
        )
        cell_style = ParagraphStyle(
            "CellStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            textColor=text_dark,
        )
        bold_cell_style = ParagraphStyle(
            "BoldCellStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            fontName="Helvetica-Bold",
            textColor=text_dark,
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#718096"),
            fontName="Helvetica-Oblique",
        )

        elements = []

        # Header Title
        elements.append(Paragraph("rPPG VITAL SIGNS MONITORING SYSTEM", title_style))
        elements.append(Paragraph("Biomedical Signal Processing & Validation Report", subtitle_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=2, color=teal_accent, spaceBefore=4, spaceAfter=12))

        # Metadata Table
        meta_data = [
            [
                Paragraph("<b>Session ID:</b>", bold_cell_style),
                Paragraph(str(data.get("session_id", "N/A")), cell_style),
                Paragraph("<b>Date / Time:</b>", bold_cell_style),
                Paragraph(str(data.get("timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))), cell_style),
            ],
            [
                Paragraph("<b>Subject Pseudonym:</b>", bold_cell_style),
                Paragraph(str(data.get("pseudonym_id", "SUBJ-ANONYMOUS")), cell_style),
                Paragraph("<b>Algorithm Engine:</b>", bold_cell_style),
                Paragraph(str(data.get("algorithm_version", "POS-v1.0.0 (Wang et al. 2017)")), cell_style),
            ],
            [
                Paragraph("<b>Camera Sensor:</b>", bold_cell_style),
                Paragraph(f"{data.get('camera_type', 'Webcam')} ({data.get('resolution', '720p')})", cell_style),
                Paragraph("<b>Duration / FPS:</b>", bold_cell_style),
                Paragraph(f"{data.get('duration_sec', 0.0):.1f}s @ {data.get('fps', 30.0):.1f} FPS", cell_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # Primary Measurements Table
        elements.append(Paragraph("Physiological Estimations", section_style))
        elements.append(Spacer(1, 6))

        vitals_headers = [
            Paragraph("<b>Parameter</b>", bold_cell_style),
            Paragraph("<b>Algorithm Estimate</b>", bold_cell_style),
            Paragraph("<b>Confidence</b>", bold_cell_style),
            Paragraph("<b>Signal Status</b>", bold_cell_style),
            Paragraph("<b>Reference Ground Truth</b>", bold_cell_style),
        ]

        def fmt_val(v, unit):
            return f"{v:.1f} {unit}" if v is not None else "UNAVAILABLE"

        vitals_rows = [
            vitals_headers,
            [
                Paragraph("<b>Heart Rate (HR)</b>", cell_style),
                Paragraph(fmt_val(data.get("hr_bpm"), "BPM"), bold_cell_style),
                Paragraph(f"{data.get('hr_confidence', 0.0):.0%}", cell_style),
                Paragraph(str(data.get("hr_status", "N/A")), cell_style),
                Paragraph(fmt_val(data.get("reference_hr"), "BPM") if data.get("reference_hr") else "Not Recorded", cell_style),
            ],
            [
                Paragraph("<b>Respiratory Rate (RR)</b>", cell_style),
                Paragraph(fmt_val(data.get("rr_brpm"), "BrPM"), bold_cell_style),
                Paragraph(f"{data.get('rr_confidence', 0.0):.0%}", cell_style),
                Paragraph(str(data.get("rr_status", "N/A")), cell_style),
                Paragraph(fmt_val(data.get("reference_rr"), "BrPM") if data.get("reference_rr") else "Not Recorded", cell_style),
            ],
            [
                Paragraph("<b>SpO2 Saturation (Research)</b>", cell_style),
                Paragraph(fmt_val(data.get("spo2_percent"), "%"), bold_cell_style),
                Paragraph(f"{data.get('spo2_confidence', 0.0):.0%}", cell_style),
                Paragraph(str(data.get("spo2_status", "EXPERIMENTAL")), cell_style),
                Paragraph(fmt_val(data.get("reference_spo2"), "%") if data.get("reference_spo2") else "Not Recorded", cell_style),
            ],
            [
                Paragraph("<b>Systolic Blood Pressure (SBP)*</b>", cell_style),
                Paragraph(fmt_val(data.get("sbp_mmhg"), "mmHg"), bold_cell_style),
                Paragraph(f"{data.get('bp_confidence', 0.0):.0%}", cell_style),
                Paragraph(str(data.get("bp_status", "EXPERIMENTAL")), cell_style),
                Paragraph(fmt_val(data.get("reference_sbp"), "mmHg") if data.get("reference_sbp") else "Not Recorded", cell_style),
            ],
            [
                Paragraph("<b>Diastolic Blood Pressure (DBP)*</b>", cell_style),
                Paragraph(fmt_val(data.get("dbp_mmhg"), "mmHg"), bold_cell_style),
                Paragraph(f"{data.get('bp_confidence', 0.0):.0%}", cell_style),
                Paragraph(str(data.get("bp_status", "EXPERIMENTAL")), cell_style),
                Paragraph(fmt_val(data.get("reference_dbp"), "mmHg") if data.get("reference_dbp") else "Not Recorded", cell_style),
            ],
        ]

        vitals_table = Table(vitals_rows, colWidths=[140, 110, 80, 100, 110])
        vitals_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B192C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(vitals_table)
        elements.append(Spacer(1, 14))

        # Signal Quality Section
        elements.append(Paragraph("Signal Quality and Optical Validation", section_style))
        elements.append(Spacer(1, 6))

        sqi_data = [
            [
                Paragraph("<b>Overall SQI Score:</b>", bold_cell_style),
                Paragraph(f"{data.get('sqi_score', 0.0):.2f} / 1.00 ({data.get('sqi_status', 'N/A')})", cell_style),
                Paragraph("<b>Cardiac SNR:</b>", bold_cell_style),
                Paragraph(f"{data.get('snr_db', -99.0):.1f} dB", cell_style),
            ],
            [
                Paragraph("<b>Motion Stability:</b>", bold_cell_style),
                Paragraph(f"{data.get('motion_stability', 0.0):.2f} / 1.00", cell_style),
                Paragraph("<b>Illumination Stability:</b>", bold_cell_style),
                Paragraph(f"{data.get('illumination_stability', 0.0):.2f} / 1.00", cell_style),
            ],
        ]
        sqi_table = Table(sqi_data, colWidths=[120, 150, 120, 150])
        sqi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(sqi_table)
        elements.append(Spacer(1, 16))

        # Research Disclaimers & Ethics
        elements.append(Paragraph("Scientific and Ethical Disclaimers", section_style))
        elements.append(Spacer(1, 4))
        disclaimer_text = (
            "1. <b>Research Prototype Only:</b> This report was generated by an experimental research system. "
            "It is NOT a medical device and must NOT be used for clinical diagnosis or treatment decisions.<br/>"
            "2. <b>Blood Pressure & SpO2 Limitations:</b> Video-based Blood Pressure (*SBP/DBP) and SpO2 are experimental research objectives. "
            "Ambient illumination and camera Bayer filters do not replicate clinical dual-wavelength pulse oximetry or arterial pressure lines. "
            "Estimates require individual reference cuff calibration to establish quantitative clinical validity under ISO 81060-2.<br/>"
            "3. <b>Privacy & Consent:</b> Video processing is performed under anonymized research protocol SUBJ-ID. No facial imagery is shared with third parties."
        )
        elements.append(Paragraph(disclaimer_text, disclaimer_style))

        doc.build(elements)
        return output_path
