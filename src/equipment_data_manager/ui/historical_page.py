"""Read-only inventory screen; processing stays in the existing monthly workflow."""
import json
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
        for key, label in zip(columns, ('Month', 'Repairs', 'Service Orders', 'TMA', 'Inventory status')):
            self.table.heading(key, text=label)
            self.table.column(key, width=130, minwidth=85, stretch=True)
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
        if hasattr(self, 'table'):
            self.table.delete(*self.table.get_children())
            for box in (self.details, self.technical):
                self._text(box, 'Discover the selected range to see an inventory. No processing has run.')
            self.export_button.configure(state='disabled')
            self.summary.configure(text='Selection changed. Discover again; previous results do not describe this selection.')

    def selection_caption(self):
        workspace = self.app.workspace
        root = str(workspace.raw_folder) if workspace else 'Configure Raw Data Folder in Settings'
        layout = LAYOUT_LABELS[self.app.folder_layout]
        self.caption.configure(text=f'{layout}\nRaw root: {root}\nRead-only inventory — found does not mean schema-validated. Cloud sync is unverified.')

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
        for month in inventory.months:
            self.table.insert('', 'end', iid=month.period, values=(month.period,
                *(r.status.replace('_', ' ').title() for r in month.reports),
                'Complete inventory' if month.complete else 'Needs attention'))
        self.summary.configure(text=f'{sum(m.complete for m in inventory.months)} of {len(inventory.months)} months have a complete readable inventory. '
            + ('Stopped; unscanned months are shown. ' if inventory.stopped else '')
            + 'Schemas, row counts and financials have not been previewed. No processing has run.')
        self._text(self.technical, json.dumps(inventory.document(), indent=2))
        self.export_button.configure(state='normal')
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
                lines.extend([f'File: {source.item_id}', f'Size: {source.size_bytes} bytes',
                              f'SHA-256: {source.sha256 or "Unavailable — stable bytes not captured"}'])
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
