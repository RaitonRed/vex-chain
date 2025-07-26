import json
from src.cli.style import CLITheme

theme = CLITheme()

def prompt_address(prompt_text):
    """Prompt for blockchain address"""
    while True:
        address = input(f"{theme.PROMPT}{prompt_text}: {theme.INPUT}")
        if address and len(address) >= 20:
            return address
        print_error("Address must be at least 20 characters")

def prompt_amount(prompt_text):
    """Prompt for numeric amount"""
    while True:
        try:
            amount = float(input(f"{theme.PROMPT}{prompt_text}: {theme.INPUT}"))
            if amount >= 0:
                return amount
            print_error("Amount must be positive")
        except ValueError:
            print_error("Invalid number format")

def prompt_contract_code():
    """Prompt for multi-line contract code"""
    print(f"{theme.INFO}Enter contract code (type 'END' on new line to finish):{theme.RESET}")
    code_lines = []
    while True:
        line = input(f"{theme.CODE_INPUT}")
        if line.strip().upper() == "END":
            break
        code_lines.append(line)
    return "\n".join(code_lines)

def prompt_contract_call():
    """Prompt for contract call arguments"""
    while True:
        args_str = input(f"{theme.PROMPT}Arguments (JSON): {theme.INPUT}") or "{}"
        try:
            return json.loads(args_str)
        except json.JSONDecodeError:
            print_error("Invalid JSON format")

def prompt_method_name():
    """Prompt for contract method name"""
    while True:
        method = input(f"{theme.PROMPT}Method name: {theme.INPUT}").strip()
        if method:
            return method
        print_error("Method name cannot be empty")

def prompt_contract_address():
    """Prompt for contract address"""
    while True:
        address = input(f"{theme.PROMPT}Contract address: {theme.INPUT}").strip()
        if address and address.startswith("0x") and len(address) >= 20:
            return address
        print_error("Invalid contract address format (must start with 0x)")

def print_error(message):
    """Helper for error messages"""
    print(f"{theme.ERROR}❌ {message}{theme.RESET}")

def prompt_json_data(prompt_text):
    """Get JSON data from user"""
    while True:
        data_str = input(f"{theme.PROMPT}{prompt_text} (or empty for {{}}): {theme.INPUT}").strip()
        if not data_str:
            return {}
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            print_error("Invalid JSON format!")

def prompt_yes_no(prompt_text):
    """Get yes/no answer"""
    while True:
        answer = input(f"{theme.PROMPT}{prompt_text} (y/n): {theme.INPUT}").lower().strip()
        if answer in ['y', 'yes']:
            return True
        if answer in ['n', 'no']:
            return False
        print_error("Please enter y or n")