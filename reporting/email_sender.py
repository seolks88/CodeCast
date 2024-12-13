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
import html


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

    def _highlight_code(self, code: str, language: str = "python") -> str:
        try:
            # 코드 문자열 정리
            code = code.replace("\r\n", "\n").strip()

            # 언어별 렉서 설정
            try:
                lexer = get_lexer_by_name(language.lower())
            except:
                lexer = PythonLexer()

            # HTML 포매터 설정
            formatter = HtmlFormatter(style="monokai", noclasses=True, nowrap=True, cssclass="highlight")

            # 코드 하이라이팅
            highlighted = highlight(code, lexer, formatter)

            # 컨테이너로 감싸기
            return f"""
            <div class="highlighted-code-container">
                <div class="code-content">
                    <pre><code class="language-{language}">{highlighted}</code></pre>
                </div>
            </div>
            """
        except Exception as e:
            print(f"코드 강조 처리 중 오류 발생: {str(e)}")
            # 폴백: 기본 pre/code 태그 사용
            return f"<pre><code>{html.escape(code)}</code></pre>"

    def _extract_code_blocks(self, markdown_text: str):
        code_blocks = []
        # @@CODEBLOCK과 일반 코드 블록 모두 처리하는 패턴
        pattern = r"(?:@@CODEBLOCK_\d+@@)|(?:```([^\n]*)\n(.*?)```)"

        def repl(m):
            # 이미 치환된 코드블록인 경우
            if m.group(0).startswith("@@CODEBLOCK"):
                return m.group(0)

            # 새로운 코드블록 처리
            language = m.group(1).strip() if m.group(1) else "python"
            code = m.group(2)
            index = len(code_blocks)
            code_blocks.append((language, code.strip()))
            return f"@@CODEBLOCK_{index}@@"

        replaced_text = re.sub(pattern, repl, markdown_text, flags=re.DOTALL)
        return replaced_text, code_blocks

    def _reinsert_code_blocks(self, html_text: str, code_blocks: list) -> str:
        def repl(m):
            try:
                index = int(m.group(1))
                if index < len(code_blocks):
                    language, code = code_blocks[index]
                    return self._highlight_code(code, language)
            except Exception as e:
                print(f"코드 블록 재삽입 중 오류: {str(e)}")
            return m.group(0)

        return re.sub(r"@@CODEBLOCK_(\d+)@@", repl, html_text)

    def _format_top_summary(self, content: str) -> str:
        sections = content.split("##")
        if len(sections) <= 1:
            return ""

        key_points = []
        for section in sections[1:4]:
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
                        font-size: 14px;
                        letter-spacing: -0.01em;
                        word-break: keep-all;
                    }}
                    
                    .wrapper {{
                        max-width: 1200px;
                        margin: 1rem auto;
                        padding: 0;
                        background-color: #F8FAFC;
                        border-radius: 16px;
                        box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.1);
                        overflow: hidden;
                    }}
                    
                    .header {{
                        background: linear-gradient(135deg, #4F46E5, #3730A3);
                        padding: 2.5rem 3rem;
                        position: relative;
                        overflow: hidden;
                    }}
                    
                    .header::before {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background-image: url('data:image/svg+xml,%3Csvg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"%3E%3Cpath d="M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z" fill="%23ffffff" fill-opacity="0.05" fill-rule="evenodd"/%3E%3C/svg%3E');
                        opacity: 0.4;
                    }}
                    
                    .header-title {{
                        font-size: 1.5rem;
                        font-weight: 800;
                        color: white;
                        margin: 0;
                        display: flex;
                        align-items: center;
                        gap: 0.75rem;
                        letter-spacing: -0.03em;
                    }}
                    
                    .logo-text {{
                        color: #F0F4FF;
                        font-weight: 900;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }}
                    
                    .divider {{
                        color: rgba(255, 255, 255, 0.3);
                        font-weight: 300;
                    }}
                    
                    .report-type {{
                        color: rgba(255, 255, 255, 0.9);
                        font-weight: 600;
                    }}
                    
                    .header-subtitle {{
                        margin-top: 0.75rem;
                        color: rgba(255, 255, 255, 0.7);
                        font-size: 0.95rem;
                        font-weight: 500;
                    }}
                    
                    .header-date {{
                        margin-top: 0.875rem;
                        color: rgba(255, 255, 255, 0.9);
                        font-size: 0.9rem;
                        font-weight: 500;
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    }}
                    
                    .header-date::before {{
                        content: '';
                        display: inline-block;
                        width: 4px;
                        height: 4px;
                        background: rgba(255, 255, 255, 0.6);
                        border-radius: 50%;
                    }}
                    
                    .content-container {{
                        padding: 0.5rem 1.5rem 0.5rem;
                        max-width: 100%;
                        line-height: 1.8;
                        background: #FFFFFF;
                        border-radius: 12px;
                        margin: 1rem;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    }}
                    
                    h1, h2, h3 {{
                        color: #0F172A;
                        font-weight: 700;
                        line-height: 1.4;
                        margin-top: 1.5rem;
                        margin-bottom: 1rem;
                    }}
                    
                    h1 {{ 
                        font-size: 1.2rem;
                        margin: 2rem 0 1.5rem;
                    }}
                    
                    h2 {{ 
                        font-size: 1.1rem;
                        margin: 2rem 0 1.5rem;
                        padding-bottom: 0.5rem;
                        border-bottom: 2px solid #E2E8F0;
                    }}
                    
                    h3 {{
                        font-size: 1rem;
                        margin: 2rem 0 1rem;
                        color: #1E293B;
                    }}

                    h4 {{
                        font-size: 1rem;
                        margin: 0.75rem 0 0.5rem;
                        color: #1E293B;
                    }}
                    h5 {{
                        font-size: 1rem;
                        margin: 0.75rem 0 0.5rem;
                        color: #1E293B;
                    }}
                    h6 {{
                        font-size: 1rem;
                        margin: 0.75rem 0 0.5rem;
                        color: #1E293B;
                    }}
                    
                    p, li {{
                        color: #334155;
                        font-size: 1rem;
                        line-height: 1.8;
                        margin: 1rem 0;
                    }}
                    
                    .highlighted-code-container {{
                        background-color: #1A1F35;
                        background-image: linear-gradient(160deg, #1A1F35, #111827);
                        border-radius: 12px;
                        padding: 1rem 1.75rem;
                        margin: 1rem 0;
                        overflow-x: auto;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
                    }}
                    
                    .highlighted-code-container .code-content {{
                        font-family: 'D2Coding', 'JetBrains Mono', Consolas, monospace;
                        font-size: 0.9rem;
                        color: #F1F5F9;
                        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
                        line-height: 1.6;
                    }}

                    .highlighted-code-container .code-content pre,
                    .highlighted-code-container .code-content pre code,
                    .highlighted-code-container .code-content pre span {{
                        font-size: 0.9rem !important;
                        line-height: 1.6 !important;
                        white-space: pre-wrap !important;
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
                        margin: 1rem 0;
                        padding: 1rem 1.5rem;
                        background: #F8FAFC;
                        border-left: 4px solid #2563EB;
                        border-radius: 0 16px 16px 0;
                        color: #334155;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
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
                        color: #64748B;
                        font-size: 1rem;
                        margin-top: 5rem;
                        padding: 2.5rem;
                        background: #F8FAFC;
                        border-radius: 0 0 16px 16px;
                        border-top: 1px solid #E2E8F0;
                    }}
                    
                    .footer p {{
                        margin: 0.4rem 0;
                        color: #94A3B8;
                    }}
                    
                    .content-container ul li,
                    .content-container ol li {{
                        font-size: 1rem;
                        padding-left: 0.5rem;
                        margin: 0.75rem 0;
                    }}
                    
                    .highlight .k {{ color: #93C5FD; font-weight: 600; }}
                    .highlight .n {{ color: #F1F5F9; }}
                    .highlight .s {{ color: #86EFAC; }}
                    .highlight .o {{ color: #FDA4AF; font-weight: 600; }}
                    .highlight .p {{ color: #F1F5F9; }}

                    .agent-section {{
                        background: #F9FAFB;
                        border: 1px solid #E2E8F0;
                        border-radius: 8px;
                        padding: 2rem;
                        margin: 1.5rem 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    }}
                    .agent-section ul, 
                    .agent-section ol {{
                        padding-left: 2.5rem;
                        margin: 1.2rem 0;
                    }}
                    .agent-section li {{
                        margin: 0.8rem 0;
                        padding-left: 0.5rem;
                    }}
                    .agent-section p {{
                        margin: 1rem 0;
                        line-height: 1.8;
                    }}
                    .analysis-section {{
                        margin: 2rem 0;
                        padding: 0 1rem;
                    }}
                    .analysis-section h3 {{
                        margin-top: 2.5rem;
                        margin-bottom: 1.5rem;
                        color: #1E293B;
                        font-weight: 600;
                    }}
                    .footer-meta {{
                        margin-top: 2rem;
                        padding: 1rem 0;
                        color: #666;
                        border-top: 1px solid #eee;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="wrapper">
                    <div class="header">
                        <h1 class="header-title">
                            <span class="logo-text">⚡️ CodeCast</span>
                            <span class="divider">&nbsp;|&nbsp;</span>
                            <span class="report-type">코드 분석 리포트</span>
                        </h1>
                        <div class="header-subtitle">
                            실시간 코드 모니터링 및 AI 기반 분석
                        </div>
                        <div class="header-date">
                            {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")} 생성
                        </div>
                    </div>
                    <div class="content-container">
                        <div class="content-section">
                            {converted_html}
                        </div>
                    </div>
                </div>
            </body>
        </html>"""

        return html_content

    def _convert_markdown_to_html(self, markdown_text: str):
        def replace_inline_backticks(text: str) -> str:
            """코드 블록 내부의 백틱 3개를 작은따옴표 3개로 치환"""
            lines = text.split("\n")
            in_code_block = False
            result = []

            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    result.append(line)
                elif in_code_block and "```" in line:
                    # 코드 블록 내부에서 백틱이 있는 경우 작은따옴표로 치환
                    result.append(line.replace("```", "'''"))
                else:
                    result.append(line)

            return "\n".join(result)

        # 코드 블록 추출 전에 백틱 치환 처리
        markdown_text = replace_inline_backticks(markdown_text)
        replaced_text, code_blocks = self._extract_code_blocks(markdown_text)

        def extract_agent_sections(text):
            sections = []
            pattern = r"<<AGENT_SECTION_START>>\n(.*?)\n<<AGENT_SECTION_END>>"

            def repl(m):
                index = len(sections)
                sections.append(m.group(1))
                return f"@@AGENT_SECTION_{index}@@"

            replaced = re.sub(pattern, repl, text, flags=re.DOTALL)
            return replaced, sections

        replaced_text, agent_sections = extract_agent_sections(replaced_text)

        extras = {
            "fenced-code-blocks": None,
            "code-friendly": None,
            "tables": None,
            "break-on-newline": True,
            "header-ids": None,
            # "preserve-tabs": True,
        }

        html = markdown2.markdown(replaced_text, extras=extras)
        # 1차로 코드블록 재삽입 (전체)
        html = self._reinsert_code_blocks(html, code_blocks)

        # 이제 에이전트 섹션 삽입 로직
        def reinsert_agent_sections(html_text):
            def repl(m):
                index = int(m.group(1))
                content = agent_sections[index]
                # 에이전트 섹션 내용도 마크다운 변환
                section_html = markdown2.markdown(content, extras=extras)
                # 섹션 내용에 존재하는 @@CODEBLOCK_x@@도 다시 재삽입
                section_html = self._reinsert_code_blocks(section_html, code_blocks)
                return f'<div class="agent-section">{section_html}</div>'

            return re.sub(r"@@AGENT_SECTION_(\d+)@@", repl, html_text)

        final_html = reinsert_agent_sections(html)
        return final_html

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
