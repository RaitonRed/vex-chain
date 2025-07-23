import time
import sys

def scary_warning():
    warning_msg = """
    ********
    *  WARNING: INTRUDER  *
    *  ACCESS DENIED!     *
    *  SYSTEM LOCKDOWN   *
    ********
    """
    for char in warning_msg:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.05)

    for i in range(5, 0, -1):
        sys.stdout.write(f"\rSelf destruct in {i} seconds... ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\n")
    sys.exit(">>> SYSTEM TERMINATED <<<")

if __name__ == "__main__":
    # scary_warning()
    from colorama import Fore, Back, Style
    print(Fore.RED + 'some red text')
    print(Back.GREEN + 'and with a green background')
    print(Style.DIM + 'and in dim text')
    print(Style.RESET_ALL)
    print('back to normal now')