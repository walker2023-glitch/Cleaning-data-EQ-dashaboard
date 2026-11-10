"""Selection, reviewed plan and results for local historical candidate processing."""
import json
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from equipment_data_manager.historical_processing import ACTIONS, RESULTS, make_plan, execute_plan, export_processing
from equipment_data_manager.processing.models import ReportType
from equipment_data_manager.ui.workflow import SUPPORTED_REPORTS, SourceFile
from equipment_data_manager.ui.worker import JobEvent
from equipment_data_manager.ui.messages import error_message, warning_message


class HistoricalProcessingPage(ctk.CTkScrollableFrame):
    def __init__(self, parent, history):
        super().__init__(parent, fg_color='white')
        self.history, self.app = history, history.app
        self.plan = self.run = None
        self.rows = {}
        self.results = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(self, text='Historical Batch Processing', text_color='#172B4D', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0,column=0,pady=4,sticky='w')
        form = ctk.CTkFrame(self)
        form.grid(row=1,column=0,sticky='ew',pady=4)
        self.month = ctk.StringVar(value='Select month')
        self.month_picker = ctk.CTkComboBox(form,variable=self.month,values=['Select month'],state='readonly',width=120)
        self.month_picker.grid(row=0,column=0,padx=4,pady=4)
        self.month_button = ctk.CTkButton(form,text='Select month',command=self.select_month,width=120)
        self.month_button.grid(row=0,column=1,padx=4,pady=4)
        self.all_button = ctk.CTkButton(form,text='Select all eligible reports',command=self.select_all,width=190)
        self.all_button.grid(row=0,column=2,padx=4,pady=4)
        self.clear_button = ctk.CTkButton(form,text='Clear selection',command=self.clear,width=120)
        self.clear_button.grid(row=0,column=3,padx=4,pady=4)
        self.types = {}; self.type_widgets = []
        for index,(kind,label) in enumerate(SUPPORTED_REPORTS.items()):
            self.types[kind] = ctk.BooleanVar(value=True)
            widget = ctk.CTkCheckBox(form,text=label,variable=self.types[kind],command=self.selection_changed)
            widget.grid(row=1,column=index,padx=4,pady=5,sticky='w');self.type_widgets.append(widget)
        box = ctk.CTkFrame(self)
        box.grid(row=2,column=0,sticky='nsew');box.grid_columnconfigure(0,weight=1);box.grid_rowconfigure(0,weight=1)
        columns=('month','report','existing','action')
        self.table=ttk.Treeview(box,columns=columns,show='headings',selectmode='extended',style='EDM.Treeview',height=6)
        for key,label in zip(columns,('Month','Report','Existing candidate','Plan / result')):
            self.table.heading(key,text=label);self.table.column(key,width=110 if key=='month' else 190,minwidth=80)
        self.table.grid(row=0,column=0,sticky='nsew')
        scroll=ttk.Scrollbar(box,orient='vertical',command=self.table.yview);scroll.grid(row=0,column=1,sticky='ns');self.table.configure(yscrollcommand=scroll.set)
        self.table.bind('<<TreeviewSelect>>',self.selection_changed)
        self.detail=ctk.CTkTextbox(self,height=110,wrap='word');self.detail.grid(row=3,column=0,sticky='ew',pady=5)
        buttons=ctk.CTkFrame(self);buttons.grid(row=4,column=0,sticky='ew')
        self.plan_button=ctk.CTkButton(buttons,text='Review Processing Plan',command=self.review_plan,width=180)
        self.plan_button.grid(row=0,column=0,padx=4,pady=4)
        self.process_button=ctk.CTkButton(buttons,text='Process Selected Reports',command=self.process,width=190)
        self.process_button.grid(row=0,column=1,padx=4,pady=4)
        self.export_button=ctk.CTkButton(buttons,text='Export Processing Summary',command=self.export,width=190)
        self.export_button.grid(row=0,column=2,padx=4,pady=4)
        self.confirmed=ctk.BooleanVar(value=False)
        self.confirm=ctk.CTkCheckBox(buttons,text='I reviewed this plan. Create local unapproved candidates only.',variable=self.confirmed,command=lambda:self.busy(False))
        self.confirm.grid(row=1,column=0,columnspan=3,padx=4,pady=4,sticky='w')
        self.correction_button=ctk.CTkButton(buttons,text='Open single-report correction workflow',command=self.open_correction,width=280)
        self.correction_button.grid(row=2,column=0,columnspan=2,padx=4,pady=4,sticky='w')
        self.open_button=ctk.CTkButton(buttons,text='Open candidate folder',command=self.open_folder,width=190)
        self.open_button.grid(row=2,column=2,padx=4,pady=4)
        self.stop_button=ctk.CTkButton(buttons,text='Stop After Current Report',command=self.stop,width=210)
        self.stop_button.grid(row=3,column=0,columnspan=2,padx=4,pady=4,sticky='w')
        self.reset()

    def _text(self,text):
        self.history._text(self.detail,text)

    def reset(self):
        self.plan = self.run = None; self.rows={};self.results={}
        self.confirmed.set(False)
        if hasattr(self,'table'):
            self.table.delete(*self.table.get_children())
            self._text('Discover and preview first. Select report rows (Ctrl-click for individual reports), then review a plan. Corrections stay blocked here. No approval or publishing is enabled.')
            self.busy(False)

    def load_preview(self,batch):
        self.reset()
        self.rows={f'{r.month}:{r.report_type}':r for r in batch.reports}
        for key,row in self.rows.items():
            existing='Potential correction' if row.candidate_status=='needs_review' else 'Exists, unchanged' if row.candidate_status=='skipped' else 'None' if row.candidate_status=='success' else 'Not assessed'
            self.table.insert('','end',iid=key,values=(row.month,SUPPORTED_REPORTS[row.report_type],existing,'Select and review plan' if row.status in ('previewed','warnings') else row.status.replace('_',' ')))
        months=sorted({r.month for r in batch.reports})
        self.month_picker.configure(values=months or ['Select month'])
        self.month.set(months[0] if months else 'Select month')
        self.busy(False)

    def selected(self):
        return tuple((self.rows[key].month,self.rows[key].report_type) for key in self.table.selection()
                     if key in self.rows and self.types[ReportType(self.rows[key].report_type)].get())

    def selection_changed(self,*_):
        if self.app.worker.busy:return
        self.plan=None;self.confirmed.set(False)
        if self.run is not None:
            chosen=set(self.selected())
            self._text(self.result_text([item for item in self.run.items if (item.month,item.report_type) in chosen]))
        elif self.rows:
            self._text(f'{len(self.selected())} report(s) selected. Review a fresh plan before writing. Completed candidates remain in History. Corrections need their single-report confirmation.')
        self.busy(False)

    def select_all(self):
        self.table.selection_set([key for key,row in self.rows.items() if row.status in ('previewed','warnings') and row.candidate_status in ('success','skipped') and self.types[ReportType(row.report_type)].get()])
        self.selection_changed()

    def select_month(self):
        self.table.selection_set(sorted(set(self.table.selection())|{key for key,row in self.rows.items() if row.month==self.month.get() and self.types[ReportType(row.report_type)].get()}))
        self.selection_changed()

    def clear(self):
        self.table.selection_remove(*self.table.selection());self.selection_changed()

    def busy(self,value):
        value=value or self.app.worker.busy or self.app.settings_worker.busy
        self.table.configure(selectmode='none' if value else 'extended')
        available=bool(self.rows) and self.app.workspace is not None and not value
        for widget in (self.month_button,self.all_button,self.clear_button,*self.type_widgets):widget.configure(state='normal' if available else 'disabled')
        self.month_picker.configure(state='readonly' if available else 'disabled')
        self.plan_button.configure(state='normal' if available and self.selected() else 'disabled')
        ready=self.app.workspace is not None and self.plan is not None and not self.plan.stopped and any(i.action in ('create','skip') for i in self.plan.items)
        self.confirm.configure(state='normal' if ready and not value else 'disabled')
        self.process_button.configure(state='normal' if ready and self.confirmed.get() and not value else 'disabled')
        self.export_button.configure(state='normal' if self.run is not None and not value else 'disabled')
        self.correction_button.configure(state='normal' if available else 'disabled')
        self.open_button.configure(state='normal' if self.app.workspace is not None and not value else 'disabled')
        self.stop_button.configure(state='normal' if self.app.worker.busy and self.app.job in ('historical_plan','historical_process') else 'disabled')

    def review_plan(self):
        if self.app.worker.busy or not self.selected() or self.history.batch is None:return
        workspace,layout=self.app.workspace,self.app.folder_layout
        inventory,batch,selected=self.history.inventory,self.history.batch,self.selected()
        self.plan=None;self.confirmed.set(False)
        self.app._start('historical_plan',lambda progress,stop:make_plan(workspace,layout,inventory,batch,selected,
            progress=progress,cancelled=stop,on_start=lambda month,kind:self.app.worker.events.put(JobEvent('historical_work_active',('Reviewing plan',month,kind)))))

    def planned(self,plan):
        self.plan=plan;self.confirmed.set(False)
        self.history.summary.configure(text=f'Plan reviewed for {len(plan.items)} selected reports. No candidates written during plan review; processing still requires confirmation.')
        lines=['Power BI CSV candidates (repair financial schema v2). Single-report Legacy mode is separate.', 'Review this exact plan. No files have been written. Candidate outputs stay unapproved.']
        for item in plan.items:
            key=f'{item.month}:{item.report_type}'
            existing='None' if item.preview.existing_revision is None else 'Exists, unchanged' if item.action=='skip' else 'Exists — correction review required'
            self.table.item(key,values=(item.month,SUPPORTED_REPORTS[item.report_type],existing,ACTIONS[item.action]))
            lines += [f'{item.month} — {SUPPORTED_REPORTS[item.report_type]}: {ACTIONS[item.action]}',f'  {item.preview.source_filename or "No selected source"}: source {item.preview.source_records if item.preview.source_records is not None else "Not assessed"}, retained {item.preview.retained_records if item.preview.retained_records is not None else "Not assessed"}, excluded {item.preview.excluded_records if item.preview.excluded_records is not None else "Not assessed"}']
            if item.action=='blocked':lines.append('  '+error_message(item.code))
            lines += ['  '+warning_message(w).replace('A monthly financial summary is saved beside the repair CSV.', 'The summary is proposed beside the repair CSV; no candidate is written during plan review.') for w in item.preview.warnings]
        self._text('\n'.join(lines))
        self.history._text(self.history.technical,json.dumps(plan.document(),indent=2))
        self.busy(False)

    def process(self):
        if self.app.worker.busy or self.plan is None or not self.confirmed.get():return
        plan=self.plan
        if set(self.selected())!={(i.month,i.report_type) for i in plan.items}:self.selection_changed();return
        creates=sum(i.action=='create' for i in plan.items);skips=sum(i.action=='skip' for i in plan.items)
        if not messagebox.askyesno('Confirm local candidate processing',f'Create {creates} local candidate report(s) and skip {skips} unchanged report(s)?\nCorrections remain blocked for individual review. No approvals, uploads or Power BI refresh will occur.',parent=self.app):return
        self.run=None;self.results={};self.confirmed.set(False)
        self.history.summary.configure(text='Processing selected reports into local unapproved candidates. Stop finishes the current report; no approval or publishing occurs.')
        workspace,layout=self.app.workspace,self.app.folder_layout
        self.app._start('historical_process',lambda progress,stop:execute_plan(workspace,layout,plan,plan.fingerprint,
            progress=progress,cancelled=stop,
            on_start=lambda month,kind:self.app.worker.events.put(JobEvent('historical_work_active',('Processing',month,kind))),
            on_result=lambda result:self.app.worker.events.put(JobEvent('historical_process_update',result))))

    def update_result(self,result):
        self.results[(result.month,result.report_type)]=result
        self.table.set(f'{result.month}:{result.report_type}','action',RESULTS[result.status])
        self._text('\n'.join(f'{month} — {SUPPORTED_REPORTS[kind]}: {RESULTS[r.status]}' + (' • '+error_message(r.code) if r.status in ('blocked','failed','correction') else '') for (month,kind),r in self.results.items()))

    def result_text(self,items):
        stats=self.run.summary
        caption=' • '.join(f'{label}: {stats[key]}' for key,label in [('selected','Selected'),('created','Created'),('skipped','Already processed'),('correction','Correction review'),('blocked','Blocked'),('failed','Failed'),('not_started','Not started')])
        retained='Retained records in committed/unchanged candidates: '+', '.join(f'{SUPPORTED_REPORTS[kind]} {count}' for kind,count in stats['retained_committed_or_unchanged'].items())
        lines=[caption,retained, 'Local candidates only. Review warnings below. Refresh preview and review a new plan to retry; committed history survives restart.']
        for item in items:
            lines += [f'{item.month} — {SUPPORTED_REPORTS[item.report_type]}: {RESULTS[item.status]}','  '+error_message(item.code) if item.status in ('blocked','failed','correction') else f'  Retained records: {item.evidence.retained_records}']
            if item.output_location:lines.append('  Candidate file: '+item.output_location)
            financial=dict(item.evidence.financial)
            if financial:
                lines.append('  Reported monthly labor / parts / total: '+ ' / '.join(financial.get(key) if financial.get(key) is not None else 'Unavailable' for key in ('ReportedLaborCost','ReportedPartsCost','ReportedTotalCost')))
                lines.append('  Financial comparison: '+financial.get('ReconciliationStatus','Not assessed').replace('_',' '))
            lines += ['  '+warning_message(w) for w in item.evidence.warnings]
        return '\n'.join(lines)

    def completed(self,run):
        self.run=run;self.plan=None;self.confirmed.set(False)
        self._text(self.result_text(run.items))
        self.history.summary.configure(text=f'Processing results: {run.summary["created"]} candidates created, {run.summary["skipped"]} unchanged, {run.summary["correction"]} corrections require individual review, {run.summary["blocked"]} blocked, {run.summary["failed"]} failed, {run.summary["not_started"]} not started. Local unapproved outputs only.')
        self.history._text(self.history.technical,json.dumps(run.document(),indent=2));self.busy(False)

    def stop(self):
        self.app.stop_work();self.stop_button.configure(state='disabled')

    def open_folder(self):
        if self.app.workspace is None:return
        from equipment_data_manager.ui.app import open_directory
        try:open_directory(self.app.workspace.candidate_folder/'powerbi_candidates')
        except OSError:self._text('No normalized candidate folder is available yet. Process an eligible report first.')

    def failed(self):
        self.plan=None;self.confirmed.set(False)
        self._text('Operation did not finish. Completed candidates remain in durable History; partial results remain in the table. Discover/preview and review a fresh plan before retrying.')
        self.busy(False)

    def export(self):
        if self.app.worker.busy or self.run is None:return
        target=filedialog.asksaveasfilename(parent=self.app,title='Export local nonproduction batch diagnostic',initialfile='historical-processing.csv',defaultextension='.csv',filetypes=[('Diagnostic CSV','*.csv'),('Diagnostic JSON','*.json')])
        if target:
            workspace,run=self.app.workspace,self.run
            self.app._start('historical_process_export',lambda progress,stop:export_processing(run,Path(target),protected_roots=(workspace.raw_folder,workspace.candidate_folder,workspace.approved_folder)))

    def open_correction(self):
        if self.app.worker.busy:return
        selected=self.selected()
        corrections={(i.month,i.report_type) for i in self.plan.items if i.action=='correction'} if self.plan else set()
        if self.run:corrections|={(i.month,i.report_type) for i in self.run.items if i.status=='correction'}
        key=next((key for key in selected if key in corrections or self.rows[f'{key[0]}:{key[1]}'].candidate_status=='needs_review'),None)
        if key is None:
            self._text('Select one correction-required report row. Its source will be checked and previewed again in Process Reports.');return
        month,kind=key
        source=next(r.sources[0] for m in self.history.inventory.months if m.period==month for r in m.reports if r.report_type==kind and len(r.sources)==1)
        from equipment_data_manager.ui.app import MONTHS
        self.plan=None;self.confirmed.set(False)
        self.app.output_format.set('Power BI CSV candidate');self.app._output_format_changed()
        self.app.report.set(kind);self.app.month.set(MONTHS[int(month[5:])-1]);self.app.year.set(month[:4])
        self.app.set_files([str(Path(self.history.inventory.root)/source.item_id)])
        self.app.sources=(SourceFile(str(Path(self.history.inventory.root)/source.item_id),source.name,source.version,source.sha256),)
        self.app.show_page('Process Reports')
        self.app.status.set('Correction route selected. Confirm this month, preview again, then use the existing report-specific replacement confirmation.')
