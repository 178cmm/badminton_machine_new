"""
IO Bridge：將 Text/ASR 輸入導向統一路徑。
"""

import asyncio
from core.parsers.unified_parser import UnifiedParser
from core.router import CommandRouter
from gui.response_templates import ReplyTemplates
from core.audit import write as audit_write


class IOBridge:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.parser = UnifiedParser()
        self.router = CommandRouter(gui_instance, ReplyTemplates)

    async def handle_text_async(self, text: str, source: str = "text") -> str:
        cmd = self.parser.parse(text, source=source)
        # 審計：解析後
        audit_write(text, cmd.__dict__ if cmd else None, None, {"source": source})
        if not cmd:
            return ""
        reply_text = await self.router.handle(cmd)
        # 審計：路由後
        audit_write(text, cmd.__dict__, reply_text, {"source": source})
        # 發佈到 UI
        self._emit_reply(cmd, reply_text)
        return reply_text

    def handle_text(self, text: str, source: str = "text"):
        asyncio.create_task(self.handle_text_async(text, source))

    def _emit_reply(self, cmd, reply_text: str):
        if not reply_text:
            return
        try:
            source = cmd.meta.get("source") if cmd and hasattr(cmd, 'meta') else None
            if source == "voice" and hasattr(self.gui, 'add_voice_chat_message'):
                self.gui.add_voice_chat_message(reply_text, "ai")
            elif hasattr(self.gui, 'text_chat_log'):
                self.gui.text_chat_log.append(f"AI: {reply_text}")
        except Exception:
            pass


