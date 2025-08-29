# Deprecated

class CLITheme:
    """ANSI color codes for CLI styling"""
    def __init__(self):
        # Reset
        self.RESET = "\033[0m"
        
        # Colors
        self.HEADER = "\033[95m"      # Purple
        self.SUBHEADER = "\033[94m"   # Blue
        self.INFO = "\033[96m"        # Cyan
        self.SUCCESS = "\033[92m"     # Green
        self.WARNING = "\033[93m"     # Yellow
        self.ERROR = "\033[91m"       # Red
        self.KEY = "\033[92m"         # Green (for menu keys)
        
        # Text styles
        self.LABEL = "\033[1m"        # Bold
        self.VALUE = "\033[37m"       # Light gray
        
        # Input prompts
        self.PROMPT = "\033[94m"      # Blue
        self.INPUT = "\033[36m"       # Cyan
        self.CODE_INPUT = "\033[90m"  # Dark gray