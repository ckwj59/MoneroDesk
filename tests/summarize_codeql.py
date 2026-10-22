"""Expose actual SARIF findings in Actions annotations; never infer a clean scan."""
import json
import os
from pathlib import Path


def escape(value, properties=False):
    value = str(value).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    return value.replace(',', '%2C').replace(':', '%3A') if properties else value


def summarize(directory):
    files = list(Path(directory).glob('*.sarif'))
    if not files:
        raise RuntimeError('No SARIF report found; this is not a clean scan result')
    rows = []
    for filename in files:
        for run in json.loads(filename.read_text(encoding='utf-8')).get('runs', []):
            for result in run.get('results', []):
                location = (result.get('locations') or [{}])[0].get('physicalLocation', {})
                path = location.get('artifactLocation', {}).get('uri', '')
                line = location.get('region', {}).get('startLine', 1)
                rule = result.get('ruleId', 'unknown')
                message = result.get('message', {}).get('text', '')
                print(f'::warning file={escape(path, True)},line={line}::{escape(rule + ": " + message)}')
                rows.append(f'- `{rule}` — `{path}:{line}`: {message}')
    return len(files), rows


if __name__ == '__main__':
    files, rows = summarize('codeql-results')
    text = f'## CodeQL: {len(rows)} findings in {files} report(s)\n\n'
    text += '\n'.join(rows) if rows else 'No findings were emitted in these reports. Verify that analysis and upload both succeeded.'
    text += '\n\nAutomated scan result only; not a safety certification. CUDA device-code coverage is limited.\n'
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
        output.write(text)
    print(f'CodeQL findings: {len(rows)}')
