"""Authorized TEST-only read pipeline. No auth/network at module import or UI startup."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import shutil
from threading import Event
from uuid import uuid4

from equipment_data_manager.auth.managed_msal import create_session
from equipment_data_manager.m365_config import load_test_config, require_local
from equipment_data_manager.processing.models import ReportType, ProcessingStatus
from equipment_data_manager.storage.contracts import StorageError
from equipment_data_manager.storage.graph_adapter import _header
from equipment_data_manager.storage.https_transport import ReadOnlyHttpsTransport
from equipment_data_manager.storage.readonly_graph import ReadOnlyGraphAdapter
from equipment_data_manager.ui.workflow import DesktopWorkflow, SourceFile


class VerifiedGraphSource:
    def __init__(self,adapter,config,selections):
        self.adapter,self.config,self.selections=adapter,config,dict(selections)
        self.downloads={}

    def read(self,source):
        entry=self.selections.get(source.reference)
        allowed=next((f for f in self.config.files if entry and f.item_id==entry.item_id),None)
        if entry is None or entry.name!=source.name or allowed is None:
            raise StorageError('storage_reference_rejected')
        folder=self.config.scope.raw_folder_ids[list(ReportType).index(allowed.report_type)]
        if entry.parent_id!=folder or (entry.sha256 is not None and entry.sha256!=allowed.sha256):
            raise StorageError('m365_synthetic_file_rejected')
        read=self.adapter.read(entry,expected_sha256=allowed.sha256)
        self.downloads[source.reference]=(entry,read)
        return read.content


def save_origin(root,source,read,artifact):
    """Immutable private original/identity receipt, separate from ingestion/revisions."""
    root=require_local(root)
    if sha256(read.content).hexdigest()!=read.sha256 or artifact.source_hash!=read.sha256 or source.version!=read.version:
        raise StorageError('m365_origin_record_integrity_failed')
    receipt=dict(version=1,source=asdict(source),download_sha256=read.sha256,integrity=read.integrity,
        candidate_revision=artifact.revision_id,candidate_output_sha256=artifact.output_hash,
        candidate_source_sha256=artifact.source_hash,sync_verified=False,approval='not_granted')
    raw=json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()
    key=sha256(raw).hexdigest();parent=root/'m365_downloads'
    require_local(parent);parent.mkdir(parents=True,exist_ok=True)
    final=parent/key
    if final.exists():
        require_local(final);require_local(final/'receipt.json');require_local(final/'original.bin')
        try:
            if ((final/'receipt.json').read_bytes()!=raw
                    or sha256((final/'original.bin').read_bytes()).hexdigest()!=read.sha256):raise ValueError
        except (OSError,ValueError):raise StorageError('m365_origin_record_integrity_failed') from None
        return final
    staged=parent/('.staging-'+uuid4().hex);staged.mkdir()
    try:
        import os
        for name,body in [('original.bin',read.content),('receipt.json',raw)]:
            with (staged/name).open('xb') as stream:
                stream.write(body);stream.flush();os.fsync(stream.fileno())
        staged.rename(final)
    except BaseException:
        shutil.rmtree(staged);raise
    return final


class ReadOnlyTestPilot:
    def __init__(self,config,session,transport,output_root,*,mode='offline_injected_components'):
        self.config=config.validate();self.session=session;self.transport=transport
        self.output_root=require_local(output_root)
        self.adapter=ReadOnlyGraphAdapter(config.scope,session,transport)
        self.mode=mode;self.resources_verified=False;self.status='not_connected'

    @classmethod
    def authorized(cls,config,output_root,*,operator_authorized=False):
        config.authorize(operator_authorized=operator_authorized)
        output_root=require_local(output_root)
        session=create_session(config,operator_authorized=operator_authorized)
        try:return cls(config,session,ReadOnlyHttpsTransport(config.scope.download_hosts),output_root,mode='authorized_test_transport')
        except Exception:
            session.close();raise

    def sign_in(self):
        self.resources_verified=False
        try:
            self.session.sign_in()
            self.verify_resources()
        except Exception:
            self.status='connection_failed';raise

    def verify_resources(self):
        self.resources_verified=False
        self.adapter.site()
        if self.config.scope.drive_id not in {d['id'] for d in self.adapter.libraries()}:
            raise StorageError('graph_library_not_in_authorized_site')
        from urllib.parse import quote
        for folder in self.config.scope.raw_folder_ids:
            path='/v1.0/drives/'+quote(self.config.scope.drive_id,safe='')+'/items/'+quote(folder,safe='')
            item=self.adapter._payload(self.adapter._request('GET',path,missing='storage_folder_missing'))
            if (item.get('id')!=folder or not isinstance(item.get('folder'),dict) or 'remoteItem' in item
                    or item.get('parentReference',{}).get('driveId')!=self.config.scope.drive_id):
                raise StorageError('graph_scope_mismatch')
        self.resources_verified=True;self.status='test_resources_verified_read_only'

    def list_reports(self,kind):
        if not self.resources_verified:raise StorageError('m365_resources_not_verified')
        kind=ReportType(kind);folder=self.config.scope.raw_folder_ids[list(ReportType).index(kind)]
        allowed={f.item_id for f in self.config.files if f.report_type==kind}
        result=tuple(f for f in self.adapter.list_files(folder) if f.item_id in allowed)
        suffix='.xlsx' if kind==ReportType.TMA_WORK_ORDERS else '.csv'
        if any(not f.name.lower().endswith(suffix) for f in result):raise StorageError('m365_synthetic_format_rejected')
        return result

    def workflow(self,files):
        if not self.resources_verified:raise StorageError('m365_resources_not_verified')
        require_local(self.output_root)
        selections={uuid4().hex:f for f in files}
        bridge=VerifiedGraphSource(self.adapter,self.config,selections)
        workflow=DesktopWorkflow(self.output_root,source=bridge,output_format='powerbi')
        return workflow,tuple(SourceFile(key,f.name) for key,f in selections.items())

    def process(self,workflow,previews,corrections=None):
        require_local(self.output_root)
        if not self.resources_verified:raise StorageError('m365_resources_not_verified')
        if (workflow.base_output_root!=self.output_root.resolve() or not isinstance(workflow.source,VerifiedGraphSource)
                or workflow.source.adapter is not self.adapter):raise StorageError('storage_reference_rejected')
        results=workflow.process(previews,corrections or {},lambda *args:None,Event())
        for entry in results:
            if entry.result.status in (ProcessingStatus.SUCCESS,ProcessingStatus.SKIPPED):
                source,read=workflow.source.downloads[entry.preview.source.reference]
                try:save_origin(self.output_root,source,read,entry.result.artifact)
                except StorageError:raise
                except Exception:raise StorageError('m365_candidate_saved_origin_record_failed') from None
        return results

    def sign_out(self):
        self.resources_verified=False;self.status='sign_out_incomplete'
        try:
            self.session.sign_out();self.status='signed_out_locally'
        finally:self.transport.close()

    def close(self):
        self.resources_verified=False;self.status='closed_cache_retained'
        try:self.session.close()
        finally:self.transport.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','list','preview','process'])
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--it-authorized-test-only',action='store_true')
    parser.add_argument('--output-root',type=Path)
    parser.add_argument('--report-type',choices=[k.value for k in ReportType])
    parser.add_argument('--item-id');parser.add_argument('--month');parser.add_argument('--replacement-token')
    parser.add_argument('--sign-out-after',action='store_true')
    args=parser.parse_args(argv);pilot=None
    try:
        config=load_test_config(args.config)
        if args.action=='inspect':
            print(json.dumps(dict(configuration='valid_test_allowlist',enabled=config.enabled,network_contacted=False,
                authorization_verified=False,reviewer_authority=False,publication_enabled=False)));return 0
        if not args.output_root or not args.report_type:raise StorageError('m365_pilot_selection_required')
        pilot=ReadOnlyTestPilot.authorized(config,args.output_root,operator_authorized=args.it_authorized_test_only)
        pilot.sign_in();files=pilot.list_reports(args.report_type)
        if args.action=='list':
            print(json.dumps(dict(mode=pilot.mode,files=[dict(item_id=f.item_id,name=f.name) for f in files],publication=False)));return 0
        selected=[f for f in files if f.item_id==args.item_id]
        if len(selected)!=1 or not args.month:raise StorageError('m365_pilot_selection_required')
        workflow,sources=pilot.workflow(selected)
        previews=workflow.preview(sources,ReportType(args.report_type),args.month,lambda *a:None,Event())
        results=[p.result for p in previews]
        if args.action=='process':
            results=[r.result for r in pilot.process(workflow,previews,{0:args.replacement_token} if args.replacement_token else {})]
        print(json.dumps(dict(mode=pilot.mode,results=[dict(status=r.status,code=r.code,rows=r.output_rows,
            warnings=r.warnings,correction_required=r.status==ProcessingStatus.NEEDS_REVIEW) for r in results],approval=False,publication=False)))
        return 0 if all(r.status in (ProcessingStatus.SUCCESS,ProcessingStatus.SKIPPED) for r in results) else 2
    except StorageError as exc:
        print(json.dumps(dict(error=str(exc),connected=False,publication=False)));return 1
    except Exception:
        print(json.dumps(dict(error='m365_pilot_failed',connected=False,publication=False)));return 1
    finally:
        if pilot is not None:
            try:
                if args.sign_out_after:pilot.sign_out()
                else:pilot.close()
            except Exception:
                print(json.dumps(dict(error='m365_session_cleanup_incomplete',publication=False)));return 1


if __name__=='__main__':raise SystemExit(main())
