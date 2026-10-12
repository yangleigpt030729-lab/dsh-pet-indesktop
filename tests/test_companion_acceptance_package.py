import hashlib
import json
import zipfile
from pathlib import Path
import scripts.package_companion_test as packager
import pytest
from scripts.package_companion_test import build, verify, PREFIX


def source(tmp_path):
    root = tmp_path/'source'
    (root/'pet').mkdir(parents=True)
    (root/'requirements.txt').write_text('PySide6>=6.5\n')
    (root/'pet'/'main.py').write_text('print("synthetic source")\n')
    return root


def test_source_package_is_deterministic_and_excludes_user_state(tmp_path):
    root = source(tmp_path)
    for name in ['config.json', 'companion_memory.sqlite3', 'companion_proactive.sqlite3-journal', '.env', 'private.log']:
        (root/'pet'/name).write_text('private synthetic excluded data')
    first, second = tmp_path/'a.zip', tmp_path/'b.zip'
    assert build(root, first) == build(root, second)
    assert verify(first) == 2
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist()) == {PREFIX+'requirements.txt', PREFIX+'pet/main.py', PREFIX+'ACCEPTANCE-SHA256.json'}


@pytest.mark.parametrize('kind', ['key_literal', 'json_key', 'symlink', 'project_key', 'pem_body'])
def test_package_rejects_secrets_and_preserves_previous_output(tmp_path, kind):
    root = source(tmp_path)
    output = tmp_path/'previous.zip'
    build(root, output)
    before = output.read_bytes()
    if kind == 'key_literal':
        (root/'pet'/'bad.py').write_text('value="'+'sk-'+'A'*32+'"')
    elif kind == 'json_key':
        (root/'pet'/'manifest.json').write_text(json.dumps({'nested':{'api_key':'synthetic-private-value'}}))
    elif kind == 'project_key':
        (root/'pet'/'bad.py').write_text('value="'+'sk-proj-'+'A'*32+'"')
    elif kind == 'pem_body':
        (root/'pet'/'bad.py').write_text('value="""'+'-----BEGIN PRIVATE KEY-----'+'\n'+'A'*64+'\n-----END PRIVATE KEY-----"""')
    else:
        try:
            (root/'pet'/'link.py').symlink_to(root/'pet'/'main.py')
        except OSError:
            pytest.skip('host does not permit symlinks')
    with pytest.raises(ValueError):
        build(root, output)
    assert output.read_bytes() == before


def test_modified_archive_fails_checksum_verification(tmp_path):
    root = source(tmp_path)
    output = tmp_path/'source.zip'
    build(root, output)
    damaged = tmp_path/'damaged.zip'
    with zipfile.ZipFile(output) as old, zipfile.ZipFile(damaged, 'w') as new:
        for name in old.namelist():
            new.writestr(name, b'changed' if name.endswith('main.py') else old.read(name))
    with pytest.raises(ValueError, match='checksum'):
        verify(damaged)
    assert hashlib.sha256(damaged.read_bytes()).digest() != hashlib.sha256(output.read_bytes()).digest()


def test_checker_can_be_packaged_without_ignoring_real_secrets(tmp_path):
    root = source(tmp_path)
    (root/'pet'/'checker.py').write_bytes(Path(packager.__file__).read_bytes())
    assert build(root, tmp_path/'source.zip')
