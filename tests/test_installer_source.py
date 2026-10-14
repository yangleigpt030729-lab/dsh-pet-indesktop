"""Real PyInstaller archives prove provenance rejection; these are not native EXEs."""
import json
from pathlib import Path
import zipfile

import pytest
from PyInstaller.archive.writers import CArchiveWriter, ZlibArchiveWriter
from scripts import package_companion_test as package
from scripts import verify_installer_source as provenance

ROOT = Path(__file__).resolve().parents[1]


def frozen_exe(directory, sources):
    directory.mkdir(parents=True, exist_ok=True)
    pyz = directory/'modules.pyz'
    codes = {name:compile(text, 'a/different/build/machine/'+name+'.py', 'exec') for name,text in sources.items()}
    entries = [(name, name.replace('.', '/')+'.py', 'PYMODULE') for name in sources]
    ZlibArchiveWriter(str(pyz), entries, codes)
    exe = directory/provenance.EXE
    CArchiveWriter(str(exe), [('PYZ.pyz', str(pyz), False, 'z')], 'python312.dll')
    pyz.unlink()
    return exe


def build_fixture(tmp_path):
    root = tmp_path/'source'; root.mkdir()
    (root/'requirements.txt').write_text('synthetic build prerequisites\n')
    sources = {}
    for name in provenance.MODULES:
        path=root/(name.replace('.', '/')+'.py');path.parent.mkdir(parents=True,exist_ok=True)
        sources[name]="VALUE = 'current repair'\ndef answer():\n    return VALUE\n"
        path.write_text(sources[name])
    work=tmp_path/'fresh-work';work.mkdir()
    package.build(root,work/'reviewed-source.zip')
    with zipfile.ZipFile(work/'reviewed-source.zip') as archive: archive.extractall(work)
    app=work/'dsh-pet-companion-win10'/'dist-onedir'/'dsh-pet-standalone-webm-chat'
    exe=frozen_exe(app,sources)
    portable=app.parent/'dsh-pet-standalone-webm-chat-portable.zip'
    with zipfile.ZipFile(portable,'w') as archive: archive.write(exe,provenance.EXE)
    return root,work,exe,portable,sources


def test_real_archives_bind_current_source_and_zip_and_keep_previous_receipt(tmp_path):
    root,work,exe,portable,_=build_fixture(tmp_path)
    receipt=tmp_path/'source-build-manifest.json'
    result=provenance.record(root,work,receipt)
    assert result['version']=='1.0.1' and result['exe_sha256']==provenance.sha256(exe)
    assert result['portable_sha256']==provenance.sha256(portable)
    assert len(result['repair_source_sha256'])==8
    assert provenance.verify(root,work,receipt)==result
    before=receipt.read_bytes()
    with pytest.raises(FileExistsError): provenance.record(root,work,receipt)
    assert receipt.read_bytes()==before


@pytest.mark.parametrize('fault',['old_exe','old_zip','source_changed','staged_changed','archive_changed','receipt_changed'])
def test_old_or_modified_build_is_refused_instead_of_relabelled_v101(tmp_path,fault):
    root,work,exe,portable,sources=build_fixture(tmp_path)
    receipt=tmp_path/'receipt.json';provenance.record(root,work,receipt)
    module=provenance.MODULES[0];relative=module.replace('.', '/')+'.py'
    if fault=='old_exe':
        sources[module]="VALUE = 'old v1.0.0'\ndef answer():\n    return VALUE\n"
        frozen_exe(exe.parent,sources)
    elif fault=='old_zip':
        with zipfile.ZipFile(portable,'w') as archive: archive.writestr(provenance.EXE,b'old portable executable')
    elif fault=='source_changed': (root/relative).write_text('VALUE=42\n')
    elif fault=='staged_changed': (work/'dsh-pet-companion-win10'/relative).write_text('VALUE=42\n')
    elif fault=='archive_changed':
        with zipfile.ZipFile(work/'reviewed-source.zip','a') as archive: archive.writestr('unexpected.txt',b'changed')
    else:
        data=json.loads(receipt.read_text());data['version']='1.0.0';receipt.write_text(json.dumps(data))
    with pytest.raises(ValueError): provenance.verify(root,work,receipt)


def test_actual_repair_sources_survive_real_pyz_filename_normalization(tmp_path):
    from PyInstaller.archive.readers import CArchiveReader
    sources={name:(ROOT/(name.replace('.', '/')+'.py')).read_bytes() for name in provenance.MODULES}
    exe=frozen_exe(tmp_path/'real-module-archive',sources)
    pyz=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
    by_path={name.replace('.', '/')+'.py':data for name,data in sources.items()}
    assert len(provenance.verify_frozen(pyz,by_path))==8
    # A missing final repair module fails, including identical filenames/layout/version.
    pyz.toc.pop(provenance.MODULES[-1])
    with pytest.raises(ValueError,match='Frozen repair module'): provenance.verify_frozen(pyz,by_path)


def test_signature_checks_nested_function_logic_and_constants():
    old=compile('def speech():\n    return "old"\n','old_machine.py','exec')
    new=compile('def speech():\n    return "fixed"\n','new_machine.py','exec')
    same=compile('def speech():\n    return "fixed"\n','elsewhere.py','exec')
    assert provenance.code_signature(old)!=provenance.code_signature(new)
    assert provenance.code_signature(new)==provenance.code_signature(same)


def test_nonmandatory_application_module_also_cannot_contain_old_code(tmp_path):
    from PyInstaller.archive.readers import CArchiveReader
    sources={name:'VALUE=1\n' for name in provenance.MODULES}
    sources['pet.other_feature']='VALUE=2\n'
    exe=frozen_exe(tmp_path/'additional-module',sources)
    pyz=CArchiveReader(str(exe)).open_embedded_archive('PYZ.pyz')
    by_path={name.replace('.', '/')+'.py':text.encode() for name,text in sources.items()}
    assert len(provenance.verify_frozen(pyz,by_path))==9
    by_path['pet/other_feature.py']=b'VALUE=3\n'
    with pytest.raises(ValueError,match='other_feature'): provenance.verify_frozen(pyz,by_path)


def test_missing_receipt_or_missing_fresh_source_archive_never_accepts_old_zip(tmp_path):
    root,work,_,_,_=build_fixture(tmp_path)
    with pytest.raises(FileNotFoundError): provenance.verify(root,work,tmp_path/'no-receipt.json')
    (work/'reviewed-source.zip').unlink()
    with pytest.raises(FileNotFoundError): provenance.record(root,work,tmp_path/'new-receipt.json')
    assert not (tmp_path/'new-receipt.json').exists()
