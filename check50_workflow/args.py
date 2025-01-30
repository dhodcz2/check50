import argparse


class Namespace(argparse.Namespace):
    slugs: list[str]
    force: bool
    outfile: str


parser = argparse.ArgumentParser(
    'check50_workflow',
)
parser.add_argument(
    'slugs',
    nargs='+',
    help='List of slugs to include in the workflow',
)
parser.add_argument(
    'outfile',
    default='./.github/workflows/classroom.yml',
    help='Output file to write the workflow to',
)
parser.add_argument(
    '--force',
    action='store_true',
    help='Force overwrite of existing workflow file',
)
