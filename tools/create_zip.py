import os
import zipfile

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
zip_path = os.path.join(root, 'plotwatch_export.zip')

print(f"Creating zip at: {zip_path}")

with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for dirpath, dirnames, filenames in os.walk(root):
        # skip the virtualenv directory at the repo root
        rel = os.path.relpath(dirpath, root)
        if rel == 'env' or rel.startswith('env' + os.sep):
            continue
        # skip __pycache__ directories
        if '__pycache__' in dirpath:
            continue
        for fname in filenames:
            fp = os.path.join(dirpath, fname)
            # don't include the zip we're creating
            if os.path.abspath(fp) == os.path.abspath(zip_path):
                continue
            arcname = os.path.relpath(fp, root)
            z.write(fp, arcname)

print('zip creation complete')
print(zip_path)
