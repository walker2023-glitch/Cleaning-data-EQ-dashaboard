"""Employee review page; worker operations never call Tk or send requests remotely."""
import json
import customtkinter as ctk
from equipment_data_manager.review import ReviewService
from equipment_data_manager.processing.models import ProcessingError


class ReviewPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='white')
        self.app, self.captured = app, None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)
        self.message = ctk.CTkLabel(self, text='Review the selected month. Final approval and Publish are unavailable.',
            anchor='w', wraplength=800, justify='left', text_color='#172B4D')
        self.message.grid(row=0,column=0,sticky='ew',padx=18,pady=12)
        bar = ctk.CTkFrame(self,fg_color='transparent'); bar.grid(row=1,column=0,sticky='ew',padx=18)
        self.load_button = ctk.CTkButton(bar,text='Review candidate',command=self.load)
        self.load_button.pack(side='left',padx=(0,8))
        self.request_button = ctk.CTkButton(bar,text='Request approval (local)',command=self.request,state='disabled')
        self.request_button.pack(side='left',padx=(0,8))
        self.history_button = ctk.CTkButton(bar,text='Publication history',command=self.publication_history)
        self.history_button.pack(side='left')
        self.note = ctk.CTkEntry(self,placeholder_text='Evidence note or private reference (required for a local review request)')
        self.note.grid(row=2,column=0,sticky='ew',padx=18,pady=12)
        disabled = ctk.CTkFrame(self,fg_color='transparent'); disabled.grid(row=3,column=0,sticky='ew',padx=18)
        self.approve_button = ctk.CTkButton(disabled,text='Approve — unavailable',state='disabled')
        self.approve_button.pack(side='left',padx=(0,8))
        self.publish_button = ctk.CTkButton(disabled,text='Publish — disabled',state='disabled')
        self.publish_button.pack(side='left')
        self.evidence = ctk.CTkTextbox(self,wrap='word',font=('Segoe UI',13))
        self.evidence.grid(row=4,column=0,sticky='nsew',padx=18,pady=12)
        self.display('Select the month on Process Reports, then Review candidate.\n'
            'No reviewer authority or publishing service is configured.\n'
            'A local request is not sent, authenticated, approved or published.')

    def display(self, text):
        self.evidence.configure(state='normal')
        self.evidence.delete('1.0','end'); self.evidence.insert('1.0',text)
        self.evidence.configure(state='disabled')

    def service(self):
        if self.app.workspace is None or self.app.workflow.output_format != 'powerbi':
            raise ProcessingError('review_workspace_required')
        return ReviewService(self.app.workflow.coordinator, raw_folder=self.app.workspace.raw_folder)

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
            captured = service.capture(period)
            history = [dict(request_id=r['request_id'], requested_at=r['requested_at'],
                status=service.status(r), evidence_note=r['evidence_note']) for r in service.history()
                if r['evidence']['period']==period]
            return dict(captured=captured, history=history)
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
            record = service.request(period, fingerprint, note)
            return dict(captured=service.capture(period), history=[dict(request_id=record['request_id'],
                requested_at=record['requested_at'], status=service.status(record), evidence_note=record['evidence_note'])])
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
        self.display('\n'.join(lines))
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
        eligible = self.captured is not None and not self.captured['evidence']['missing_reports']
        self.request_button.configure(state='normal' if not value and eligible else 'disabled')
        self.approve_button.configure(state='disabled'); self.publish_button.configure(state='disabled')

    def publication_history(self):
        self.display('Publication history is unavailable: no publishing service is configured.\n'
            'This does not assert that no snapshots exist on SharePoint.\n'
            'Existing local candidate revisions remain available in History.')
