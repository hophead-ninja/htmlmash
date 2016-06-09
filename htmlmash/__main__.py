import argparse
from htmlmash import load_template

parser = argparse.ArgumentParser(prog='htmlmash', description="Process and print template")
parser.add_argument("template", help="htmlmash template file")
args = parser.parse_args()
try:
    template = load_template(args.template)
    print(template)
except FileNotFoundError:
    exit(2)
