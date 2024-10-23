import os
import shutil

def replace_py_with_pyc(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'venv' in dirpath:
            continue
        
        for filename in filenames:
            if filename.endswith('.py') and not filename == 'compile.py':
                py_file = os.path.join(dirpath, filename)
                pyc_file = os.path.join(dirpath, '__pycache__', f'{filename[:-3]}.cpython-{os.sys.version_info.major}{os.sys.version_info.minor}.pyc')

                if os.path.exists(pyc_file):
                    print(f'Replacing {py_file} with {pyc_file} as {filename[:-3]}.pyc')
                    os.remove(py_file)

                    shutil.move(pyc_file, os.path.join(dirpath, f'{filename[:-3]}.pyc'))
                else:
                    print(f'No .pyc file found for {py_file}')


if __name__ == '__main__':
    replace_py_with_pyc('.')
