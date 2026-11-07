"""Convert connector raw-message staging JSON to self-contained EML archives.

No network access. Never modifies an existing email record.
"""
import base64
import hashlib
import json
import os
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

root = Path(sys.argv[1]).resolve()
for source in sorted(root.glob('*.raw.json')):
    data = json.loads(source.read_text())
    encoded = data['raw']
    raw = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
    message = BytesParser(policy=policy.default).parsebytes(raw)
    target = source.with_suffix('').with_suffix('.eml')
    if target.exists():
        if target.read_bytes() != raw:
            raise RuntimeError(f'Existing archive differs: {target.name}')
    else:
        with target.open('xb') as out:
            out.write(raw)
        target.chmod(0o600)
    metadata = {
        'gmail_id': data['id'], 'gmail_thread_id': data['thread_id'],
        'labels': data.get('label_ids', []),
        'from': str(message.get('From', '')),
        'to': str(message.get('To', '')), 'cc': str(message.get('Cc', '')),
        'date': str(message.get('Date', '')), 'subject': str(message.get('Subject', '')),
        'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
        'attachments': [str(p.get_filename()) for p in message.walk() if p.get_filename()],
    }
    sidecar = target.with_suffix('.metadata.json')
    if not sidecar.exists():
        with sidecar.open('x') as out:
            json.dump(metadata, out, ensure_ascii=False, indent=2)
            out.write('\n')
        sidecar.chmod(0o600)
    # The verified EML contains precisely the decoded source, including attachments.
    source.unlink()
print(json.dumps({'eml_files': len(list(root.glob('*.eml')))}))
