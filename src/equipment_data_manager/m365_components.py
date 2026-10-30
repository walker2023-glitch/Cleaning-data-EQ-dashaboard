"""Offline installed/packaged dependency check. NEVER constructs an OAuth client."""
import argparse
import json
from pathlib import Path
from equipment_data_manager.m365_config import require_local
from equipment_data_manager.storage.contracts import StorageError


def component_check():
    try:
        import msal
        import requests
    except ImportError:raise StorageError('m365_dependencies_missing') from None
    from equipment_data_manager.storage.readonly_graph import ReadOnlyGraphAdapter
    from equipment_data_manager.storage.https_transport import ReadOnlyHttpsTransport
    if not Path(requests.certs.where()).is_file():raise StorageError('m365_tls_roots_missing')
    cache=msal.SerializableTokenCache()
    if json.loads(cache.serialize())!={}:raise StorageError('m365_component_check_failed')
    return dict(status='offline_components_available',msal=msal.__version__,requests=requests.__version__,
        tls_roots_available=True,authentication_attempted=False,network_contacted=False,publication_enabled=False)


def write_component_check(path):
    path=Path(path);require_local(path.parent)
    report=component_check()
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(report,stream,sort_keys=True)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:write_component_check(args.output);return 0
    except Exception:return 1


if __name__=='__main__':raise SystemExit(main())
