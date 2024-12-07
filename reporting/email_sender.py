# reporting/email_sender.py
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import Config
import re
import markdown2
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer, PythonLexer
import pygments


class EmailSender:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.sender_email = Config.SENDER_EMAIL
        self.sender_password = Config.SENDER_PASSWORD
        self.recipient_email = Config.RECIPIENT_EMAIL

        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            raise ValueError("Missing required email configuration in settings")

    def _get_latest_analysis(self):
        """데이터베이스에서 최신 분석 결과를 가져옵니다."""
        conn = sqlite3.connect(Config.DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT analysis, created_at 
                FROM analysis_results 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result if result else (None, None)
        finally:
            conn.close()

    def _highlight_code(self, code: str, language: str) -> str:
        """코드 구문 강조를 적용합니다."""
        try:
            try:
                lexer = get_lexer_by_name(language)
            except pygments.util.ClassNotFound:
                # 언어 인식 실패 시 추측
                try:
                    lexer = guess_lexer(code)
                except pygments.util.ClassNotFound:
                    lexer = PythonLexer()

            formatter = HtmlFormatter(noclasses=True, style="monokai", nowrap=False, inline_css=True)
            return highlight(code, lexer, formatter)
        except Exception as e:
            print(f"코드 강조 처리 중 오류 발생: {str(e)}")
            return f"<pre><code>{code}</code></pre>"

    def _extract_code_blocks(self, markdown_text: str):
        """마크다운 텍스트에서 ```lang ...``` 형태 코드 블록 추출 및 플레이스홀더 치환"""
        code_blocks = []

        pattern = r"```(\w+)?\n(.*?)```"

        def repl(m):
            language = m.group(1) if m.group(1) else "python"
            code = m.group(2)
            index = len(code_blocks)
            code_blocks.append((language, code))
            return f"@@CODEBLOCK_{index}@@"

        replaced_text = re.sub(pattern, repl, markdown_text, flags=re.DOTALL)
        return replaced_text, code_blocks

    def _reinsert_code_blocks(self, html: str, code_blocks):
        """플레이스홀더 @@CODEBLOCK_i@@를 하이라이팅 코드 블록으로 치환"""

        def repl(m):
            index = int(m.group(1))
            language, code = code_blocks[index]
            highlighted = self._highlight_code(code, language)
            return f"""
<div class="highlighted-code-container">
    <div class="code-content">
        {highlighted}
    </div>
</div>
"""

        return re.sub(r"@@CODEBLOCK_(\d+)@@", repl, html)

    def _convert_markdown_to_html(self, markdown_text: str):
        """
        마크다운 변환 + 코드 하이라이팅 (플레이스홀더 기법)
        """
        replaced_text, code_blocks = self._extract_code_blocks(markdown_text)
        extras = {
            "fenced-code-blocks": None,
            "code-friendly": None,
            "tables": None,
            "break-on-newline": None,
            "header-ids": None,
        }
        html = markdown2.markdown(replaced_text, extras=extras)
        final_html = self._reinsert_code_blocks(html, code_blocks)
        return final_html

    def _create_email_content(self, analysis, analysis_time):
        """이메일 내용을 생성. 마크다운 & 코드 하이라이팅 반영"""
        converted_html = self._convert_markdown_to_html(analysis)

        # 새로운 CSS 스타일 추가
        html_content = f"""<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Inter, Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', Oxygen, Ubuntu, sans-serif;
            background-color: #F8FAFC;
            margin: 0;
            padding: 0;
            color: #334155;
            line-height: 1.8;
            font-size: 16px;
        }}
        .wrapper {{
            max-width: 1400px;
            margin: 2.5rem auto;
            padding: 0 40px;
            background-color: #FFFFFF;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}
        .header {{
            padding: 2rem 0 1.5rem;
            border-bottom: 1px solid #E2E8F0;
            margin-bottom: 2rem;
            background-color: #FFFFFF;
        }}
        .header-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: #1E293B;
            margin: 0;
            letter-spacing: -0.01em;
        }}
        .content-container {{
            padding: 0 0 3rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .footer {{
            text-align: center;
            color: #64748B;
            font-size: 0.9rem;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #E2E8F0;
        }}
        h1,h2,h3,h4,h5,h6 {{
            color: #1E293B;
            font-weight: 600;
            letter-spacing: -0.005em;
            margin-top: 2.2em;
            margin-bottom: 1.2em;
            line-height: 1.4;
            position: relative;
        }}
        h2::after {{
            content: "";
            display: block;
            width: 100%;
            height: 1px;
            background-color: #E2E8F0;
            position: absolute;
            bottom: -0.6em;
            left: 0;
        }}
        h1 {{ font-size: 1.8rem; }}
        h2 {{ font-size: 1.5rem; }}
        h3 {{ font-size: 1.3rem; }}
        p {{
            margin: 1.8rem 0;
            font-size: 16.5px;
            line-height: 1.85;
            padding-right: 2rem;
        }}
        ul, ol {{
            padding-left: 2.5em;
            padding-right: 2.5em;
            margin: 1.8rem 0;
            font-size: 16.5px;
        }}
        li {{
            margin: 1em 0;
            line-height: 1.85;
        }}
        div.highlighted-code-container {{
            margin: 2.2em 0;
            border-radius: 12px;
            background: rgb(39,40,35);
            overflow: hidden;
            padding: 0 1rem;
        }}
        div.highlighted-code-container .code-content {{
            padding: 1.5em 2.5em;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 15.5px;
            line-height: 1.75;
            color: #e4e4e4;
            background: rgb(39,40,35);
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="header">
            <h1 class="header-title">코드 분석 리포트</h1>
        </div>
        <div class="content-container">
            {converted_html}
            <div class="footer">
                <p>이 리포트는 CodeCast 자동 분석 시스템을 통해 생성되었습니다.</p>
                <p>© {datetime.now().year} CodeCast</p>
            </div>
        </div>
    </div>
</body>
</html>"""

        return html_content

    async def send_analysis_report(self):
        """분석 결과를 이메일로 전송합니다."""
        try:
            analysis, created_at = self._get_latest_analysis()
            if not analysis:
                print("No analysis results found to send")
                return False

            email_content = self._create_email_content(analysis, created_at)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f'코드 분석 리포트 - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg.attach(MIMEText(email_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"이메일 전송 중 오류 발생: {str(e)}")
            return False
