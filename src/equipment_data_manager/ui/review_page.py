"""Employee review page; worker operations never call Tk or send requests remotely."""
import json
import customtkinter as ctk
from equipment_data_manager.review import ReviewService
from equipment_data_manager.processing.models import ProcessingError
from equipment_data_manager.auth.reviewer_identity import UnavailableReviewerIdentity
from equipment_data_manager.ui.review_presenter import review_sections
from equipment_data_manager.ui.messages import error_message


class ReviewPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='white')
        self.app, self.captured = app, None
        self.identity_provider = UnavailableReviewerIdentity()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(6, weight=1)
        self.message = ctk.CTkLabel(self, text='Choose the reporting month, then refresh the evidence. Local requests are not sent. Entra sign-in and reviewer verification are unavailable.',
            anchor='w', wraplength=800, justify='left', text_color='#172B4D')
        self.message.grid(row=0,column=0,sticky='ew',padx=18,pady=12)
        month_bar = ctk.CTkFrame(self,fg_color='transparent')
        month_bar.grid(row=1,column=0,sticky='ew',padx=18,pady=(0,8))
        ctk.CTkLabel(month_bar,text='Reporting month').pack(side='left',padx=(0,10))
        from equipment_data_manager.ui.app import MONTHS
        self.month_picker = ctk.CTkComboBox(month_bar,variable=app.month,values=list(MONTHS),state='readonly',width=130)
        self.month_picker.pack(side='left')
        self.year_entry = ctk.CTkEntry(month_bar,textvariable=app.year,width=70)
        self.year_entry.pack(side='left',padx=8)
        self.month_caption = ctk.CTkLabel(month_bar,text='',anchor='w')
        self.month_caption.pack(side='left',padx=8)
        bar = ctk.CTkFrame(self,fg_color='transparent'); bar.grid(row=2,column=0,sticky='ew',padx=18)
        self.load_button = ctk.CTkButton(bar,text='Review candidate',command=self.load)
        self.load_button.pack(side='left',padx=(0,8))
        self.request_button = ctk.CTkButton(bar,text='Request approval (local)',command=self.request,state='disabled')
        self.request_button.pack(side='left',padx=(0,8))
        self.history_button = ctk.CTkButton(bar,text='Publication history',command=self.publication_history)
        self.history_button.pack(side='left')
        self.note = ctk.CTkEntry(self,placeholder_text='Evidence note or private reference (required for a local review request)')
        self.note.grid(row=3,column=0,sticky='ew',padx=18,pady=12)
        disabled = ctk.CTkFrame(self,fg_color='transparent'); disabled.grid(row=4,column=0,sticky='ew',padx=18)
        self.approve_button = ctk.CTkButton(disabled,text='Approve — unavailable',state='disabled')
        self.approve_button.pack(side='left',padx=(0,8))
        self.publish_button = ctk.CTkButton(disabled,text='Publish — disabled',state='disabled')
        self.publish_button.pack(side='left')
        self.sign_in_button = ctk.CTkButton(disabled,text='Entra sign-in — unavailable',state='disabled')
        self.sign_in_button.pack(side='left',padx=8)
        self.stages = ctk.CTkFrame(self,fg_color='#F3F6FA')
        self.stages.grid(row=5,column=0,sticky='ew',padx=18,pady=(10,0))
        self.stage_labels=[]
        for column in range(4):
            self.stages.grid_columnconfigure(column,weight=1)
            label=ctk.CTkLabel(self.stages,text='',wraplength=170,justify='left',anchor='nw',text_color='#52647A')
            label.grid(row=0,column=column,sticky='nsew',padx=8,pady=8)
            self.stage_labels.append(label)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=6,column=0,sticky='nsew',padx=18,pady=(4,12))
        for name in ('Overview','Issues','Revisions','Review history','Technical details'):
            frame=self.tabs.add(name)
            frame.grid_columnconfigure(0,weight=1);frame.grid_rowconfigure(0,weight=1)
        overview=self.tabs.tab('Overview')
        overview.grid_rowconfigure(1,weight=2)
        self.counts = ctk.CTkTextbox(overview,wrap='word',font=('Segoe UI',14),height=100)
        self.counts.grid(row=0,column=0,sticky='nsew',pady=(0,6))
        self.financial = ctk.CTkTextbox(overview,wrap='word',font=('Segoe UI',14))
        self.financial.grid(row=1,column=0,sticky='nsew')
        self.issues=self.text_box('Issues')
        self.revisions=self.text_box('Revisions')
        self.review_history=self.text_box('Review history')
        self.evidence=self.text_box('Technical details')
        self.selection_label()
        self.display('Select the month on Process Reports, then Review candidate.\n'
            'No reviewer authority or publishing service is configured.\n'
            'A local request is not sent, authenticated, approved or published.')

    def text_box(self, name):
        box=ctk.CTkTextbox(self.tabs.tab(name),wrap='word',font=('Segoe UI',13))
        box.grid(row=0,column=0,sticky='nsew')
        return box

    @staticmethod
    def write(box,text):
        box.configure(state='normal');box.delete('1.0','end');box.insert('1.0',text);box.configure(state='disabled')

    def selection_label(self):
        try:
            self.month_caption.configure(text=self.app.period()+' • local/offline')
        except ProcessingError:
            self.month_caption.configure(text='Choose a valid month and year')

    def invalidate(self, message):
        self.captured=None
        self.selection_label()
        self.display(message+'\nRefresh evidence for the selected reporting month. Final approval and Publish stay disabled.')
        # A CTk ComboBox temporarily unlocks its entry while setting the shared
        # variable. Reconfiguring selector state inside that trace can erase the
        # value before insertion completes. Only invalidate review actions here.
        self.request_button.configure(state='disabled')
        self.approve_button.configure(state='disabled')
        self.publish_button.configure(state='disabled')
        self.sign_in_button.configure(state='disabled')

    def display(self, text):
        self.write(self.counts,text)
        for box in (self.financial,self.issues,self.revisions,self.review_history):
            self.write(box,'Refresh evidence to load this section.')
        for label,title in zip(self.stage_labels,('Review Requested Locally','Approval Pending','Approved','Published')):
            label.configure(text=title+'\nNo current authoritative evidence')
        self.tabs.set('Overview')
        self.evidence.configure(state='normal')
        self.evidence.delete('1.0','end'); self.evidence.insert('1.0',text)
        self.evidence.configure(state='disabled')

    def service(self):
        if self.app.workspace is None or self.app.workflow.output_format != 'powerbi':
            raise ProcessingError('review_workspace_required')
        return ReviewService(self.app.workflow.coordinator, raw_folder=self.app.workspace.raw_folder)

    @staticmethod
    def payload(service, period):
        captured=service.capture(period)
        history=[dict(request_id=r['request_id'],requested_at=r['requested_at'],
            status=service.status(r),evidence_note=r['evidence_note']) for r in service.history()
            if r['evidence']['period']==period]
        return dict(captured=captured,history=history)

    def load(self):
        if self.app.worker.busy:
            return
        self.captured = None
        self.busy(False)
        try:
            service, period = self.service(), self.app.period()
        except ProcessingError as exc:
            from equipment_data_manager.ui.messages import error_message
            self.display(error_message(str(exc))); return
        def operation(progress, stop):
            return self.payload(service, period)
        self.app._start('business_review',operation)

    def request(self):
        if self.app.worker.busy or self.captured is None:
            return
        try:
            service = self.service()
            period = self.app.period()
        except ProcessingError:
            self.load(); return
        fingerprint, note = self.captured['fingerprint'], self.note.get()
        def operation(progress, stop):
            service.request(period, fingerprint, note)
            return self.payload(service, period)
        self.app._start('business_review',operation)

    def completed(self, payload):
        self.captured = payload['captured']
        e = self.captured['evidence']
        lines = [f"Reporting month: {e['period']}",
            'Approval: unavailable — reviewer authority is not configured.',
            'Publication readiness: blocked. Publish remains disabled.',
            'Local requests are not sent. CandidateUnverified status is unchanged.',
            'Missing reports: '+(', '.join(e['missing_reports']) or 'none'), '']
        for kind, report in e['reports'].items():
            lines += [f"{kind}: {report['retained_rows']} retained / {report['input_rows']} source rows",
                'Missing values: '+json.dumps(report['missing_values']),
                'Warnings: '+', '.join(report['warnings'])]
            if 'financial_summary' in report:
                lines += ['Reported monthly financial summary: '+json.dumps(report['financial_summary']),
                    'Arithmetic reconciliation: '+report['financial_reconciliation']]
        lines += ['', 'Exact selected revisions and source/output/summary hashes:',
            json.dumps(e['selected'],indent=2), '', 'Local review requests:', json.dumps(payload['history'],indent=2)]
        self.display('\n'.join(lines))  # Raw evidence stays accessible in Technical details.
        sections=review_sections(payload)
        self.write(self.counts,'REPORT COUNTS\n\n'+sections['counts'])
        self.write(self.financial,'REPORTED MONTHLY FINANCIAL TOTALS\n\n'+sections['financial'])
        self.write(self.issues,'WARNINGS AND MISSING DATA\n\n'+sections['issues'])
        self.write(self.revisions,'EXACT SELECTED REVISIONS\n\n'+sections['revisions'])
        self.write(self.review_history,'LOCAL REVIEW HISTORY\n\n'+sections['history'])
        for label,(title,status) in zip(self.stage_labels,sections['stages']):
            label.configure(text=title+'\n'+status)
        self.selection_label()
        self.busy(False)
        self.app.status.set('Review evidence loaded. Final approval and publication remain disabled.')

    def failed(self):
        self.captured = None
        self.busy(False)
        self.display('Review could not finish. '+self.app.status.get()+'\nReload current evidence before requesting review.')

    def busy(self, value):
        self.load_button.configure(state='disabled' if value else 'normal')
        self.history_button.configure(state='disabled' if value else 'normal')
        self.note.configure(state='disabled' if value else 'normal')
        self.month_picker.configure(state='disabled' if value else 'readonly')
        self.year_entry.configure(state='disabled' if value else 'normal')
        eligible = self.captured is not None and not self.captured['evidence']['missing_reports']
        self.request_button.configure(state='normal' if not value and eligible else 'disabled')
        self.approve_button.configure(state='disabled'); self.publish_button.configure(state='disabled')
        self.sign_in_button.configure(state='disabled')

    def publication_history(self):
        self.display('Publication history is unavailable: no publishing service is configured.\n'
            'This does not assert that no snapshots exist on SharePoint.\n'
            'Existing local candidate revisions remain available in History.')
