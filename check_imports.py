#!/usr/bin/env python3
import sys
import os

# Add the dashboard/backend directory to Python path
sys.path.insert(0, 'dashboard/backend')

test_dir = 'dashboard/backend/tests'
errors = []

for root, dirs, files in os.walk(test_dir):
    for file in files:
        if file.endswith('.py') and not file.startswith('__'):
            file_path = os.path.join(root, file)
            try:
                # Try to import the module
                module_name = file_path.replace('/', '.').replace('.py', '')
                module_name = module_name.replace('dashboard.backend.tests.', '')
                __import__(module_name)
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")

if errors:
    print("Import errors found:")
    for error in errors:
        print(error)
else:
    print("No import errors found")