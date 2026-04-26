import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client as TwilioClient

class NotificationEngine:
    def __init__(self):
        self.sg_api_key = os.getenv('SENDGRID_API_KEY')
        self.sg_from_email = os.getenv('SENDGRID_DEFAULT_FROM', 'service@ziffcode.com.ng')
        
        self.twilio_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_whatsapp_from = os.getenv('TWILIO_WHATSAPP_NUMBER', '+14155238886')

    def send_email(self, to_email, subject, content):
        if not self.sg_api_key:
            print("SendGrid API Key missing. Skipping email.")
            return False
            
        message = Mail(
            from_email=self.sg_from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content)
        try:
            sg = SendGridAPIClient(self.sg_api_key)
            response = sg.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"SendGrid Error: {str(e)}")
            return False

    def send_whatsapp(self, to_number, body):
        if not all([self.twilio_sid, self.twilio_auth_token]):
            print("Twilio Credentials missing. Skipping WhatsApp.")
            return False
            
        try:
            client = TwilioClient(self.twilio_sid, self.twilio_auth_token)
            # Twilio WhatsApp requires 'whatsapp:' prefix
            formatted_to = f"whatsapp:{to_number}" if not to_number.startswith('whatsapp:') else to_number
            formatted_from = f"whatsapp:{self.twilio_whatsapp_from}" if not self.twilio_whatsapp_from.startswith('whatsapp:') else self.twilio_whatsapp_from
            
            message = client.messages.create(
                body=body,
                from_=formatted_from,
                to=formatted_to
            )
            return message.sid is not None
        except Exception as e:
            print(f"Twilio Error: {str(e)}")
            return False

# Global instance
notification_engine = NotificationEngine()
