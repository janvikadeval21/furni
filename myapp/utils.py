from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
 

def send_email(subject, to_email, template_name, context=None, attachments=None):
    if context is None:
        context = {}

    html_content = render_to_string(template_name, context)

    email = EmailMultiAlternatives(
        subject=subject,
        body="Please open this email in an HTML-supported email client.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    email.attach_alternative(html_content, "text/html")

    # Attach any files (format: [(filename, content, mimetype)])
    if attachments:
        for filename, content, mimetype in attachments:
            email.attach(filename, content, mimetype)

    email.send(fail_silently=False)
    return True

from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

def generate_pdf_bytes(template_src, context_dict):
    """Renders HTML template into raw PDF bytes."""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None