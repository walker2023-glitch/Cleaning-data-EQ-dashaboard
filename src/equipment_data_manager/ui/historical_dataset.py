"""Employee controls for LOCAL unapproved snapshots of selected candidates."""
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from equipment_data_manager.historical_dataset import preview_dataset,generate_dataset
from equipment_data_manager.monthly import _packet_identifier
from equipment_data_manager.ui.messages import error_message,warning_message
from equipment_data_manager.ui.workflow import SUPPORTED_REPORTS


class HistoricalDatasetPage(ctk.CTkScrollableFrame):
    def __init__(self,parent,history):
        super().__init__(parent,fg_color='white')
        self.history,self.app=history,history.app
        self.plan=None;self.output=None
        self.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(self,text='Power BI Historical Snapshot',font=ctk.CTkFont(size=18,weight='bold')).grid(row=0,column=0,sticky='w')
        ctk.CTkLabel(self,text='Combine current selected candidates for the range above. No raw cleaning, approval, upload or refresh.',
            wraplength=760,justify='left').grid(row=1,column=0,sticky='w',pady=5)
        self.preview_button=ctk.CTkButton(self,text='Preview selected candidates',command=self.preview,width=230)
        self.preview_button.grid(row=2,column=0,sticky='w',pady=5)
        self.table=ttk.Treeview(self,columns=('month','type','status','rows','revision'),show='headings',height=5,style='EDM.Treeview')
        for key,label in zip(('month','type','status','rows','revision'),('Month','Report','Selection / integrity','Rows','Revision')):
            self.table.heading(key,text=label);self.table.column(key,width=180 if key=='type' else 125,minwidth=70)
        self.table.grid(row=3,column=0,sticky='ew');self.table.bind('<<TreeviewSelect>>',self.details)
        self.detail=ctk.CTkTextbox(self,height=130,wrap='word');self.detail.grid(row=4,column=0,sticky='ew',pady=5)
        self.ack=ctk.BooleanVar(value=False);self.local=ctk.BooleanVar(value=False)
        self.compatibility=ctk.CTkCheckBox(self,text='I understand the compatibility gaps. This is an unapproved backup Power BI test.',variable=self.ack,command=lambda:self.busy(False))
        self.compatibility.grid(row=5,column=0,sticky='w',pady=5)
        self.local_check=ctk.CTkCheckBox(self,text='I will choose trusted local storage outside raw, candidates, approved and production folders.',variable=self.local,command=lambda:self.busy(False))
        self.local_check.grid(row=6,column=0,sticky='w',pady=5)
        self.open_button=ctk.CTkButton(self,text='Open completed snapshot',command=self.open,width=230)
        self.open_button.grid(row=7,column=0,sticky='w',pady=5)
        self.create_button=ctk.CTkButton(self,text='Create local unapproved snapshot',command=self.create,width=280)
        self.create_button.grid(row=8,column=0,sticky='w',pady=5)
        self.invalidate()

    def invalidate(self):
        self.plan=None;self.ack.set(False);self.local.set(False)
        self.table.delete(*self.table.get_children())
        self.history._text(self.detail,'Preview selected candidates for this range first. Missing or invalid slots block generation. Compatibility gaps include TMA table grain, date-only requests, Building derivation and dashboard filters. No revisions are changed.')
        self.busy(False)

    def busy(self,value):
        busy=value or self.app.worker.busy or self.app.settings_worker.busy
        ready=self.app.workspace is not None and not busy
        self.preview_button.configure(state='normal' if ready else 'disabled')
        for widget in (self.compatibility,self.local_check):widget.configure(state='normal' if self.plan and self.plan.ready and ready else 'disabled')
        self.create_button.configure(state='normal' if self.plan and self.plan.ready and self.ack.get() and self.local.get() and ready else 'disabled')
        self.open_button.configure(state='normal' if self.output and not busy else 'disabled')

    def preview(self):
        if self.app.worker.busy or self.app.settings_worker.busy or self.app.workspace is None:return
        self.invalidate();workspace=self.app.workspace;start,end=self.history.start.get(),self.history.end.get()
        self.app._start('dataset_preview',lambda progress,stop:preview_dataset(workspace,start,end,progress=progress,cancelled=stop.is_set))

    def previewed(self,plan):
        self.plan=plan;self.ack.set(False);self.local.set(False)
        for index,item in enumerate(plan.selections):
            self.table.insert('','end',iid=str(index),values=(item.month,SUPPORTED_REPORTS[item.report_type],item.status,item.rows if item.status=='ready' else 'Not assessed',item.revision[:12] or 'None'))
        self.history._text(self.detail,('All requested candidate slots passed integrity checks. ' if plan.ready else 'Snapshot blocked: missing, invalid or unassessed candidate slots. No older fallback will be used. ')
            +'No snapshot written. Business accuracy is unverified. Read the compatibility guide before confirming. Select a row for counts, missing values, warnings and exact revision/hash evidence.')
        self.history.summary.configure(text=f'Snapshot preview: {sum(s.status=="ready" for s in plan.selections)} of {len(plan.selections)} selected candidate slots ready. '+('Complete selection; compatibility still needs review.' if plan.ready else 'Incomplete or invalid — creation disabled.'))
        self.busy(False)

    def details(self,*_):
        if not self.plan or not self.table.selection():return
        s=self.plan.selections[int(self.table.selection()[0])]
        if s.status!='ready':
            self.history._text(self.detail,f'{s.month} — {SUPPORTED_REPORTS[s.report_type]}: {s.status}\nCounts and missing values: Not assessed.\nIssue: {error_message(s.code)}\nDiagnostic category: {s.code}')
            return
        lines=[f'{s.month} — {s.report_type}: {s.status}',f'Records: {s.rows if s.status=="ready" else "Not assessed"}',
            f'Missing reported costs: {s.unavailable_costs}; missing assignments: {s.missing_assignments}; missing identifiers: {s.missing_identifiers}',
            f'Reconciliation: {s.reconciliation or "Not applicable"}',f'Revision: {s.revision or "No valid selected revision"}',
            f'Source SHA-256: {s.source_sha256}',f'Candidate SHA-256: {s.output_sha256}',f'Financial summary SHA-256: {s.summary_sha256}',
            f'Cleaner version: {s.cleaner_version}']
        if s.code:lines+=['Issue: '+error_message(s.code),f'Diagnostic category: {s.code}']
        lines+=['Warning: '+warning_message(w) for w in s.warnings]
        self.history._text(self.detail,'\n'.join(lines))

    def create(self):
        if self.app.worker.busy or self.plan is None or not self.plan.ready or not self.ack.get() or not self.local.get():return
        if not messagebox.askyesno('Create local unapproved test snapshot?',
            'Combine only the reviewed selected revisions? All four CSVs remain CandidateUnverified. No PBIX change, approval, upload or refresh will occur.',parent=self.app):return
        parent=filedialog.askdirectory(parent=self.app,title='Choose trusted local snapshot parent (outside all workspace folders)')
        if not parent:return
        plan=self.plan;workspace=self.app.workspace
        target=Path(parent)/('PowerBI_Historical_Test_'+_packet_identifier())
        self.ack.set(False);self.local.set(False)
        self.app._start('dataset_create',lambda progress,stop:generate_dataset(workspace,plan,target,
            confirmation=plan.fingerprint,local_confirmed=True,compatibility_acknowledged=True,progress=progress,cancelled=stop.is_set))

    def completed(self,path):
        import json
        self.output=path;self.plan=None
        try:manifest=json.loads((path/'snapshot_manifest.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):
            self.failed();self.app.status.set('Snapshot completion evidence is unavailable. Inspect the local folder before importing.');return
        lines=['Local snapshot completed. CandidateUnverified — not approved or published.',str(path)]
        lines += [f'{e["file"]}: {e["rows"]} rows; monthly counts {e["rows_by_month"]}' for e in manifest['datasets']]
        lines+=['Read compatibility_report.md and snapshot_manifest.json before importing into a backup PBIX. Historical financial warnings and missing values remain.']
        self.history._text(self.detail,'\n'.join(lines));self.history.summary.configure(text='Local historical test snapshot created. Candidate selections unchanged. No approval, publication or Power BI refresh.')
        self.busy(False)

    def failed(self):
        self.plan=None;self.ack.set(False);self.local.set(False)
        self.history._text(self.detail,'Snapshot operation stopped. No incomplete snapshot is ready for import. Check the status message, then preview selected candidates again. Previous completed snapshots and candidate selections are preserved.')
        self.busy(False)

    def open(self):
        if self.output:
            try:
                from equipment_data_manager.ui.app import open_directory
                open_directory(self.output)
            except OSError:self.app.status.set('Could not open the snapshot folder. Open the displayed local path manually.')
