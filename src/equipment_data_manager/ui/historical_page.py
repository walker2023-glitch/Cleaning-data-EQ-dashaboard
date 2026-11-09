"""Read-only inventory screen; processing stays in the existing monthly workflow."""
import json
import re
from pathlib import Path
from tkinter import filedialog, ttk

import customtkinter as ctk

from equipment_data_manager.historical import LAYOUT_LABELS, describe_issue, discover_history, export_inventory
from equipment_data_manager.storage.local import LocalFolderStorage
from equipment_data_manager.ui.workflow import SUPPORTED_REPORTS



class HistoricalPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='white')
        self.app, self.inventory = app, None
        self.batch = None
        self.preview_rows = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.caption = ctk.CTkLabel(self, text='Read-only historical inventory. No cleaning, approval or publishing.',
            anchor='w', wraplength=820, justify='left', text_color='#172B4D')
        self.caption.grid(row=0, column=0, padx=18, pady=10, sticky='ew')
        form = ctk.CTkFrame(self, fg_color='#F3F6FA')
        form.grid(row=1, column=0, padx=18, pady=4, sticky='ew')
        self.start = ctk.StringVar(value=app.period())
        self.end = ctk.StringVar(value=app.period())
        self.fields = []
        for index, (label, variable) in enumerate((('Start month (YYYY-MM)', self.start), ('End month (YYYY-MM)', self.end))):
            ctk.CTkLabel(form, text=label, text_color='#172B4D').grid(row=0, column=index, padx=10, sticky='w')
            widget = ctk.CTkEntry(form, textvariable=variable, width=180)
            widget.grid(row=1, column=index, padx=10, pady=6)
            self.fields.append(widget)
            variable.trace_add('write', lambda *_: self.invalidate())
        self.discover_button = ctk.CTkButton(form, text='Discover Historical Reports', command=self.discover, width=230, fg_color='#087F8C')
        self.discover_button.grid(row=1, column=2, padx=10, pady=6)
        self.export_button = ctk.CTkButton(form, text='Export Discovery Report', command=self.export, state='disabled', width=210, fg_color='#172B4D')
        self.preview_button = ctk.CTkButton(form, text='Preview Selected Months', command=self.preview, state='disabled', width=230)
        self.preview_button.grid(row=2, column=2, padx=10, pady=8)
        self.preview_export_button = ctk.CTkButton(form, text='Export Preview Report', command=self.export_batch, state='disabled', width=210)
        self.preview_export_button.grid(row=3, column=0, columnspan=2, padx=10, pady=8, sticky='w')
        self.export_button.grid(row=2, column=0, columnspan=2, padx=10, pady=8, sticky='w')
        self.summary = ctk.CTkLabel(self, text='Choose the root and layout in Settings, then select a range of up to 120 months.',
            anchor='w', wraplength=820, justify='left', text_color='#52647A')
        self.summary.grid(row=2, column=0, padx=18, pady=8, sticky='ew')
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=3, column=0, padx=10, pady=6, sticky='nsew')
        month_tab, detail_tab, technical_tab = (tabs.add(name) for name in ('Monthly completeness', 'Problems & files', 'Technical details'))
        for tab in (month_tab, detail_tab, technical_tab):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        columns = ('month', 'repairs', 'service', 'tma', 'status')
        self.table = ttk.Treeview(month_tab, columns=columns, show='headings', style='EDM.Treeview')
        for key, label in zip(columns, ('Month', 'Repairs', 'Service Orders', 'TMA', 'Inventory / preview status')):
            self.table.heading(key, text=label)
            self.table.column(key, width=300 if key == 'status' else 100, minwidth=85, stretch=True)
        self.table.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(month_tab, orient='vertical', command=self.table.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind('<<TreeviewSelect>>', self.show_details)
        self.details = ctk.CTkTextbox(detail_tab, wrap='word')
        self.details.grid(row=0, column=0, sticky='nsew')
        self.technical = ctk.CTkTextbox(technical_tab, wrap='word')
        self.technical.grid(row=0, column=0, sticky='nsew')
        self.invalidate()

    def invalidate(self):
        self.inventory = None
        self.batch = None
        self.preview_rows = {}
        if hasattr(self, 'table'):
            self.table.delete(*self.table.get_children())
            for box in (self.details, self.technical):
                self._text(box, 'Discover the selected range to see an inventory. No processing has run.')
            self.export_button.configure(state='disabled')
            self.preview_button.configure(state='disabled')
            self.preview_export_button.configure(state='disabled')
            self.summary.configure(text='Selection changed. Discover again; previous results do not describe this selection.')

    def selection_caption(self):
        workspace = self.app.workspace
        root = str(workspace.raw_folder) if workspace else 'Configure Raw Data Folder in Settings'
        layout = LAYOUT_LABELS[self.app.folder_layout]
        self.caption.configure(text=f'{layout}\nRaw root: {root}\nRead-only inventory and preview — no cleaned candidates, approval or publication. Cloud sync is unverified.')

    def discover(self):
        if self.app.worker.busy or self.app.settings_worker.busy:
            return
        self.invalidate()
        if self.app.workspace is None:
            self.summary.configure(text='Open Settings, select the raw root and folder layout, then Save Settings.')
            return
        root = self.app.workspace.raw_folder
        start, end = self.start.get(), self.end.get()
        from equipment_data_manager.historical import periods_between
        from equipment_data_manager.processing.models import ProcessingError
        try:
            periods_between(start, end)
        except ProcessingError:
            self.summary.configure(text='Enter start and end as YYYY-MM. End must follow start; select at most 120 months.')
            return
        layout = self.app.folder_layout
        self.app._start('historical_discover', lambda progress, stop: discover_history(
            LocalFolderStorage(root), start, end, layout, progress=progress, cancelled=stop))
        self.app.status.set('Inspecting historical reports read only. No cleaned candidates will be created. Stop ends after the current file read.')

    def completed(self, inventory):
        self.inventory = inventory
        self.table.delete(*self.table.get_children())
        for month in inventory.months:
            self.table.insert('', 'end', iid=month.period, values=(month.period,
                *(r.status.replace('_', ' ').title() for r in month.reports),
                'Complete inventory' if month.complete else 'Needs attention'))
        self.summary.configure(text=f'{sum(m.complete for m in inventory.months)} of {len(inventory.months)} months have a complete readable inventory. '
            + ('Stopped; unscanned months are shown. ' if inventory.stopped else '')
            + 'Schemas, row counts and financials have not been previewed. No processing has run.')
        self._text(self.technical, json.dumps(inventory.document(), indent=2))
        self.export_button.configure(state='normal')
        self.busy(False)
        if inventory.months:
            self.table.selection_set(inventory.months[0].period)
            self.show_details()

    @staticmethod
    def _text(box, text):
        box.configure(state='normal')
        box.delete('1.0', 'end')
        box.insert('1.0', text)
        box.configure(state='disabled')

    def show_details(self, *_):
        if not self.inventory or not self.table.selection():
            return
        if self.preview_rows:
            self.show_preview_details(self.table.selection()[0])
            return
        month = next(m for m in self.inventory.months if m.period == self.table.selection()[0])
        lines = [f'{month.period} — local inventory, synchronization unverified',
                 'No cleaning or business validation has run.', '']
        lines.extend(describe_issue(i) for i in month.issues)
        for report in month.reports:
            lines.extend(['', f'{SUPPORTED_REPORTS[report.report_type]}: {report.status.replace("_", " ").title()}'])
            if report.status == 'missing':
                lines.append('Required report is missing; no zero-activity report was inferred.')
            lines.extend(describe_issue(i) for i in report.issues)
            for source in report.sources:
                lines.extend([f'File: {source.name}', f'Size: {source.size_bytes} bytes'])
        self._text(self.details, '\n'.join(lines))

    def export(self):
        if not self.inventory or self.app.worker.busy or self.app.settings_worker.busy:
            return
        target = filedialog.asksaveasfilename(parent=self.app, title='Export private local inventory (outside raw/synced folders)',
            initialfile='historical-discovery.json', defaultextension='.json', filetypes=[('Discovery report', '*.json')], confirmoverwrite=True)
        if target:
            inventory = self.inventory
            self.app._start('historical_export', lambda progress, stop: export_inventory(inventory, Path(target)))

    def busy(self, value):
        for field in self.fields:
            field.configure(state='disabled' if value else 'normal')
        self.discover_button.configure(state='disabled' if value else 'normal')
        self.export_button.configure(state='normal' if self.inventory is not None and not value else 'disabled')
        self.preview_button.configure(state='normal' if self.inventory is not None and not self.inventory.stopped and self.app.workspace is not None and not value else 'disabled')
        self.preview_export_button.configure(state='normal' if self.batch is not None and not value else 'disabled')

    def preview(self):
        if self.inventory is None or self.inventory.stopped or self.app.worker.busy or self.app.settings_worker.busy:
            return
        from equipment_data_manager.historical_preview import preview_history
        from equipment_data_manager.ui.worker import JobEvent
        inventory = self.inventory
        self.preview_rows = {}
        self.batch = None
        root = self.app.workflow.base_output_root
        for month in inventory.months:
            self.table.item(month.period, values=(month.period, '—', '—', '—', 'Not previewed'))
        self.app._start('historical_preview', lambda progress, stop: preview_history(
            LocalFolderStorage(Path(inventory.root)), inventory, root, progress=progress, cancelled=stop,
            on_result=lambda result: self.app.worker.events.put(JobEvent('historical_preview_update', result)),
            on_start=lambda period, kind: self.app.worker.events.put(JobEvent('historical_preview_active', (period, kind)))))
        self.app.status.set('Preview only. No candidates or approval records will be written. Stop ends after the current report.')

    def preview_update(self, result):
        from equipment_data_manager.historical_preview import month_status
        self.preview_rows[(result.month, result.report_type)] = result
        reports = [self.preview_rows.get((result.month, kind)) for kind in SUPPORTED_REPORTS]
        values = [str(r.retained_records) if r and r.retained_records is not None else '—' for r in reports]
        present = [r for r in reports if r]
        status = month_status(present) if len(present) == 3 else 'Preview in progress'
        self.table.item(result.month, values=(result.month, *values, status))
        self.summary.configure(text=f'{len(self.preview_rows)} report slots checked. Preview only; business accuracy not independently verified. Select a month, then open Problems & files.')
        self.app.status.set(f'{result.month} • {SUPPORTED_REPORTS[result.report_type]} • {result.status.replace("_", " ")}')
        if self.table.selection() == (result.month,):
            self.show_preview_details(result.month)

    def preview_completed(self, batch):
        self.batch = batch
        self.summary.configure(text=('Stopped safely. ' if batch.stopped else 'Batch preview complete. ')
            + f'{len(batch.reports)} report slots shown. No candidates written. Business accuracy not independently verified. Cloud synchronization unverified.')
        self._text(self.technical, json.dumps(batch.document(), indent=2))
        self.busy(False)

    def show_preview_details(self, period):
        from equipment_data_manager.historical_preview import LABELS
        from equipment_data_manager.ui.messages import error_message, warning_message, REASONS
        def readable(key):
            return REASONS.get(key, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", key).replace("_", " ").replace(":", " — "))
        lines = [f'{period} — read-only preview', 'Cleaning success is not independent verification of business accuracy.',
                 'Missing financial values remain missing. Known sums may be incomplete.', '']
        for kind, label in SUPPORTED_REPORTS.items():
            result = self.preview_rows.get((period, kind))
            lines += ['', label]
            if result is None:
                lines.append('Not previewed')
                continue
            lines += [LABELS[result.status], f'File: {result.source_filename or "No source selected"}',
                      f'Source records: {result.source_records if result.source_records is not None else "Not assessed"}',
                      f'Retained: {result.retained_records if result.retained_records is not None else "Not assessed"}',
                      f'Excluded: {result.excluded_records if result.excluded_records is not None else "Not assessed"}',
                      f'Source integrity: {result.integrity.replace("_", " ")}']
            if result.status in ('failed', 'unsupported', 'stale', 'missing'):
                lines += [error_message(result.code)]
            financial = dict(result.financial)
            def display_value(key, value):
                if value is None:
                    return 'Unavailable (incomplete)'
                text = readable(str(value))
                incomplete = (key == 'KnownRepairTotalCost' and
                    (int(financial.get('UnavailableRepairCostCount') or '0') > 0 or result.source_records != result.retained_records))
                if key.endswith('KnownSum'):
                    incomplete = int(financial.get(key.removesuffix('KnownSum') + 'MissingCount') or '0') > 0
                return text + (' (incomplete)' if incomplete else '')
            for title, pairs in (('Exclusion reasons (existing rules)', result.exclusions),
                                 ('Missing values in retained records', result.missing_values),
                                 ('Date validation observations', result.date_observations),
                                 ('Reported financial summary / separate estimated and legacy known sums', result.financial)):
                if pairs:
                    lines += [title] + [f'  {readable(key)}: {display_value(key, value)}' for key, value in pairs]
            if result.report_type == 'tma_work_orders' and result.retained_records is not None:
                lines.append('Retained request dates passed the existing selected-month validator. Timestamp checks apply only to the timestamped layout.')
            lines += ['Warnings:'] + [f'  {warning_message(w).replace("A monthly financial summary is saved beside the repair CSV.", "The monthly summary is computed in memory; nothing is saved by preview.")}' for w in result.warnings]
            if result.candidate_status == 'needs_review':
                lines.append('Potential correction to an existing candidate. This preview does not select or replace a revision.')
        self._text(self.details, '\n'.join(lines))
        self._text(self.technical, json.dumps([r.document() for (month, _), r in self.preview_rows.items() if month == period], indent=2))

    def export_batch(self):
        if self.batch is None or self.app.worker.busy or self.app.settings_worker.busy:
            return
        from equipment_data_manager.historical_preview import export_preview
        target = filedialog.asksaveasfilename(parent=self.app, title='Save nonproduction diagnostic preview outside all workspace folders',
            initialfile='historical-preview.csv', defaultextension='.csv',
            filetypes=[('Diagnostic CSV', '*.csv'), ('Technical diagnostic JSON', '*.json')])
        if target:
            batch, workspace = self.batch, self.app.workspace
            roots = (workspace.raw_folder, workspace.candidate_folder, workspace.approved_folder)
            self.app._start('historical_preview_export', lambda progress, stop: export_preview(batch, Path(target), protected_roots=roots))
