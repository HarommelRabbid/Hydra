import sys

class HydraError(Exception):
    def __init__(self, msg, line=1, col=1, line_text="", length=1):
        self.msg = msg
        self.line = line
        self.col = col
        self.line_text = line_text
        self.length = length

    def display(self):
        prefix = f"{self.line} | "
        prefix1 = (" " * len(str(self.line))) + " | "
        padding = " " * (self.col - 1)
        carets = "^" * max(1, self.length)
        sys.stderr.write(f"\nHydra has encountered an error: {self.msg}\n")
        sys.stderr.write(f"--> Line {self.line}, Column {self.col}\n")
        sys.stderr.write(f"{prefix}{self.line_text}\n")
        sys.stderr.write(f"{prefix1}{padding}{carets}\n")