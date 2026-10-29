"""Private local preferences and folder checks. No credentials or data migration."""

from dataclasses import dataclass, field
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib

from equipment_data_manager.monthly import Workspace
from equipment_data_manager.processing.models import ProcessingError

FOLDER_KEYS = ('raw_folder', 'candidate_folder', 'approved_folder')


def default_settings_path():
    if sys.platform == 'win32':
        root = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local'))
    elif sys.platform == 'darwin':
        root = Path.home() / 'Library/Application Support'
    else:
        root = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return root / 'EquipmentDataManager/settings.toml'


@dataclass(frozen=True)
class Preferences:
    guided: bool = True
    detail: str = 'detailed'
    output_format: str = 'powerbi'
    candidate_local_confirmed: bool = False
    reporting_period: str = ''


@dataclass(frozen=True)
class UserSettings:
    folders: dict[str, str] = field(default_factory=lambda: dict.fromkeys(FOLDER_KEYS, ''))
    preferences: Preferences = field(default_factory=Preferences)

    def workspace(self):
        if any(not self.folders[k].strip() for k in FOLDER_KEYS):
            raise ProcessingError('settings_missing_folders')
        return Workspace(**{k: Path(v).resolve() for k, v in self.folders.items()}).validate()


def parse_settings(text, *, base: Path):
    """Strict versioned schema; accept the existing three-key workspace on import."""
    try:
        data = tomllib.loads(text)
        if set(data) == set(FOLDER_KEYS):
            folders, prefs = data, Preferences()
        else:
            if set(data) != {'version', 'folders', 'preferences'} or type(data['version']) is not int or data['version'] not in (1, 2):
                raise ValueError
            folders, p = data['folders'], data['preferences']
            expected = {'guided', 'detail', 'output_format', 'candidate_local_confirmed'}
            if data['version'] == 2:
                expected.add('reporting_period')
            if set(p) != expected:
                raise ValueError
            period = p.get('reporting_period', '')
            if not isinstance(period, str):
                raise ValueError
            if period:
                from equipment_data_manager.processing.cleaners import validate_period
                try:
                    validate_period(period)
                except ProcessingError:
                    raise ValueError from None
            if (type(p['guided']) is not bool or type(p['candidate_local_confirmed']) is not bool
                    or p['detail'] not in ('brief', 'detailed') or p['output_format'] not in ('legacy', 'powerbi')):
                raise ValueError
            prefs = Preferences(**p)
        if not isinstance(folders, dict) or set(folders) != set(FOLDER_KEYS) or any(not isinstance(v, str) for v in folders.values()):
            raise ValueError
        resolved = {k: str((base / v).resolve()) if v.strip() else '' for k, v in folders.items()}
        return UserSettings(resolved, prefs)
    except (ValueError, TypeError, KeyError, OSError):
        raise ProcessingError('settings_invalid') from None


def encode_settings(settings):
    # JSON basic strings are TOML-compatible for paths/Unicode/control characters.
    if set(settings.folders) != set(FOLDER_KEYS) or any(not isinstance(v,str) for v in settings.folders.values()):
        raise ProcessingError('settings_invalid')
    p = settings.preferences
    body = ['version = 2', '', '[folders]']
    body.extend(f'{k} = {json.dumps(settings.folders[k], ensure_ascii=False)}' for k in FOLDER_KEYS)
    body.extend(['', '[preferences]', f'guided = {str(p.guided).lower()}',
        f'detail = "{p.detail}"', f'output_format = "{p.output_format}"',
        f'candidate_local_confirmed = {str(p.candidate_local_confirmed).lower()}',
        f'reporting_period = {json.dumps(p.reporting_period)}', ''])
    text = '\n'.join(body)
    parse_settings(text, base=Path.cwd())  # Reject accidental extra/malformed state before writing.
    return text


class SettingsStore:
    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        if self.path.suffix.lower() != ".toml":
            raise ProcessingError("settings_invalid")

    def load(self):
        try:
            if self.path.is_symlink():
                raise ProcessingError('settings_invalid')
            return parse_settings(self.path.read_text(encoding='utf-8'), base=self.path.parent)
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError):
            raise ProcessingError('settings_unavailable') from None

    def save(self, settings):
        text = encode_settings(settings)
        temporary = None
        try:
            if self.path.is_symlink():
                raise ProcessingError('settings_unavailable')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                    prefix='.settings-', suffix='.tmp', dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise ProcessingError('settings_unavailable') from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def known_sync_roots():
    roots = [Path(os.environ[k]).resolve() for k in ('OneDrive', 'OneDriveCommercial', 'OneDriveConsumer') if os.environ.get(k)]
    if sys.platform == 'win32':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\OneDrive\Accounts') as accounts:
                for index in range(winreg.QueryInfoKey(accounts)[0]):
                    with winreg.OpenKey(accounts, winreg.EnumKey(accounts, index)) as account:
                        try:
                            roots.append(Path(winreg.QueryValueEx(account, 'UserFolder')[0]).resolve())
                        except OSError:
                            pass
        except OSError:
            pass
    return roots


def candidate_location_error(path: Path):
    """Conservative local checks, NOT proof that every third-party sync client is absent."""
    try:
        if str(path).startswith(("\\\\", "//")):
            return "Use a folder on this computer, not a shared network location."
        resolved = path.resolve()
        if str(path).startswith(('\\\\', '//')) or str(resolved).startswith(('\\\\', '//')):
            return 'Use a folder on this computer, not a shared network location.'
        if any(resolved.is_relative_to(root) for root in known_sync_roots()):
            return 'Candidate history cannot be stored in a OneDrive-synchronized folder. Choose a local folder.'
        if any(part.casefold().startswith(('onedrive', 'sharepoint', 'dropbox', 'google drive'))
                or part.casefold() == 'box' for part in resolved.parts):
            return 'This appears to be a synchronized folder. Choose a local candidate folder outside sync services.'
        if sys.platform == 'win32':
            if ctypes.windll.kernel32.GetDriveTypeW(str(resolved.anchor)) != 3:  # DRIVE_FIXED
                return 'Choose a fixed local disk for candidate history; network/removable/unknown drives are not supported.'
            # Reject folder redirection and cloud placeholders anywhere along this path.
            for item in (path, *path.parents):
                if item.exists():
                    attrs = getattr(item.stat(follow_symlinks=False), 'st_file_attributes', 0)
                    if item.is_symlink() or item.is_junction() or attrs & (0x400 | 0x40000 | 0x400000):
                        return 'Candidate history cannot use redirected or cloud-managed folders. Ask IT for a trusted local location.'
        elif sys.platform.startswith('linux'):
            mounts = Path('/proc/mounts').read_text().splitlines()
            matches = [(len(row[1]), row[2]) for line in mounts if len(row := line.split()) >= 3
                       and resolved.is_relative_to(Path(row[1].replace('\\040', ' ')))]
            if matches:
                filesystem = max(matches)[1]
                if filesystem.startswith(('nfs', 'cifs', 'smb', 'fuse', '9p', 'davfs')):
                    return 'Candidate history needs a local disk, outside network and synchronized mounts.'
        return ''
    except (OSError, ValueError, RuntimeError):
        return 'This location could not be checked. Choose a trusted local folder or ask your maintainer.'


@dataclass(frozen=True)
class FolderCheck:
    messages: dict[str, str]
    missing: tuple[Path, ...] = ()
    valid: bool = False
    workspace: Workspace | None = None


def validate_locations(settings: UserSettings, *, probe=False):
    messages, missing = {}, []
    paths = {}
    for key, value in settings.folders.items():
        try:
            if not value.strip() or not Path(value).is_absolute():
                messages[key] = 'Select a folder using Browse.'
            else:
                paths[key] = Path(value).resolve()
        except (OSError, ValueError, RuntimeError):
            messages[key] = 'This path cannot be resolved. Select another folder.'
    if messages:
        return FolderCheck(messages)
    try:
        Workspace(**paths).validate()
    except (OSError, ValueError, RuntimeError):
        return FolderCheck({key: 'Folders must be separate; one cannot be inside another.' for key in FOLDER_KEYS})
    candidate_error = candidate_location_error(Path(settings.folders['candidate_folder']))
    if candidate_error:
        messages['candidate_folder'] = candidate_error
    elif not settings.preferences.candidate_local_confirmed:
        messages['candidate_folder'] = 'Confirm that candidate history is on this computer and is not synchronized or shared.'
    for key, path in paths.items():
        if key in messages:
            continue
        try:
            if not path.exists():
                parent = path.parent
                while not parent.exists():
                    parent = parent.parent
                if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
                    raise PermissionError
                missing.append(path)
                continue
            if not path.is_dir():
                messages[key] = 'This is a file, not a folder. Select a folder.'
                continue
            with os.scandir(path) as entries:
                next(entries, None)
            if key != 'raw_folder' and not os.access(path, os.W_OK | os.X_OK):
                raise PermissionError
            if probe and key == 'candidate_folder':
                with tempfile.TemporaryFile(dir=path):
                    pass
        except OSError:
            messages[key] = 'Folder unavailable or access denied. Check local availability and permissions; synchronization is unverified.'
    if messages:
        return FolderCheck(messages)
    return FolderCheck({k: 'Needs creation — confirmation required.' if paths[k] in missing
                        else 'Ready (reserved only).' if k == 'approved_folder' else 'Ready.' for k in FOLDER_KEYS},
                       tuple(missing), not missing, Workspace(**paths) if not missing else None)


def create_confirmed_folders(settings):
    """Called only after GUI confirmation of the listed missing locations."""
    check = validate_locations(settings)
    if not check.valid and not check.missing:
        return check
    try:
        for path in check.missing:
            path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return FolderCheck({k: 'Folder could not be created. Check permissions; existing files were not changed.' for k in FOLDER_KEYS})
    return validate_locations(settings, probe=True)
