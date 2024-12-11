# email_sender.py
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

    # -----------------
    # 데이터베이스 작업
    # -----------------
    def _get_latest_analysis(self):
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

    # -----------------
    # 코드 블록 처리
    # -----------------
    def _highlight_code(self, code: str, language: str) -> str:
        """코드 구문 강조를 적용합니다."""
        try:
            # 코드 끝의 불필요한 줄바꿈 제거
            code = code.rstrip()

            try:
                lexer = get_lexer_by_name(language)
            except pygments.util.ClassNotFound:
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

    def _format_top_summary(self, content: str) -> str:
        sections = content.split("##")
        if len(sections) <= 1:
            return ""

        key_points = []
        for section in sections[1:4]:  # 처음 3개 섹션만 처리
            lines = section.strip().split("\n")
            if lines:
                title = lines[0].strip()
                if title:
                    key_points.append(title)

        if not key_points:
            return ""

        summary_html = """
        <div class="summary-section">
            <div class="summary-title">📌 주요 포인트</div>
            <ul>
        """
        for point in key_points:
            summary_html += f"<li>{point}</li>"
        summary_html += """
            </ul>
        </div>
        """
        return summary_html

    # -----------------
    # HTML 생성 및 스타일링
    # -----------------
    def _create_email_content(self, analysis, analysis_time):
        converted_html = self._convert_markdown_to_html(analysis)

        html_content = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Pretendard', 'Noto Sans KR', 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        background-color: #F8FAFC;
                        margin: 0;
                        padding: 0;
                        color: #334155;
                        line-height: 1.8;
                        -webkit-font-smoothing: antialiased;
                        -moz-osx-font-smoothing: grayscale;
                        font-size: 16px;
                        letter-spacing: -0.01em;
                        word-break: keep-all;
                    }}
                    
                    .wrapper {{
                        max-width: 1200px;
                        margin: 2rem auto;
                        padding: 0 2rem;
                        background-color: #FFFFFF;
                        border-radius: 12px;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                    }}
                    
                    .header {{
                        background-color: #2563EB;
                        padding: 2rem 2.5rem;
                        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    }}
                    
                    .header-title {{
                        font-size: 1.6rem;
                        font-weight: 600;
                        color: white;
                        margin: 0;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }}
                    
                    .header-date {{
                        margin-top: 0.75rem;
                        color: rgba(255, 255, 255, 0.9);
                        font-size: 0.95rem;
                    }}
                    
                    .content-container {{
                        padding: 2rem 2.5rem;
                        max-width: 100%;
                    }}
                    
                    h1, h2, h3 {{
                        color: #1E293B;
                        font-weight: 600;
                        line-height: 1.4;
                        letter-spacing: -0.02em;
                        max-width: 100%;
                        overflow-wrap: break-word;
                        word-wrap: break-word;
                        -webkit-hyphens: auto;
                        -ms-hyphens: auto;
                        hyphens: auto;
                    }}
                    
                    h1 {{ 
                        font-size: 1.875rem;
                        margin: 2.5rem 0 1.5rem;
                    }}
                    
                    h2 {{ 
                        font-size: 1.5rem;
                        margin: 2.5rem 0 1.2rem;
                        padding-bottom: 0.75rem;
                        border-bottom: 1px solid #E2E8F0;
                    }}
                    
                    h3 {{
                        font-size: 1.25rem;
                        margin: 2rem 0 1rem;
                    }}
                    
                    p, li {{
                        margin: 1.2rem 0;
                        line-height: 1.8;
                        color: #475569;
                        font-size: 1.125rem;
                        letter-spacing: -0.01em;
                    }}
                    
                    .highlighted-code-container {{
                        background-color: #1E293B;
                        border-radius: 8px;
                        padding: 1.25rem;
                        margin: 1.5rem 0;
                        overflow-x: auto;
                    }}
                    
                    .highlighted-code-container .code-content {{
                        font-family: 'D2Coding', 'JetBrains Mono', Consolas, monospace;
                        font-size: 1rem;
                        line-height: 1.75;
                        letter-spacing: 0;
                        color: #E2E8F0;
                    }}
                    
                    .highlight {{
                        background: transparent !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }}
                    
                    .highlight pre {{
                        margin: 0 !important;
                        padding: 0 !important;
                        background: transparent !important;
                    }}
                    
                    .code-header {{
                        display: none;
                    }}
                    
                    ul, ol {{
                        margin: 1.2rem 0;
                        padding-left: 1.8rem;
                        color: #475569;
                    }}
                    
                    li {{
                        margin: 0.8rem 0;
                        line-height: 1.6;
                        padding-left: 0.3rem;
                    }}
                    
                    blockquote {{
                        margin: 1.8rem 0;
                        padding: 1.2rem 1.8rem;
                        background: #F8FAFC;
                        border-left: 4px solid #2563EB;
                        border-radius: 0 8px 8px 0;
                        color: #475569;
                    }}
                    
                    strong {{
                        color: #1E293B;
                        font-weight: 600;
                    }}
                    
                    a {{
                        color: #2563EB;
                        text-decoration: none;
                        border-bottom: 1px solid transparent;
                        transition: border-color 0.2s;
                    }}
                    
                    a:hover {{
                        border-bottom-color: #2563EB;
                    }}
                    
                    .footer {{
                        text-align: center;
                        color: #94A3B8;
                        font-size: 0.9rem;
                        margin-top: 3.5rem;
                        padding: 1.8rem;
                        background: #F8FAFC;
                        border-radius: 0 0 12px 12px;
                    }}
                    
                    .footer p {{
                        margin: 0.4rem 0;
                        color: #94A3B8;
                    }}
                    
                    .content-container ul li,
                    .content-container ol li {{
                        font-size: 1.125rem;
                        padding-left: 0.5rem;
                        margin: 0.75rem 0;
                    }}
                </style>
            </head>
            <body>
                <div class="wrapper">
                    <div class="header">
                        <h1 class="header-title">📊 코드 분석 리포트</h1>
                        <div class="header-date">
                            생성일시: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}
                        </div>
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

    def _convert_markdown_to_html(self, markdown_text: str):
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

    # -----------------
    # 이메일 전송
    # -----------------
    async def send_analysis_report(self):
        try:
            analysis, created_at = self._get_latest_analysis()
            if not analysis:
                print("📭 발송할 분석 결과가 없습니다")
                return False

            email_content = self._create_email_content(analysis, created_at)
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f'[CodeCast] 코드 분석 리포트 - {datetime.now().strftime("%Y-%m-%d")}'
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg.attach(MIMEText(email_content, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            print("📨 분석 리포트가 성공적으로 발송되었습니다!")
            return True

        except Exception as e:
            print(f"❌ 이메일 전송 중 오류가 발생했습니다: {str(e)}")
            return False
