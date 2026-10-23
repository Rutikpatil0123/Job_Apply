import os
import time
import email
import imaplib
import logging
from typing import Optional, Dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DEFAULT_RESUME_PATH

logger = logging.getLogger("gmail_drafter")

class GmailDrafter:
    def __init__(
        self,
        email_address: str = GMAIL_ADDRESS,
        app_password: str = GMAIL_APP_PASSWORD,
    ):
        self.email_address = email_address
        self.app_password = app_password.replace(" ", "") if app_password else ""

    def is_configured(self) -> bool:
        """Check if Gmail credentials are provided."""
        return bool(self.email_address and self.app_password)

    def _find_drafts_mailbox(self, mail: imaplib.IMAP4_SSL) -> str:
        """Detect the localized Drafts folder name in Gmail (default: [Gmail]/Drafts)."""
        try:
            status, folder_list = mail.list()
            if status == "OK" and folder_list:
                for f in folder_list:
                    folder_str = f.decode("utf-8", errors="ignore") if isinstance(f, bytes) else str(f)
                    if "\\Drafts" in folder_str:
                        # Extract folder name in quotes or last token
                        parts = folder_str.split(' "/" ')
                        if len(parts) > 1:
                            return parts[1].strip().strip('"')
        except Exception as e:
            logger.debug(f"Could not list folders to detect Drafts folder: {e}")

        return "[Gmail]/Drafts"

    def create_mime_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        resume_path: Optional[str] = None,
    ) -> MIMEMultipart:
        """Assemble standard MIME email message with optional resume attachment."""
        msg = MIMEMultipart()
        msg["From"] = self.email_address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="gmail.com")

        # Attach email body
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Attach resume PDF if present
        actual_resume = resume_path or DEFAULT_RESUME_PATH
        if actual_resume and os.path.exists(actual_resume):
            try:
                with open(actual_resume, "rb") as f:
                    part = MIMEBase("application", "pdf")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(actual_resume)
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    msg.attach(part)
                logger.info(f"Attached resume: '{actual_resume}'")
            except Exception as e:
                logger.warning(f"Could not attach resume file '{actual_resume}': {e}")

        return msg

    def save_draft(
        self,
        to_email: str,
        subject: str,
        body: str,
        resume_path: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Connect to Gmail via IMAP and append message to Drafts.
        Returns result dict with status and message details.
        """
        if not self.is_configured():
            return {
                "status": "error",
                "message": (
                    "Gmail credentials not configured. Please set GMAIL_ADDRESS and "
                    "GMAIL_APP_PASSWORD in .env (get a 16-char code at myaccount.google.com/apppasswords)."
                ),
            }

        msg = self.create_mime_message(
            to_email=to_email,
            subject=subject,
            body=body,
            resume_path=resume_path,
        )

        try:
            logger.info(f"Connecting to imap.gmail.com for {self.email_address}...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(self.email_address, self.app_password)

            drafts_box = self._find_drafts_mailbox(mail)
            logger.info(f"Appending draft to mailbox: '{drafts_box}'...")

            # Append with \Draft flag and current internal date
            now = time.time()
            internal_date = imaplib.Time2Internaldate(now)
            status, response = mail.append(drafts_box, "\\Draft", internal_date, msg.as_bytes())

            mail.logout()

            if status == "OK":
                return {
                    "status": "success",
                    "to": to_email,
                    "subject": subject,
                    "folder": drafts_box,
                    "message": f"Draft saved successfully to Gmail '{drafts_box}'!",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Gmail IMAP returned status {status}: {response}",
                }

        except imaplib.IMAP4.error as e:
            err_msg = str(e)
            if "AUTHENTICATIONFAILED" in err_msg:
                return {
                    "status": "error",
                    "message": "Gmail authentication failed. Please verify your 16-character Google App Password in .env.",
                }
            return {"status": "error", "message": f"IMAP error: {err_msg}"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error while saving draft: {e}"}
