import os
import sys
import yaml
from pathlib import Path
from args import parser, Namespace

# This helper class will represent our "blank line" insert.
class BlankLine:
    """Placeholder object to force a blank line in PyYAML output."""

# Subclass PyYAML's Dumper for customized handling
class BlankLineStepsDumper(yaml.Dumper):
    pass

# Use a custom presenter for multi-line strings, so they become literal block scalars (|).
def str_presenter(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

BlankLineStepsDumper.add_representer(str, str_presenter)

# Define a representer for our BlankLine placeholder
def blank_line_presenter(dumper, _):
    # Output an empty string with literal style, forcing a blank line
    return dumper.represent_scalar('tag:yaml.org,2002:str', '', style='|')

BlankLineStepsDumper.add_representer(BlankLine, blank_line_presenter)

# Capture the original list representer
original_list_representer = BlankLineStepsDumper.represent_list

def represent_list_with_extra_blank_lines(self, data):
    """
    If we're representing the 'steps' list, insert BlankLine() objects
    before each item (except the first) to force a blank line.
    """
    # Attempt to detect if this list is the steps array
    is_steps = False
    for obj in self.recursive_objects:
        if isinstance(obj, tuple) and len(obj) == 2:
            parent, _ = obj
            # If the parent is a dict that has a key == 'steps' pointing to `data`
            if isinstance(parent, dict) and any(
                k == 'steps' and parent[k] is data for k in parent
            ):
                is_steps = True
                break

    if is_steps and len(data) > 1:
        new_data = []
        first = True
        for item in data:
            # Insert a blank line placeholder before each step after the first
            if not first:
                new_data.append(BlankLine())
            new_data.append(item)
            first = False
        return original_list_representer(self, new_data)

    return original_list_representer(self, data)

# Override the default list representer with our augmented version
BlankLineStepsDumper.represent_list = represent_list_with_extra_blank_lines

def build_workflow(args: Namespace) -> dict:
    workflow = {
        'name': 'Autograding Tests',
        'on': {
            'push': {},
            'repository_dispatch': {}
        },
        'permissions': {
            'checks': 'write',
            'actions': 'read',
            'contents': 'read'
        },
        'jobs': {
            'run-autograding-tests': {
                'container': {'image': 'python:3.12-slim'},
                'runs-on': 'ubuntu-latest',
                'steps': [
                    {
                        'uses': 'actions/checkout@v4'
                    },
                    {
                        'name': 'Install dependencies (node, git, jq)',
                        'run': (
                            "apt-get update\n"
                            "apt-get install -y nodejs git jq\n"
                            "apt-get clean\n"
                            "rm -rf /var/lib/apt/lists/*\n"
                        )
                    }
                ]
            }
        }
    }

    slug_names = []
    for slug_path in args.slugs:
        slug_clean = slug_path.rstrip('/')
        slug_name_no_ext = Path(slug_clean).stem
        slug_names.append(slug_name_no_ext)

        workflow['jobs']['run-autograding-tests']['steps'].append({
            'name': slug_name_no_ext,
            'id': slug_name_no_ext,
            'uses': 'classroom-resources/autograding-command-grader@v1',
            'with': {
                'test-name': slug_name_no_ext,
                'setup-command': (
                    "pip uninstall -y check50\n"
                    "pip install --no-cache-dir git+https://github.com/dhodcz2/check50.git\n"
                ),
                'command': (
                    f"check50 {slug_clean} --dev -o json "
                    f"--autograder ./autograder/{slug_name_no_ext}.json "
                    f"--feedback ./feedback/{slug_name_no_ext}.txt"
                )
            }
        })

        workflow['jobs']['run-autograding-tests']['steps'].append({
            'name': f"Assign file contents to {slug_name_no_ext}_RESULTS",
            'run': f'echo "{slug_name_no_ext}_RESULTS=$(base64 -w0 ./{slug_name_no_ext}.json)" >> $GITHUB_ENV'
        })

    env_map = {f'{s}_RESULTS': f'${{{{ env.{s}_RESULTS }}}}' for s in slug_names}
    workflow['jobs']['run-autograding-tests']['steps'].append({
        'name': 'Autograding Reporter',
        'uses': 'classroom-resources/autograding-grading-reporter@v1',
        'env': env_map,
        'with': {
            'runners': ' '.join(slug_names)
        }
    })

    return workflow

def main():
    args: Namespace = parser.parse_args()
    if os.path.exists(args.outfile) and not args.force:
        sys.exit(1)

    workflow = build_workflow(args)
    with open(args.outfile, 'w', encoding='utf-8') as f:
        yaml.dump(
            workflow,
            f,
            sort_keys=False,
            default_flow_style=False,
            Dumper=BlankLineStepsDumper
        )

if __name__ == '__main__':
    main()

"""
/home/arstneio/PycharmProjects/test/example/ /home/arstneio/PycharmProjects/test/example/test.yml --force
"""
