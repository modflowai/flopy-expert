#!/usr/bin/env python3
from scripts.review_tests import TestReviewCLI
from pathlib import Path

cli = TestReviewCLI()
model_file = Path('test_review/models/test_binaryfile_reverse/dis/model.py')
work_dir = Path('test_review/models/test_binaryfile_reverse/dis')

print(f"Testing: {model_file}")
print(f"In directory: {work_dir}")

result = cli.test_model(model_file, work_dir)

print(f'\nFinal result:')
for k, v in result.items():
    if k != 'error':
        print(f'  {k}: {v}')
        
if not result['runs']:
    print(f'\nError details:')
    print(result.get('error', 'No error message')[:500])