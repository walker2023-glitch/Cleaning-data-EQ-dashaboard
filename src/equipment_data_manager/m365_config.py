"""Strict IT-owned test-pilot configuration. Parsing NEVER starts SDK/network I/O."""
from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from equipment_data_manager.auth.msal_session import OrganizationalConfig
from equipment_data_manager.processing.models import ReportType
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.graph_adapter import GraphScope
from equipment_data_manager.settings import candidate_location_error

SELECTED_SCOPES = frozenset({'Sites.Selected','Files.SelectedOperations.Selected',
    'Lists.SelectedOperations.Selected','ListItems.SelectedOperations.Selected'})


@dataclass(frozen=True, repr=False)
class SyntheticFile:
    item_id: str
    report_type: ReportType
    sha256: str


@dataclass(frozen=True, repr=False)
class TestPilotConfig:
    organization: OrganizationalConfig
    scope: GraphScope
    files: tuple[SyntheticFile, ...]
    cache_path: Path
    enabled: bool = False
    authorization_reference: str = ''

    def validate(self):
        if (not isinstance(self.organization,OrganizationalConfig) or not isinstance(self.scope,GraphScope)
                or not isinstance(self.cache_path,Path) or type(self.files) is not tuple
                or any(not isinstance(f,SyntheticFile) for f in self.files)):
            raise StorageError('m365_test_configuration_invalid')
        if (type(self.enabled) is not bool or not isinstance(self.authorization_reference,str)
                or not self.authorization_reference.strip() or len(self.authorization_reference)>300
                or not set(self.organization.scopes) <= SELECTED_SCOPES
                or len(set(self.organization.scopes)) != len(self.organization.scopes)
                or not self.files or len(self.files)>128 or self.scope.probe_folder_id is not None
                or len(self.scope.raw_folder_ids)!=3 or len(set(self.scope.raw_folder_ids))!=3
                or not self.scope.download_hosts
                or any(not h.endswith('.sharepoint.com') or not re.fullmatch(r'[a-z0-9][a-z0-9.-]*',h)
                       for h in self.scope.download_hosts)
                or len({f.item_id for f in self.files})!=len(self.files)
                or any(not re.fullmatch(r'[A-Za-z0-9!_-]{1,200}',f.item_id)
                       or not isinstance(f.report_type,ReportType) or not re.fullmatch(r'[a-f0-9]{64}',f.sha256)
                       for f in self.files)):
            raise StorageError('m365_test_configuration_invalid')
        require_local(self.cache_path.parent)
        if (self.cache_path.name != 'msal-cache.bin'
                or self.cache_path.parent.name.casefold()!=self.organization.client_id
                or self.cache_path.parent.parent.name.casefold()!=self.organization.tenant_id):
            raise StorageError('m365_cache_namespace_invalid')
        return self

    def authorize(self, *, operator_authorized=False):
        self.validate()
        if self.enabled is not True or operator_authorized is not True:
            raise StorageError('m365_test_pilot_not_authorized')


def require_local(path):
    path=Path(path).absolute()
    if candidate_location_error(path) or any(p.is_symlink() or p.is_junction() for p in (path,*path.parents)):
        raise StorageError('m365_local_storage_required')
    return path


def load_test_config(path):
    try:
        path=Path(path).absolute()
        if path.stat().st_size>256*1024:raise ValueError
        data=tomllib.loads(path.read_text(encoding='utf-8'))
        if set(data)!={'test_pilot','organization','resources','cache','synthetic_files'}:raise ValueError
        pilot,org,res,cache=data['test_pilot'],data['organization'],data['resources'],data['cache']
        if (set(pilot)!={'enabled','environment','authorization_reference'} or pilot['environment']!='nonproduction'
                or set(org)!={'tenant_id','client_id','scopes'}
                or set(res)!={'site_id','drive_id','raw_folder_ids','download_hosts'} or set(cache)!={'path'}
                or type(org['scopes']) is not list or type(res['raw_folder_ids']) is not list
                or type(res['download_hosts']) is not list or not isinstance(cache['path'],str) or not cache['path'].strip()
                or type(data['synthetic_files']) is not list):raise ValueError
        files=[]
        for entry in data['synthetic_files']:
            if set(entry)!={'item_id','report_type','sha256'}:raise ValueError
            files.append(SyntheticFile(entry['item_id'],ReportType(entry['report_type']),entry['sha256']))
        return TestPilotConfig(OrganizationalConfig(org['tenant_id'],org['client_id'],tuple(org['scopes'])),
            GraphScope(res['site_id'],res['drive_id'],tuple(res['raw_folder_ids']),download_hosts=tuple(res['download_hosts'])),
            tuple(files),(path.parent/cache['path']).absolute(),pilot['enabled'],pilot['authorization_reference']).validate()
    except StorageError:raise
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        raise StorageError('m365_test_configuration_invalid') from None
