# reporting/email_sender.py
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import sqlite3
from config.settings import Config
import aiosmtplib


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

    def _convert_markdown_to_html(self, markdown_text):
        """마크다운 텍스트를 HTML로 변환하고 다양한 언어의 코드 블록에 구문 강조를 적용합니다."""
        try:
            import markdown2
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_by_name, guess_lexer

            # 코드 블록 스타일 정의
            code_style = """
            <style>
                .highlight {
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 1em;
                    margin: 0.5em 0;
                    border-radius: 5px;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 14px;
                    line-height: 1.5;
                    overflow-x: auto;
                }
                .highlight .k  { color: #569cd6; } /* Keyword */
                .highlight .s  { color: #ce9178; } /* String */
                .highlight .c1 { color: #6a9955; } /* Comment */
                .highlight .n  { color: #9cdcfe; } /* Name */
                .highlight .o  { color: #d4d4d4; } /* Operator */
                .highlight .p  { color: #d4d4d4; } /* Punctuation */
                .highlight .c  { color: #6a9955; } /* Comment */
                .highlight .kc { color: #569cd6; } /* Keyword.Constant */
                .highlight .kd { color: #569cd6; } /* Keyword.Declaration */
                .highlight .na { color: #9cdcfe; } /* Name.Attribute */
                .highlight .nf { color: #dcdcaa; } /* Name.Function */
                .highlight .nn { color: #9cdcfe; } /* Name.Namespace */
                .highlight .nt { color: #569cd6; } /* Name.Tag */
            </style>
            """

            def custom_code_formatter(code, language=None):
                try:
                    if language:
                        lexer = get_lexer_by_name(language)
                    else:
                        lexer = guess_lexer(code)
                    formatter = HtmlFormatter(style="vs", cssclass="highlight")
                    return highlight(code, lexer, formatter)
                except Exception:
                    # 언어를 감지할 수 없는 경우 일반 코드 블록으로 표시
                    return f'<pre class="highlight"><code>{code}</code></pre>'

            # markdown2 확장 기능 설정
            extras = {
                "fenced-code-blocks": None,
                "code-friendly": None,
                "tables": None,
                "break-on-newline": None,
                "header-ids": None,
            }

            # 마크다운을 HTML로 변환
            html = markdown2.markdown(markdown_text, extras=extras)

            # 코드 블록 처리를 위한 정규식 패턴
            import re

            code_block_pattern = r"<pre><code.*?>(.*?)</code></pre>"

            def replace_code_block(match):
                code = match.group(1)
                # 언어 감지 시도
                lang_match = re.match(r"^(\w+):\n", code)
                if lang_match:
                    language = lang_match.group(1)
                    code = code[len(language) + 2 :]
                else:
                    language = None
                return custom_code_formatter(code, language)

            # 코드 블록 변환
            html = re.sub(code_block_pattern, replace_code_block, html, flags=re.DOTALL)

            # 최종 HTML 반환
            return code_style + html

        except ImportError:
            print("필요한 패키지를 설치하세요: pip install markdown2 pygments")
            return markdown_text
        except Exception as e:
            print(f"마크다운 변환 중 오류 발생: {str(e)}")
            return markdown_text

    def _create_email_content(self, analysis, analysis_time):
        """이메일 내용을 생성합니다."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_content = f"""<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; line-height: 1.4; color: #2D3748; max-width: 800px; margin: 0 auto; background-color: #F7FAFC; }}
        .container {{ padding: 1.5rem; }}
        .header {{ 
            background: linear-gradient(135deg, #2B6CB0 0%, #4C51BF 100%);
            color: white;
            padding: 1.8rem;
            border-radius: 12px 12px 0 0;
            text-align: left;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            position: relative;
            overflow: hidden;
        }}
        .header::after {{
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 300px;
            height: 100%;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0) 100%);
            transform: skewX(-30deg) translateX(70%);
        }}
        .content {{ 
            background: white;
            padding: 1.8rem;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        }}
        .timestamp {{ 
            color: #718096;
            font-size: 0.9rem;
            margin: 0.5rem 0 1.2rem;
            padding: 0.8rem 1rem;
            border-radius: 6px;
            background: #F8FAFC;
            display: inline-block;
        }}
        .analysis-section {{ 
            background-color: #F8FAFC;
            border-left: 4px solid #4C51BF;
            padding: 1.2rem;
            margin: 0.8rem 0;
            border-radius: 6px;
            font-family: 'SF Mono', Consolas, Monaco, monospace;
            white-space: pre-wrap;
            overflow-x: auto;
            line-height: 1.3;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        }}
        .footer {{ 
            text-align: center;
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid #EDF2F7;
            color: #718096;
            font-size: 0.875rem;
        }}
        h1 {{ 
            margin: 0;
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.025em;
        }}
        .badge {{ 
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background-color: rgba(255,255,255,0.15);
            border-radius: 9999px;
            font-size: 0.875rem;
            margin-top: 0.5rem;
            backdrop-filter: blur(4px);
        }}
        p {{ margin: 0.3rem 0; }}
        .meta-info {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding: 0.8rem 1rem;
            background: #F8FAFC;
            border-radius: 6px;
        }}
        .meta-info-item {{
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }}
        .meta-info-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #718096;
        }}
        .meta-info-value {{
            font-weight: 500;
            color: #2D3748;
        }}
        .section-title {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            
            color: #718096;
            margin: 1.5rem 0 0.5rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>코드 분석 리포트</h1>
            <div class="badge">CodeCast AI</div>
        </div>
        <div class="content">
            <div class="meta-info">
                <div class="meta-info-item">
                    <span class="meta-info-label">분석 시간</span>
                    <span class="meta-info-value">{analysis_time}</span>
                </div>
                <div class="meta-info-item">
                    <span class="meta-info-label">리포트 생성</span>
                    <span class="meta-info-value">{current_time}</span>
                </div>
            </div>
            <div class="section-title">분석 결과</div>
            <div class="analysis-section">{self._convert_markdown_to_html(analysis)}</div>
            <div class="footer">
                <p>CodeCast 자동 분석 시스템에서 생성된 리포트입니다</p>
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

            # 인라인 스타일을 사용한 HTML 템플릿
            email_template = """
<html>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6;">
    <h2 style="color: #333; margin-bottom: 20px;">코드 분석 리포트</h2>
    <p style="color: #666; margin-bottom: 30px;">생성 시각: {created_at}</p>
    <div style="white-space: pre-line;">
        {content}
    </div>
</body>
</html>"""

            # 마크다운의 코드 블록을 HTML로 변환하고 설명 텍스트에 여백 추가
            import re

            content = analysis

            # 개선점 제목에 여백 추가
            content = re.sub(r"\n(\d+\. .+)\n", r"\n\n\1\n", content)

            # 개선 이유 목록에 여백 추가
            content = re.sub(
                r"\n개선 이유:(.+?)(?=\n\d+\. |\Z)", lambda m: f"\n개선 이유:\n{m.group(1)}", content, flags=re.DOTALL
            )

            # 코드 블록 변환 및 스타일링
            content = re.sub(
                r"```(\w+)?\n(.*?)```",
                lambda m: f'<div style="margin: 20px 0;"><pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; overflow-x: auto; font-family: Consolas, monospace; font-size: 14px; line-height: 1.4;">{self._highlight_code(m.group(2), m.group(1) if m.group(1) else "python")}</pre></div>',
                content,
                flags=re.DOTALL,
            )

            # 이메일 내용 생성
            email_content = email_template.format(created_at=created_at, content=content)

            # 이메일 전송
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

    def _highlight_code(self, code: str, language: str) -> str:
        """코드 구문 강조를 적용합니다."""
        try:
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import get_lexer_by_name, PythonLexer

            try:
                lexer = get_lexer_by_name(language)
            except:
                lexer = PythonLexer()

            formatter = HtmlFormatter(noclasses=True, style="monokai", nowrap=False, inline_css=True)

            return highlight(code, lexer, formatter)
        except Exception as e:
            print(f"코드 강조 처리 중 오류 발생: {str(e)}")
            return code
