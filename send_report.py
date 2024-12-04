# reporting/send_report.py
from reporting.email_sender import EmailSender
from config.settings import Config
import asyncio


async def main():
    try:
        print("Starting email report sender...")
        print(f"Recipient email: {Config.RECIPIENT_EMAIL}")

        sender = EmailSender()
        success = await sender.send_analysis_report()

        if success:
            print("Email report sent successfully")
        else:
            print("Failed to send email report")

    except Exception as e:
        print(f"Error in send_report: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
