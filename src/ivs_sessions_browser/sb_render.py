


from __future__ import annotations

from .defs import SessionsBrowserLike


class SessionsBrowserRenderMixin:
    def render_sessions_list(self: SessionsBrowserLike) -> list[str]:
        """
        Defined in sb_render.py.
        Docstring for render_sessions_list


        :return: A list of strings representing the rendered sessions.
        :rtype: list[str]
        """
        lines: list[str] = []
        lines.append(f"IVS Sessions Browser — year={self.year}, scope={self.scope}")
        lines.append(f"Filters: {self.filters}")
        lines.append("Jon Leithe")
        lines.append("(No session rows available in this minimal implementation.)")
        return lines
# ─── END OF render_sessions_list() ────────────────────────────────────────────
