"""
Aria Automation Engine
======================
Wraps the real certificateautomater scripts into async-safe functions
called by FastAPI endpoints.

Certificate logic adapted from:
  certificateautomater/generate_certificates.py
  certificateautomater/generate_all.py

Email logic adapted from:
  certificateautomater/send_official_certificates.py
  certificateautomater/EmailAutomater1/EmailAutomater/certificate_template.html
"""

import csv
import io
import os
import re
import glob
import smtplib
import asyncio
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from email.message import EmailMessage

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── Directories ────────────────────────────────────────────────────────────────
BACKEND_DIR   = Path(__file__).parent
UPLOADS_DIR   = BACKEND_DIR / "uploads"
OUTPUT_DIR    = BACKEND_DIR / "automation_output"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Known column name aliases (fuzzy detection) ────────────────────────────────
_ALIASES: Dict[str, List[str]] = {
    "name":   ["name", "full name", "full_name", "member name", "participant name",
                "student name", "recipient", "person"],
    "email":  ["email", "email address", "e-mail", "mail", "email id"],
    "team":   ["team", "team name", "group", "group name", "squad", "section"],
    "phone":  ["phone", "mobile", "contact", "phone number", "mobile number"],
    "address":["address", "location", "city", "place"],
    "date":   ["date", "completion date", "completion_date", "event date"],
    "roll":   ["roll", "roll no", "roll_no", "rollno", "enrollment", "reg no"],
    "dept":   ["department", "branch", "dept", "stream"],
}


def _fuzzy_role(col_header: str) -> Optional[str]:
    """Return the semantic role for a CSV column header, or None."""
    h = col_header.strip().lower()
    for role, aliases in _ALIASES.items():
        if any(h == a or h.startswith(a) for a in aliases):
            return role
    return None


def detect_columns(csv_bytes: bytes) -> Dict[str, Any]:
    """
    Parse CSV bytes, detect column roles, return:
      {
        "headers": [...],
        "detected": {"name": "Member Name", "email": "Email", ...},
        "preview": [{...}, ...],   # first 5 rows as dicts
      }
    """
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []

    detected: Dict[str, str] = {}
    for h in headers:
        role = _fuzzy_role(h)
        if role and role not in detected:
            detected[role] = h

    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append(dict(row))

    return {"headers": list(headers), "detected": detected, "preview": rows}


# ── Email helpers ──────────────────────────────────────────────────────────────

def build_default_email_template(detected_cols: Dict[str, str], event_name: str = "our event") -> str:
    """
    Build a sensible HTML email template using detected column names.
    Uses [Participant_Name] / [Team_Name] style placeholders (matching the real scripts).
    """
    name_ph   = "[Participant_Name]"
    team_ph   = "[Team_Name]"   if "team"  in detected_cols else ""
    has_team  = bool(team_ph)

    team_line = (
        f"<p>as a key member of team <strong>{team_ph}</strong>!</p>"
        if has_team else "<p>for your participation!</p>"
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px;
                border: 1px solid #eaeaea; border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #3d405b 100%);
             color: white; padding: 25px; text-align: center;
             border-radius: 10px 10px 0 0; }}
  .content {{ padding: 30px 20px; }}
  .footer {{ text-align: center; font-size: 0.85em; color: #888;
             margin-top: 20px; border-top: 1px solid #eaeaea; padding-top: 15px; }}
  .highlight {{ color: #d4af37; font-weight: 600; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0;">🏆 Congratulations!</h2>
      <p style="margin:8px 0 0; opacity:0.85;">{event_name}</p>
    </div>
    <div class="content">
      <p>Hey <span class="highlight">{name_ph}</span>,</p>
      <p>Thank you for participating in <strong>{event_name}</strong>
      {team_line}
      <p>We are incredibly proud of the energy, innovation, and hard work you brought to the event.
      Please find your <strong>Certificate of Participation</strong> attached.</p>
      <p>Keep innovating and building the future!</p>
      <p>Best regards,<br><strong>The Organizing Team</strong></p>
    </div>
    <div class="footer">
      <p>This is an automated message. Please do not reply directly to this email.</p>
    </div>
  </div>
</body>
</html>"""


async def draft_email_with_gemini(
    detected_cols: Dict[str, str],
    event_name: str,
    tone: str = "professional",
    gemini_client=None,
) -> str:
    """
    Use Gemini to draft a richer HTML email template.
    Falls back to build_default_email_template if Gemini is unavailable.
    """
    if gemini_client is None:
        return build_default_email_template(detected_cols, event_name)

    placeholders = ", ".join(
        f"[{role.title()}]" for role in detected_cols
    )
    prompt = (
        f"Write a {tone} HTML email template for '{event_name}'. "
        f"Available placeholders: {placeholders}. "
        "Use [Participant_Name] for the recipient's name, [Team_Name] for their team. "
        "Include a styled header, body paragraph, and footer. "
        "Return ONLY the full HTML, no markdown."
    )
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
        )
        html = response.text.strip()
        # Strip markdown code fences if Gemini wraps them
        if html.startswith("```"):
            html = re.sub(r"^```[a-z]*\n?", "", html)
            html = re.sub(r"\n?```$", "", html)
        return html
    except Exception as e:
        print(f"[AutoEng] Gemini email draft failed: {e}")
        return build_default_email_template(detected_cols, event_name)


# ── Certificate generation ─────────────────────────────────────────────────────

def _get_safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in (" ", "_")).replace(" ", "_").strip("_")


def _load_font(font_path: Optional[str], size: int):
    """Load font from path, fall back to Windows Times New Roman, then PIL default."""
    candidates = [font_path] if font_path else []
    candidates += [
        "C:\\Windows\\Fonts\\timesbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if p:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_certificate_for_person(
    name: str,
    team_dir: Path,
    font,
    template_img,
    text_x: int,
    text_y: int,
    text_color: tuple = (0, 0, 0),
) -> Path:
    """
    Draw `name` onto a copy of `template_img` at (text_x, text_y) centred,
    save as PDF — mirrors generate_certificates.py exactly.
    """
    img = template_img.copy()
    draw = ImageDraw.Draw(img)

    try:
        bbox = draw.textbbox((0, 0), name, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except AttributeError:
        tw, th = draw.textsize(name, font=font)

    final_x = text_x - (tw / 2)
    final_y = text_y - (th / 2)
    draw.text((final_x, final_y), name, font=font, fill=text_color)

    if img.mode != "RGB":
        img = img.convert("RGB")

    safe_name = _get_safe_filename(name)
    output_path = team_dir / f"{safe_name}_Certificate.pdf"
    img.save(str(output_path), "PDF", resolution=100.0)
    return output_path


async def generate_certificates_batch(
    csv_bytes: bytes,
    template_img_path: str,
    layout: Dict[str, Any],
    output_dir: Optional[str] = None,
    websocket=None,
) -> str:
    """
    Batch-generate PDFs from CSV data + a template image + layout from frontend.

    layout = {
        "text_x": int,       # px X centre of name on image
        "text_y": int,       # px Y centre of name on image
        "font_size": int,
        "font_path": str,    # optional custom font path
        "text_color": [R,G,B],
        "name_col": str,     # CSV column header for name
        "group_col": str,    # CSV column header for team/group (sub-folder)
    }

    Output: output_dir/<GroupName>/<SafeName>_Certificate.pdf
    """
    if not PIL_AVAILABLE:
        return "❌ Pillow not installed."

    out = Path(output_dir) if output_dir else OUTPUT_DIR / "certificates"
    out.mkdir(parents=True, exist_ok=True)

    # Load template
    try:
        template_img = Image.open(template_img_path)
    except Exception as e:
        return f"❌ Cannot open template image: {e}"

    img_w, img_h = template_img.size

    # Layout params — convert ratio coords if frontend sends 0-1 floats
    raw_x = layout.get("text_x", 0.5)
    raw_y = layout.get("text_y", 0.5)
    text_x = int(raw_x * img_w) if isinstance(raw_x, float) and raw_x <= 1 else int(raw_x)
    text_y = int(raw_y * img_h) if isinstance(raw_y, float) and raw_y <= 1 else int(raw_y)

    font_size  = int(layout.get("font_size", 70))
    font_path  = layout.get("font_path", None)
    color_val  = layout.get("text_color", [0, 0, 0])
    text_color = tuple(color_val) if isinstance(color_val, list) else (0, 0, 0)
    name_col   = layout.get("name_col", "Member Name")
    group_col  = layout.get("group_col", "Team Name")

    font = _load_font(font_path, font_size)

    # Parse CSV
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return "❌ CSV is empty."

    total = len(rows)
    generated = 0
    errors: List[str] = []

    if websocket:
        try:
            await websocket.send_json({
                "type": "task_update",
                "task": f"🎓 Generating {total} certificates…"
            })
        except Exception:
            pass

    for i, row in enumerate(rows, 1):
        # Resolve name
        name = (row.get(name_col) or row.get("name") or row.get("Name") or f"Person_{i}").strip().title()
        group = (row.get(group_col) or row.get("Team Name") or row.get("team") or "General").strip()

        team_dir = out / _get_safe_filename(group)
        team_dir.mkdir(parents=True, exist_ok=True)

        try:
            await asyncio.to_thread(
                generate_certificate_for_person,
                name, team_dir, font, template_img,
                text_x, text_y, text_color,
            )
            generated += 1
            if websocket:
                try:
                    await websocket.send_json({
                        "type": "task_update",
                        "task": f"🎓 {generated}/{total}: {name} ({group})"
                    })
                except Exception:
                    pass
        except Exception as e:
            errors.append(f"{name}: {e}")

    summary = f"✅ Generated {generated}/{total} certificates in '{out}'."
    if errors:
        summary += f" ⚠ {len(errors)} errors."
    if websocket:
        try:
            await websocket.send_json({"type": "task_update", "task": summary})
        except Exception:
            pass
    return summary


# ── Email sending ──────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name).lower()


def _find_certificate(base_dir: str, team_name: str, member_name: str) -> Optional[str]:
    """Fuzzy cert finder — adapted from send_official_certificates.py."""
    team_folder = team_name.replace(" ", "_")
    member_file = member_name.replace(" ", "_") + "_Certificate.pdf"
    exact = os.path.join(base_dir, team_folder, member_file)
    if os.path.exists(exact):
        return exact

    norm_team   = _normalize(team_name)
    norm_member = _normalize(member_name)

    for tf in glob.glob(os.path.join(base_dir, "*")):
        if _normalize(os.path.basename(tf)) == norm_team:
            for mf in glob.glob(os.path.join(tf, "*.pdf")):
                if norm_member in _normalize(os.path.basename(mf)):
                    return mf
    return None


def _connect_smtp(sender: str, password: str):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        return server
    except Exception as e:
        raise RuntimeError(f"SMTP login failed: {e}")


async def send_emails_batch(
    csv_bytes: bytes,
    subject: str,
    html_template: str,
    certs_base_dir: Optional[str],
    smtp_cfg: Optional[Dict[str, str]],  # {"sender": ..., "password": ...}
    name_col: str = "Member Name",
    team_col: str = "Team Name",
    email_col: str = "Email",
    websocket=None,
) -> str:
    """
    Send personalised emails with PDF cert attachments.
    If smtp_cfg is None/empty → saves .html files to output/emails/ instead.

    Adapted from send_official_certificates.py.
    """
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        return "❌ CSV is empty."

    total     = len(rows)
    sent      = 0
    saved     = 0
    missing   = []
    failed    = []

    emails_out = OUTPUT_DIR / "emails"
    emails_out.mkdir(parents=True, exist_ok=True)

    use_smtp = bool(smtp_cfg and smtp_cfg.get("sender") and smtp_cfg.get("password"))
    server   = None

    if use_smtp:
        try:
            server = await asyncio.to_thread(
                _connect_smtp, smtp_cfg["sender"], smtp_cfg["password"]
            )
        except Exception as e:
            return f"❌ SMTP connection failed: {e}"

    if websocket:
        try:
            mode = "SMTP" if use_smtp else "file output"
            await websocket.send_json({
                "type": "task_update",
                "task": f"📧 Sending {total} emails via {mode}…"
            })
        except Exception:
            pass

    for i, row in enumerate(rows, 1):
        member = (row.get(name_col) or row.get("name") or f"Person_{i}").strip()
        team   = (row.get(team_col) or row.get("team") or "General").strip()
        email  = (row.get(email_col) or row.get("email") or "").strip()

        if not email or email.upper() == "MISSING":
            missing.append(f"{member} — no email")
            continue

        body = (
            html_template
            .replace("[Participant_Name]", member)
            .replace("[Team_Name]", team)
        )

        if use_smtp:
            pdf_path = None
            if certs_base_dir:
                pdf_path = _find_certificate(certs_base_dir, team, member)

            msg = EmailMessage()
            msg.set_content(body, subtype="html")
            msg["Subject"] = subject
            msg["From"]    = f"ARIA <{smtp_cfg['sender']}>"
            msg["To"]      = email

            if pdf_path:
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_fname = f"Certificate_{member.replace(' ', '_')}.pdf"
                msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename=pdf_fname)

            for attempt in range(3):
                try:
                    await asyncio.to_thread(server.send_message, msg)
                    sent += 1
                    break
                except smtplib.SMTPServerDisconnected:
                    server = await asyncio.to_thread(
                        _connect_smtp, smtp_cfg["sender"], smtp_cfg["password"]
                    )
                except Exception as e:
                    if attempt == 2:
                        failed.append(f"{member} ({email}): {e}")
                    break

            await asyncio.sleep(1.5)  # rate limit
        else:
            # Save as .html file
            safe = _get_safe_filename(member)
            save_path = emails_out / f"{safe}_email.html"
            save_path.write_text(body, encoding="utf-8")
            saved += 1

        if websocket and i % 5 == 0:
            try:
                await websocket.send_json({
                    "type": "task_update",
                    "task": f"📧 Processed {i}/{total} — {member}"
                })
            except Exception:
                pass

    if server:
        try:
            server.quit()
        except Exception:
            pass

    if use_smtp:
        summary = f"✅ Sent {sent}/{total} emails."
    else:
        summary = f"✅ Saved {saved}/{total} email HTML files to '{emails_out}'."
    if missing:
        summary += f" ⚠ {len(missing)} skipped (no email)."
    if failed:
        summary += f" ❌ {len(failed)} failed."

    if websocket:
        try:
            await websocket.send_json({"type": "task_update", "task": summary})
        except Exception:
            pass

    return summary
