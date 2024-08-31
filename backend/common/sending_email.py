import smtplib
import ssl
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Literal, Sequence

from config import get_settings
from jinja2 import Environment, FileSystemLoader

settings = get_settings()
environment = Environment(loader=FileSystemLoader("templates"))  # define templates location
ENCODING = settings.default_encoding


class EmptyMessageException(Exception):
    """
    This exception will be raised if an email message have no any content.
    An email message must have at least plain text as a content.
    """

    _message = "Message have no content. Plain text must be attached at least."

    def __init__(self) -> None:
        self.message = self._message
        super().__init__(self.message)


class EmailSender(ABC):
    """
    Abstract base class that defines the interface for sending an email.
    """

    @abstractmethod
    def send_email(self, send_from: str, to_addrs: Sequence[str] | str, message: MIMEMultipart) -> None:
        """
        Sends an email.

        Args:
            send_from (str): The email address of the sender.
            to_addrs (Sequence[str] | str): A list of recipient email addresses or a single recipient email address.
            message (MIMEMultipart): The email message to be sent.
        """
        raise NotImplementedError


class SMTPEmailSender(EmailSender):
    """
    A class that implements sending an email using the SMTP protocol over SSL.

    This class utilizes the SMTP protocol to send emails securely using the
    `smtplib.SMTP_SSL` class. It handles authentication and ensures the
    communication is encrypted using SSL.

    Attributes:
        port (int): The port number to connect to the SMTP server.
        host (str): The hostname or IP address of the SMTP server.
        username (str): The username used to authenticate with the SMTP server.
        password (str): The password used to authenticate with the SMTP server.
    """

    def __init__(self, port: int, host: str, username: str, password: str) -> None:
        self.port = port
        self.host = host
        self.username = username
        self.password = password

    def send_email(self, send_from: str, to_addrs: Sequence[str] | str, message: MIMEMultipart) -> None:
        """
        Sends an email using the SMTP protocol over SSL.

        This method connects to the SMTP server, logs in using the provided credentials,
        and sends the email to the specified recipients. If the email fails to be delivered
        to any recipient, an `smtplib.SMTPResponseException` is raised.

        Args:
            send_from (str): The email address of the sender.
            to_addrs (Sequence[str] | str): A list of recipient email addresses or a single
                                            recipient email address.
            message (MIMEMultipart): The email message to be sent, formatted as a
                                     `MIMEMultipart` object.

        Raises:
            smtplib.SMTPResponseException: If the email fails to be delivered to any recipient,
                                           this exception is raised with the corresponding SMTP
                                           error code and a message indicating the problematic
                                           email address.
        """
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host=self.host, port=self.port, context=context) as server:
            server.login(user=send_from, password=self.password)

            result: dict[str, tuple[int, bytes]] = server.sendmail(
                to_addrs=to_addrs,
                from_addr=send_from,
                msg=message.as_string(),
            )

        if result:
            code = list(result.values())[0][0]
            msg = list(result.keys())[0]
            raise smtplib.SMTPResponseException(
                code=code,
                msg=f"Check your email `{msg}` for accuracy. "
                f"Probably you made typo mistake or provided wrong address.",
            )


@dataclass(kw_only=True)
class EmailContent:
    """
    Content for email body.
    """

    plain_text: str | bytes | None = None
    html_name: str | bytes | None = None
    file_name: Path | str | None = None
    image_name: Path | str | None = None

    def __bool__(self) -> bool:
        """
        Instance must have one attribute as not None at least to return True.
        """
        return any([self.plain_text, self.html_name, self.file_name, self.image_name])


class EmailWithAttachments:
    """
    Class for creating email with attachments like pictures, pdf documents, archives etc.
    Also with opportunity to add plain text along with HTML document in order to read email
    on devices without capable HTML.
    """

    # available MIME Types
    mime_types = {
        "plain_text": MIMEText,
        "html": MIMEText,
        "file": MIMEApplication,
        "image": MIMEImage,
    }

    def __init__(self, send_from: str, email_sender: EmailSender) -> None:
        self.send_from = send_from
        self.email_sender = email_sender
        self._attachments_data = dict.fromkeys(["file", "plain_text", "html", "image"], None)

    def _create_mimetype_document(
        self,
        doc_type: Literal["plain_text", "html", "file", "image"],
        content: str | bytes,
    ) -> MIMEText | MIMEImage | MIMEApplication:
        """
        Returns MIME `doc_type` document created with `content`.
        """
        if doc_type == "html":
            return self.mime_types[doc_type](_text=content, _subtype="html")

        return self.mime_types[doc_type](content)

    def _read_media_content(self, source: Path | str) -> bytes:
        """
        Reading media content from the given `source`.
        """
        try:
            with open(source, "rb") as file:
                return file.read()
        except FileNotFoundError as e:
            raise e

    def _read_string_content(self, source: str | Path) -> str:
        """
        Reading string content from the given `source`.
        """
        if isinstance(source, str):
            return source

        try:
            with open(source, "r", encoding=ENCODING) as file:
                return file.read()
        except FileNotFoundError as e:
            raise e

    def _read_bytes_content(self, source: bytes) -> str:
        """
        Reading bytes content from the given `source`.
        """
        return source.decode(ENCODING)

    def _compose_message_attachments(self, attachments: EmailContent) -> dict:
        """
        Returns dict with attachment data for email.
        Data in dict are in particular MIME type which depends on their content.
        """
        if not attachments:
            raise EmptyMessageException

        if attachments.plain_text is not None:
            plain_content = (
                self._read_bytes_content(attachments.plain_text)
                if isinstance(attachments.plain_text, bytes)
                else self._read_string_content(attachments.plain_text)  # type: ignore
            )

            document = self._create_mimetype_document("plain_text", plain_content)
            self._attachments_data["plain_text"] = document

        if attachments.html_name is not None:
            html_content = (
                self._read_bytes_content(attachments.html_name)  # type: ignore
                if isinstance(attachments.html_name, bytes)
                else self._read_string_content(attachments.html_name)  # type: ignore
            )
            document = self._create_mimetype_document("html", html_content)
            self._attachments_data["html"] = document

        if attachments.file_name is not None:
            file_content = self._read_media_content(attachments.file_name)
            file = self._create_mimetype_document("file", file_content)
            filename = attachments.file_name.stem if isinstance(attachments.file_name, Path) else attachments.file_name

            # add header as key/value pair to attachment part
            file.add_header(
                "Content-Disposition",
                f"attachment; filename={filename}",
            )
            self._attachments_data["file"] = file

        if attachments.image_name is not None:
            image_content = self._read_media_content(attachments.image_name)
            image = self._create_mimetype_document("image", image_content)
            imagename = (
                attachments.image_name.stem if isinstance(attachments.image_name, Path) else attachments.image_name
            )

            # add header as key/value pair to attachment part
            image.add_header(
                "Content-Disposition",
                f"attachment; filename={imagename}",
            )
            self._attachments_data["image"] = image

        return self._attachments_data

    def render_to_string(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Return the rendered template with the as a string with the provided `context`.
        """
        template = environment.get_template(template_name)
        return template.render(context)

    def _build_message(self, content: EmailContent) -> MIMEMultipart:
        """
        Build message with attachments from the given `content`.
        """
        message = MIMEMultipart("alternative")

        # attach parts to the message
        for att in self._compose_message_attachments(content).values():
            if att is not None:
                message.attach(att)

        return message

    def send_mail(
        self, send_to: Sequence[str] | str, subject: str, content: EmailContent, bcc: Sequence[str] | str | None = None
    ) -> None:
        """
        Send email over SSL.
        - `send_to` - email receivers,
        - `subject` - email subject,
        - `bcc` - blind carbon copy receivers,
        - `content` - `EmailContent` dataclass
        """
        message = self._build_message(content)
        message["Subject"] = subject
        message["From"] = self.send_from
        message["To"] = ", ".join(send_to) if isinstance(send_to, list) else send_to  # type: ignore

        to_addrs = []

        recipients = send_to if isinstance(send_to, (list, tuple)) else [send_to]
        if bcc is not None:
            bcc_recipients = bcc if isinstance(bcc, (list, tuple)) else [bcc]
            to_addrs.extend(bcc_recipients)

        to_addrs.extend(recipients)

        self.email_sender.send_email(self.send_from, to_addrs, message)


smtp_sender = SMTPEmailSender(
    host=settings.email_host,
    port=settings.email_port,
    username=settings.email_from,
    password=settings.email_password,
)

email_sender = EmailWithAttachments(
    settings.email_from,
    smtp_sender,
)
