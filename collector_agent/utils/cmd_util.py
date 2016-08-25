
import subprocess


def get_cmd_output(cmd):
    return subprocess.check_output(cmd)

if __name__ == '__main__':
    print get_cmd_output(['iostat1', '-x', '1', '1'])