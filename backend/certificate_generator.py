"""
Certificate Generation Module for ARIA OS Agent
================================================
Generates batch certificates using PIL + CSV data.

Usage (from agent_tools or main):
    from certificate_generator import generate_certificates_from_csv, generate_single_certificate

    result = await generate_certificates_from_csv(
        csv_path="participants.csv",
        template_path="templates/cert_template.png",
        output_dir="certificates",
        websocket=ws,
    )
"""

import csv
import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── Default paths ──────────────────────────────────────────────────────────────
BACKEND_DIR      = Path(__file__).parent
CERTIFICATES_DIR = BACKEND_DIR / "certificates"
TEMPLATES_DIR    = BACKEND_DIR / "templates"
FINDINGS_DIR     = BACKEND_DIR / "findings"

# ── Layout constants (relative to template size) ───────────────────────────────
# These work for a standard A4-landscape certificate (1123×794 px @ 96dpi)
DEFAULT_LAYOUT = {
    "name":        {"y_ratio": 0.50, "font_size": 68, "color": "#1a1a2e",   "bold": True},
    "course_name": {"y_ratio": 0.61, "font_size": 34, "color": "#3d405b",   "bold": False},
    "date":        {"y_ratio": 0.72, "font_size": 28, "color": "#555555",   "bold": False},
    "extra_line":  {"y_ratio": 0.79, "font_size": 24, "color": "#777777",   "bold": False},
}


def _load_font(size: int, bold: bool = False):
    """Load a font — tries system fonts, falls back to PIL default."""
    font_candidates = []
    if bold:
        font_candidates = [
            "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
            "LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        font_candidates = [
            "arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
            "LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            continue
    # PIL default bitmap font — always works, but small
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str):
    """Convert #RRGGBB to (R, G, B)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _create_blank_template(width: int = 1123, height: int = 794) -> Image.Image:
    """Create a clean gradient template when no PNG template is provided."""
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(height):
        ratio = y / height
        r = int(240 + (200 - 240) * ratio)
        g = int(244 + (220 - 244) * ratio)
        b = int(255 + (240 - 255) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Decorative border
    border_color = "#1a1a2e"
    draw.rectangle([20, 20, width - 20, height - 20], outline=border_color, width=4)
    draw.rectangle([30, 30, width - 30, height - 30], outline="#3d405b", width=2)

    # Header banner
    draw.rectangle([20, 20, width - 20, 120], fill="#1a1a2e")

    # ARIA branding in header
    header_font = _load_font(36, bold=True)
    draw.text((width // 2, 70), "ARIA OS — Certificate of Completion",
              fill="#ffffff", font=header_font, anchor="mm")

    # "Certificate of Appreciation" subtitle
    sub_font = _load_font(28, bold=False)
    draw.text((width // 2, 155), "This certificate is proudly presented to",
              fill="#555555", font=sub_font, anchor="mm")

    # Divider lines
    draw.line([(80, 200), (width - 80, 200)], fill="#d4af37", width=3)
    draw.line([(80, 540), (width - 80, 540)], fill="#d4af37", width=2)

    return img


def generate_single_certificate(
    name: str,
    course_name: str,
    output_path: Path,
    template_path: Optional[Path] = None,
    date_str: Optional[str] = None,
    extra_line: str = "",
    layout: Optional[dict] = None,
) -> Path:
    """
    Generate a single certificate PNG.

    Args:
        name:          Recipient name (goes in big text)
        course_name:   Name of the course/event/hackathon
        output_path:   Where to save the PNG
        template_path: Optional background template image
        date_str:      Date string (defaults to today)
        extra_line:    Optional 4th line (e.g. college, roll number)
        layout:        Override DEFAULT_LAYOUT dict

    Returns:
        Path to generated certificate
    """
    if not PIL_AVAILABLE:
        raise ImportError("Pillow not installed. Run: pip install Pillow")

    if date_str is None:
        date_str = datetime.now().strftime("%B %d, %Y")

    layout = layout or DEFAULT_LAYOUT

    # Load or create template
    if template_path and Path(template_path).exists():
        img = Image.open(template_path).convert("RGB")
    else:
        img = _create_blank_template()

    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Draw name
    name_cfg = layout.get("name", {})
    name_font = _load_font(name_cfg.get("font_size", 68), bold=name_cfg.get("bold", True))
    name_y = int(height * name_cfg.get("y_ratio", 0.50))
    name_color = _hex_to_rgb(name_cfg.get("color", "#1a1a2e"))
    draw.text((width // 2, name_y), name, fill=name_color, font=name_font, anchor="mm")

    # Draw course name
    course_cfg = layout.get("course_name", {})
    course_font = _load_font(course_cfg.get("font_size", 34), bold=course_cfg.get("bold", False))
    course_y = int(height * course_cfg.get("y_ratio", 0.61))
    course_color = _hex_to_rgb(course_cfg.get("color", "#3d405b"))
    draw.text((width // 2, course_y), f"for successfully completing: {course_name}",
              fill=course_color, font=course_font, anchor="mm")

    # Draw date
    date_cfg = layout.get("date", {})
    date_font = _load_font(date_cfg.get("font_size", 28), bold=date_cfg.get("bold", False))
    date_y = int(height * date_cfg.get("y_ratio", 0.72))
    date_color = _hex_to_rgb(date_cfg.get("color", "#555555"))
    draw.text((width // 2, date_y), f"Date: {date_str}",
              fill=date_color, font=date_font, anchor="mm")

    # Draw extra line (college, roll no, etc.)
    if extra_line:
        extra_cfg = layout.get("extra_line", {})
        extra_font = _load_font(extra_cfg.get("font_size", 24), bold=extra_cfg.get("bold", False))
        extra_y = int(height * extra_cfg.get("y_ratio", 0.79))
        extra_color = _hex_to_rgb(extra_cfg.get("color", "#777777"))
        draw.text((width // 2, extra_y), extra_line,
                  fill=extra_color, font=extra_font, anchor="mm")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG", optimize=True)
    return output_path


async def generate_certificates_from_csv(
    csv_path: str,
    course_name: str = "ARIA Hackathon",
    template_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    websocket=None,
) -> str:
    """
    Batch-generate certificates from a CSV file.

    CSV columns supported (case-insensitive):
        name, email, college, roll_no / rollno, department

    Args:
        csv_path:      Path to CSV file
        course_name:   Name of the event/hackathon for the certificate
        template_path: Optional background image path
        output_dir:    Where to save output PNGs (default: backend/certificates)
        websocket:     WebSocket to send progress updates

    Returns:
        Summary string
    """
    # ── Setup paths ─────────────────────────────────────────────────────────────
    csv_file   = Path(csv_path)
    tmpl_path  = Path(template_path) if template_path else None
    out_dir    = Path(output_dir) if output_dir else CERTIFICATES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_file.exists():
        msg = f"CSV file not found: {csv_path}"
        if websocket:
            try:
                await websocket.send_json({"type": "task_update", "task": f"❌ {msg}"})
            except Exception:
                pass
        return msg

    # ── Read CSV ────────────────────────────────────────────────────────────────
    participants: List[Dict] = []
    try:
        with open(csv_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys to lowercase
                participants.append({k.strip().lower(): v.strip() for k, v in row.items()})
    except Exception as e:
        return f"Failed to read CSV: {e}"

    if not participants:
        return "CSV file is empty — no certificates generated."

    total = len(participants)
    generated = 0
    errors = []

    if websocket:
        try:
            await websocket.send_json({"type": "task_update", "task": f"🎓 Generating {total} certificates for '{course_name}'..."})
        except Exception:
            pass

    # ── Generate each certificate ───────────────────────────────────────────────
    for i, person in enumerate(participants, 1):
        # Try common name column variations
        name = (
            person.get("name")
            or person.get("full name")
            or person.get("full_name")
            or person.get("participant name")
            or person.get("student name")
            or f"Participant_{i}"
        ).strip()

        college  = person.get("college", person.get("institution", ""))
        roll_no  = person.get("roll_no", person.get("rollno", person.get("roll no", "")))
        dept     = person.get("department", person.get("branch", ""))
        date_str = person.get("date", person.get("completion_date", None))

        extra_parts = [x for x in [college, dept, roll_no] if x]
        extra_line  = " | ".join(extra_parts) if extra_parts else ""

        # Safe filename
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        safe_name = safe_name.replace(" ", "_")
        output_path = out_dir / f"certificate_{i:03d}_{safe_name}.png"

        try:
            await asyncio.to_thread(
                generate_single_certificate,
                name=name,
                course_name=course_name,
                output_path=output_path,
                template_path=tmpl_path,
                date_str=date_str,
                extra_line=extra_line,
            )
            generated += 1

            if websocket:
                try:
                    await websocket.send_json({
                        "type": "task_update",
                        "task": f"🎓 Generated {generated}/{total}: {name}"
                    })
                except Exception:
                    pass

        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"[CertGen] Error for {name}: {e}")

    # ── Write summary to findings ────────────────────────────────────────────────
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary_md = f"""# 🎓 Certificate Generation Report

**Event:** {course_name}
**Generated:** {timestamp}
**Total Participants:** {total}
**Successfully Generated:** {generated}
**Output Folder:** `{out_dir}`

## Generated Certificates
"""
    for i, p in enumerate(participants[:generated], 1):
        name = p.get("name", p.get("full_name", f"Participant_{i}"))
        summary_md += f"- ✅ {name}\n"

    if errors:
        summary_md += "\n## ❌ Errors\n"
        for err in errors:
            summary_md += f"- {err}\n"

    summary_file = FINDINGS_DIR / "certificates_generated.md"
    summary_file.write_text(summary_md, encoding="utf-8")

    final_msg = f"✅ Generated {generated}/{total} certificates in '{out_dir}'. Report saved."
    if websocket:
        try:
            await websocket.send_json({"type": "task_update", "task": final_msg})
        except Exception:
            pass

    return final_msg