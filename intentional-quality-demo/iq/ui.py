"""Terminal presentation layer (rich). Colours match the SoftCon 2026 deck."""
import time

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

ICE, CORAL, GREEN, AMBER, MUTED = "#61CBF4", "#FF6B6B", "#4ADE80", "#FFC857", "#A9BCD3"
FRAMEWORK_COLOR = {"LangGraph": ICE, "CrewAI": "#C4A7FF", "AutoGen": AMBER, "VRTQ": GREEN, "A2A": MUTED}


class UI:
    def __init__(self, stage=False, record=False, speed=1.0):
        self.console = Console(record=record, width=122 if record else None, highlight=False)
        self.stage, self.speed = stage, speed

    # ---- pacing
    def wait(self, s):
        if self.speed > 0:
            time.sleep(s * self.speed)

    def pause(self):
        if self.stage:
            self.console.input(f"[{MUTED}]  press Enter to continue >[/] ")

    # ---- building blocks
    def step(self, n, title, framework):
        c = FRAMEWORK_COLOR.get(framework, ICE)
        self.console.print()
        self.console.rule(Text.assemble((f" STEP {n} ", "bold black on " + c), "  ", (title, "bold white"),
                                        "   ", (f"[{framework}]", c)), style=c)

    def say(self, text, style="white"):
        self.console.print(Text(text, style=style))

    def code(self, src, title=None, highlight_lines=None):
        syn = Syntax(src, "python", theme="monokai", line_numbers=True, highlight_lines=highlight_lines or set(),
                     background_color="#050C1A")
        self.console.print(Panel(syn, title=title, border_style=MUTED, box=box.ROUNDED, expand=False))

    def big_numbers(self, items):
        t = Table.grid(padding=(0, 6))
        cells = []
        for label, value, colour in items:
            cells.append(Group(Text(value, style=f"bold {colour}", justify="center"),
                               Text(label, style=MUTED, justify="center")))
        t.add_row(*cells)
        self.console.print(Panel(t, box=box.ROUNDED, border_style=MUTED, expand=False, padding=(1, 3)))

    def a2a(self, msg, show_json=False):
        meta = msg["params"]["message"]["metadata"]
        data = msg["params"]["message"]["parts"][0]["data"]
        kind = data.get("task", "")
        self.console.print(Text.assemble(("  A2A ", "bold black on " + MUTED), " ",
                                         (meta["from"], ICE), (" -> ", MUTED), (meta["to"], AMBER),
                                         (f"   message/send #{msg['id']}  {kind}", MUTED)))
        if show_json:
            import json
            self.console.print(Panel(Syntax(json.dumps(msg, indent=2), "json", theme="monokai",
                                            background_color="#050C1A"),
                                     title="what travels between agents", border_style=MUTED, expand=False))

    def mutant_row_table(self):
        t = Table(box=box.SIMPLE_HEAVY, header_style=f"bold {ICE}", expand=False)
        for col in ("#", "function", "line", "change", "mutated code", "result"):
            t.add_column(col)
        return t

    def status_text(self, status):
        return {"killed": Text("KILLED", style=f"bold {GREEN}"),
                "survived": Text("SURVIVED", style=f"bold {CORAL}"),
                "equivalent": Text("EQUIVALENT", style=f"bold {AMBER}"),
                "pending": Text("...", style=MUTED)}[status]

    def speaker(self, who, text):
        colour = {"Gap Hunter": CORAL, "Equivalence Advocate": AMBER, "Judge": ICE}.get(who, MUTED)
        self.console.print(Text.assemble((f"  {who:>21}  ", f"bold {colour}"), (text, "white")))

    def save_html(self, path, title):
        from rich.terminal_theme import MONOKAI
        self.console.save_html(path, theme=MONOKAI, inline_styles=False)
        # give the backup page a proper title
        with open(path, encoding="utf-8") as f:
            html = f.read()
        html = html.replace("<head>", f"<head>\n<title>{title}</title>", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
