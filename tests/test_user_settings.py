"""Private temporary folders and invented settings only; no Microsoft access."""
from dataclasses import replace
from pathlib import Path

import pytest

from equipment_data_manager.settings import (
    FOLDER_KEYS, Preferences, SettingsStore, UserSettings, candidate_location_error,
    create_confirmed_folders, encode_settings, parse_settings, validate_locations,
)
from equipment_data_manager.processing.models import ProcessingError


@pytest.fixture
def settings(tmp_path):
    return UserSettings({key:str(tmp_path / key) for key in FOLDER_KEYS},Preferences(candidate_local_confirmed=True))


def existing(settings):
    for folder in settings.folders.values():
        Path(folder).mkdir()
    return settings


def test_first_run_defaults_and_no_side_effects(tmp_path):
    store=SettingsStore(tmp_path / 'private/settings.toml')
    assert store.load() is None and not store.path.parent.exists()
    defaults=UserSettings()
    assert defaults.preferences.guided and defaults.preferences.detail=='detailed'
    assert defaults.preferences.output_format=='powerbi'
    assert not validate_locations(defaults).valid


def test_persistence_and_safe_reset_preserve_all_existing_data(tmp_path,settings):
    existing(settings)
    report=Path(settings.folders['raw_folder']) / 'original.csv'
    report.write_bytes(b'SYNTHETIC ORIGINAL')
    history=Path(settings.folders['candidate_folder']) / 'retained.txt'
    history.write_bytes(b'SYNTHETIC HISTORY')
    store=SettingsStore(tmp_path / 'private/settings.toml')
    choices=replace(settings,preferences=Preferences(False,'brief','legacy',True))
    store.save(choices)
    assert SettingsStore(store.path).load()==choices
    store.save(UserSettings())
    assert store.load()==UserSettings()
    assert report.read_bytes()==b'SYNTHETIC ORIGINAL' and history.read_bytes()==b'SYNTHETIC HISTORY'


def test_missing_folders_require_separate_confirmed_creation(settings):
    check=validate_locations(settings,probe=True)
    assert not check.valid and len(check.missing)==3
    assert all(not Path(value).exists() for value in settings.folders.values())
    result=create_confirmed_folders(settings)
    assert result.valid and result.workspace==settings.workspace()
    assert all(Path(value).is_dir() for value in settings.folders.values())
    assert list(Path(settings.folders['approved_folder']).iterdir())==[]


@pytest.mark.parametrize('key',FOLDER_KEYS)
def test_missing_selection_and_file_instead_of_folder_are_rejected(settings,key,tmp_path):
    folders=dict(settings.folders);folders[key]=''
    assert not validate_locations(replace(settings,folders=folders)).valid
    file=tmp_path / 'not-a-folder';file.write_text('SYNTHETIC')
    folders[key]=str(file)
    result=validate_locations(replace(settings,folders=folders))
    assert 'file, not a folder' in result.messages[key]


@pytest.mark.parametrize('nested',['','/child'])
def test_overlapping_folders_fail_before_creation(settings,nested):
    folders=dict(settings.folders);folders['approved_folder']=folders['raw_folder']+nested
    result=create_confirmed_folders(replace(settings,folders=folders))
    assert not result.valid and all('separate' in text for text in result.messages.values())
    assert not Path(folders['raw_folder']).exists()


def test_access_denied_has_safe_message_and_does_not_modify_data(settings,monkeypatch):
    existing(settings)
    def denied(*args):raise PermissionError('SYNTHETIC_PRIVATE_PATH')
    monkeypatch.setattr('equipment_data_manager.settings.os.scandir',denied)
    check=validate_locations(settings,probe=True)
    assert not check.valid and all('access denied' in text for text in check.messages.values())
    assert 'SYNTHETIC_PRIVATE' not in repr(check)


def test_candidate_probe_failure_prevents_save_eligibility(settings,monkeypatch):
    existing(settings)
    monkeypatch.setattr('equipment_data_manager.settings.tempfile.TemporaryFile',lambda **kwargs: (_ for _ in ()).throw(PermissionError()))
    result=validate_locations(settings,probe=True)
    assert not result.valid and 'access denied' in result.messages['candidate_folder']


def test_local_storage_confirmation_is_required(settings):
    result=validate_locations(replace(settings,preferences=Preferences()))
    assert not result.valid and 'Confirm' in result.messages['candidate_folder']


@pytest.mark.parametrize('name',['OneDrive - Example','SharePoint','Dropbox','Google Drive','Box'])
def test_known_synced_names_block_candidate_history(tmp_path,name):
    assert candidate_location_error(tmp_path / name / 'candidates')


def test_custom_onedrive_root_and_unc_are_blocked(tmp_path,monkeypatch):
    root=tmp_path / 'custom-sync-name'
    monkeypatch.setenv('OneDriveCommercial',str(root))
    assert 'OneDrive' in candidate_location_error(root / 'history')
    assert 'network' in candidate_location_error(Path('//host/share/history'))


def test_sync_candidate_check_fails_before_any_confirmed_folder_creation(settings,monkeypatch):
    monkeypatch.setenv('OneDrive',settings.folders['candidate_folder'])
    check=create_confirmed_folders(settings)
    assert not check.valid and not any(Path(p).exists() for p in settings.folders.values())


def test_failed_atomic_replace_keeps_previous_settings(tmp_path,settings,monkeypatch):
    store=SettingsStore(tmp_path / 'settings.toml');store.save(settings)
    previous=store.path.read_bytes()
    def fail(*args):raise PermissionError('SYNTHETIC_PRIVATE')
    monkeypatch.setattr('equipment_data_manager.settings.os.replace',fail)
    with pytest.raises(ProcessingError,match='^settings_unavailable$'):store.save(UserSettings())
    assert store.path.read_bytes()==previous
    assert list(tmp_path.glob('.settings-*.tmp'))==[]


@pytest.mark.parametrize('bad',['not toml','version=2', 'version=true',
    'version=1\nfolders=[]\npreferences={}',
    'raw_folder="a"\ncandidate_folder="b"\napproved_folder="c"\ntoken="SYNTHETIC_PRIVATE"'])
def test_corrupted_or_unknown_settings_rejected_without_echo(tmp_path,bad):
    path=tmp_path / 'settings.toml';path.write_text(bad)
    with pytest.raises(ProcessingError,match='^settings_invalid$'):SettingsStore(path).load()
    assert path.read_text()==bad


@pytest.mark.parametrize('field,value',[('guided','"yes"'),('detail','"expert"'),('output_format','"approved"'),('candidate_local_confirmed','1')])
def test_invalid_preference_types_rejected(tmp_path,field,value):
    text=encode_settings(UserSettings())
    lines=text.splitlines()
    text='\n'.join(field+' = '+value if line.startswith(field+' =') else line for line in lines)
    with pytest.raises(ProcessingError,match='settings_invalid'):parse_settings(text,base=tmp_path)


def test_legacy_import_resolves_relative_paths_and_has_no_implicit_trust(tmp_path):
    settings=parse_settings('raw_folder="raw"\ncandidate_folder="candidate"\napproved_folder="approved"',base=tmp_path)
    assert settings.folders['raw_folder']==str(tmp_path / 'raw')
    assert not settings.preferences.candidate_local_confirmed
    assert not (tmp_path / 'raw').exists()


def test_sanitized_template_contains_no_current_paths_or_secrets(settings,tmp_path):
    template=encode_settings(UserSettings())
    assert str(tmp_path) not in template and 'password' not in template and 'token' not in template
    assert parse_settings(template,base=tmp_path)==UserSettings()


def test_permission_failure_during_creation_is_safe(settings,monkeypatch):
    real=Path.mkdir
    def fail(path,*args,**kwargs):
        if path==Path(settings.folders['candidate_folder']):raise PermissionError
        return real(path,*args,**kwargs)
    monkeypatch.setattr(Path,'mkdir',fail)
    result=create_confirmed_folders(settings)
    assert not result.valid and 'could not be created' in result.messages['candidate_folder']
    assert not Path(settings.folders['approved_folder']).exists()


def test_windows_nonfixed_drive_is_blocked_without_host_privileges(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import equipment_data_manager.settings as module
    monkeypatch.setattr(module,'sys',SimpleNamespace(platform='win32'))
    monkeypatch.setattr(module,'known_sync_roots',lambda:[])
    monkeypatch.setattr(module.ctypes,'windll',SimpleNamespace(kernel32=SimpleNamespace(GetDriveTypeW=lambda anchor:4)),raising=False)
    assert 'fixed local disk' in candidate_location_error(tmp_path / 'candidate')


def test_settings_file_cannot_target_a_csv_report(tmp_path):
    source=tmp_path / 'raw.csv';source.write_bytes(b'SYNTHETIC ORIGINAL')
    with pytest.raises(ProcessingError,match='settings_invalid'):
        SettingsStore(source)
    assert source.read_bytes()==b'SYNTHETIC ORIGINAL'


def test_version_one_settings_load_without_month_and_upgrade_losslessly(tmp_path, settings):
    text=encode_settings(settings).replace('version = 2','version = 1')
    text='\n'.join(line for line in text.splitlines() if not line.startswith('reporting_period ='))
    original=parse_settings(text,base=tmp_path)
    assert original==settings and original.preferences.reporting_period==''
    selected=replace(original,preferences=replace(original.preferences,reporting_period='2026-01'))
    store=SettingsStore(tmp_path/'private/settings.toml');store.save(selected)
    assert store.load()==selected and 'version = 2' in store.path.read_text()
    assert original.folders==selected.folders


@pytest.mark.parametrize('value',['"2026-13"','"2026-1"','"0000-01"','"January"','true','1','[]'])
def test_invalid_saved_reporting_month_is_rejected_without_rewriting(tmp_path,value):
    text=encode_settings(UserSettings()).replace('reporting_period = ""','reporting_period = '+value)
    path=tmp_path/'settings.toml';path.write_text(text)
    with pytest.raises(ProcessingError,match='settings_invalid'):
        SettingsStore(path).load()
    assert path.read_text()==text


def test_empty_reporting_month_is_not_a_report_inference_or_template_leak(tmp_path):
    defaults=parse_settings(encode_settings(UserSettings()),base=tmp_path)
    assert defaults.preferences.reporting_period==''
    assert defaults==UserSettings()
