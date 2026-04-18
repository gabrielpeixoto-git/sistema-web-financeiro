from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from financas_app.app.settings import get_settings


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, html: str, text: str) -> bool: ...


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        from_addr: str,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr
        self.use_tls = use_tls

    def send(self, *, to: str, subject: str, html: str, text: str) -> bool:
        if not self.host or not self.user:
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = to
            msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(self.host, self.port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_addr, [to], msg.as_string())
            return True
        except Exception:
            return False


class ConsoleEmailSender:
    """Dev fallback: prints to console instead of sending."""

    def send(self, *, to: str, subject: str, html: str, text: str) -> bool:
        print("=" * 60)
        print(f"EMAIL TO: {to}")
        print(f"SUBJECT: {subject}")
        print("-" * 60)
        print(text)
        print("=" * 60)
        return True


def get_sender() -> EmailSender:
    s = get_settings()
    if s.smtp_host and s.smtp_user:
        return SmtpEmailSender(
            host=s.smtp_host,
            port=s.smtp_port,
            user=s.smtp_user,
            password=s.smtp_password,
            from_addr=s.smtp_from or s.smtp_user,
            use_tls=s.smtp_tls,
        )
    return ConsoleEmailSender()


def build_reminder_email(
    *,
    user_name: str,
    items: list[dict],
    app_name: str = "Finanças App",
) -> tuple[str, str]:
    """Build (text, html) reminder email content."""
    count = len(items)
    subject = f"Lembrete: {count} conta(s) a pagar/vencer em breve"

    # Plain text version
    lines = [f"Olá {user_name},", ""]
    lines.append(f"Você tem {count} conta(s) a pagar nos próximos dias:")
    lines.append("")
    for item in items:
        due = item.get("due_date", "")
        desc = item.get("description", "")
        amount = item.get("amount", "")
        acc = item.get("account", "")
        lines.append(f"- {due}: {desc} ({amount}) - Conta: {acc}")
    lines.append("")
    lines.append(f"Acesse o {app_name} para mais detalhes.")
    text = "\n".join(lines)

    # HTML version
    rows = []
    for item in items:
        due = item.get("due_date", "")
        desc = item.get("description", "")
        amount = item.get("amount", "")
        acc = item.get("account", "")
        rows.append(
            f"<tr style='border-bottom:1px solid #334155;'>"
            f"<td style='padding:8px;color:#F1F5F9;'>{due}</td>"
            f"<td style='padding:8px;color:#F1F5F9;'>{desc}</td>"
            f"<td style='padding:8px;color:#F59E0B;font-weight:600;'>{amount}</td>"
            f"<td style='padding:8px;color:#94A3B8;'>{acc}</td>"
            f"</tr>"
        )

    html = f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#0F172A;font-family:Inter,system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr>
      <td align="center" style="padding:20px 0;">
        <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#1E293B;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:24px;border-bottom:1px solid #334155;">
              <h2 style="margin:0;color:#3B82F6;font-size:20px;">{app_name}</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:24px;">
              <p style="margin:0 0 16px;color:#F1F5F9;font-size:16px;">Olá <strong>{user_name}</strong>,</p>
              <p style="margin:0 0 16px;color:#94A3B8;font-size:14px;">
                Você tem <strong style="color:#EF4444;">{count}</strong> conta(s) a pagar nos próximos dias:
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0F172A;border-radius:8px;overflow:hidden;margin-top:12px;">
                <thead>
                  <tr style="background:#334155;">
                    <th style="padding:10px 8px;text-align:left;color:#94A3B8;font-size:12px;font-weight:600;">VENCIMENTO</th>
                    <th style="padding:10px 8px;text-align:left;color:#94A3B8;font-size:12px;font-weight:600;">DESCRIÇÃO</th>
                    <th style="padding:10px 8px;text-align:left;color:#94A3B8;font-size:12px;font-weight:600;">VALOR</th>
                    <th style="padding:10px 8px;text-align:left;color:#94A3B8;font-size:12px;font-weight:600;">CONTA</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(rows)}
                </tbody>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:24px;border-top:1px solid #334155;">
              <p style="margin:0;color:#64748B;font-size:12px;">
                Acesse o <a href="#" style="color:#3B82F6;text-decoration:none;">{app_name}</a> para mais detalhes.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return text, html
