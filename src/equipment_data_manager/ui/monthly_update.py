"""Employee hybrid controls; all storage work uses the existing worker queue."""
from dataclasses import asdict
import json
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from equipment_data_manager.monthly import _packet_identifier
from equipment_data_manager.monthly_update import preview_update, generate_update, REBUILD


class MonthlyUpdateControls(ctk.CTkFrame):
    def __init__(self, parent, dataset):
        super().__init__(parent)
        self.dataset=dataset; self.app=dataset.app; self.history=dataset.history
        self.plan=None; self.baseline=None; self.destination=None
        self.grid_columnconfigure(0,weight=1)
        self.caption=ctk.CTkLabel(self,text='Baseline: none — initial historical build. Choose an existing completed snapshot for monthly updates.',wraplength=730,justify='left')
        self.caption.grid(row=0,column=0,sticky='w',padx=8,pady=4)
        buttons=ctk.CTkFrame(self);buttons.grid(row=1,column=0,sticky='w',padx=8)
        self.baseline_button=ctk.CTkButton(buttons,text='Choose completed baseline',command=self.choose_baseline,width=210)
        self.baseline_button.pack(side='left',padx=3,pady=4)
        self.initial_button=ctk.CTkButton(buttons,text='Initial build (no baseline)',command=self.initial,width=210)
        self.initial_button.pack(side='left',padx=3,pady=4)
        self.destination_button=ctk.CTkButton(self,text='Choose new local output location',command=self.choose_destination,width=260)
        self.destination_button.grid(row=2,column=0,sticky='w',padx=8,pady=4)
        self.destination_label=ctk.CTkLabel(self,text='Destination: choose a trusted local parent before preview.',wraplength=730,justify='left')
        self.destination_label.grid(row=3,column=0,sticky='w',padx=8)
        self.preview_button=ctk.CTkButton(self,text='Review monthly update',command=self.preview,width=230)
        self.preview_button.grid(row=4,column=0,sticky='w',padx=8,pady=4)
        self.recommendation=ctk.CTkLabel(self,text='Review the proposed range above. No output has been generated.',wraplength=730,justify='left')
        self.recommendation.grid(row=5,column=0,sticky='w',padx=8,pady=4)
        self.mode=ctk.StringVar(value=REBUILD)
        self.mode_menu=ctk.CTkOptionMenu(self,variable=self.mode,values=[REBUILD],command=lambda *_:self.reset_confirmation())
        self.mode_menu.grid(row=6,column=0,sticky='w',padx=8,pady=4)
        self.confirmed=ctk.BooleanVar(value=False);self.changes=ctk.BooleanVar(value=False)
        self.confirm=ctk.CTkCheckBox(self,text='I reviewed the plan, compatibility gaps and trusted local destination.',variable=self.confirmed,command=lambda:self.busy(False))
        self.confirm.grid(row=7,column=0,sticky='w',padx=8,pady=4)
        self.change_confirm=ctk.CTkCheckBox(self,text='I authorize the displayed replacements and removals for this new version.',variable=self.changes,command=lambda:self.busy(False))
        self.change_confirm.grid(row=8,column=0,sticky='w',padx=8,pady=4)
        self.generate_button=ctk.CTkButton(self,text='Generate confirmed monthly update',command=self.generate,width=280)
        self.generate_button.grid(row=9,column=0,sticky='w',padx=8,pady=8)

    def invalidate(self):
        self.plan=None;self.reset_confirmation()
        self.recommendation.configure(text='Plan changed or not reviewed. Review monthly update before confirming.')

    def reset_confirmation(self):
        self.confirmed.set(False);self.changes.set(False);self.busy(False)

    def choose_baseline(self):
        path=filedialog.askdirectory(parent=self.app,title='Choose one completed baseline folder ending in snapshot')
        if path:
            self.baseline=Path(path);self.caption.configure(text='Explicit baseline: '+path)
            self.dataset.invalidate()

    def initial(self):
        if self.baseline and not messagebox.askyesno('Start an independent initial build?',
            'No previous history will be compared. Previous outputs remain intact. For a normal monthly update, choose its completed baseline instead. Continue?',parent=self.app):return
        self.baseline=None
        self.caption.configure(text='Baseline: none — initial historical build. Existing outputs will not be selected automatically.')
        self.dataset.invalidate()

    def choose_destination(self):
        parent=filedialog.askdirectory(parent=self.app,title='Choose trusted local output parent outside raw, candidates, approved and production')
        if parent:
            self.destination=Path(parent)/('Monthly_Update_Test_'+_packet_identifier())
            self.destination_label.configure(text='New output: '+str(self.destination))
            self.dataset.invalidate()

    def busy(self,value):
        ready=self.app.workspace is not None and not (value or self.app.worker.busy or self.app.settings_worker.busy)
        for widget in (self.baseline_button,self.initial_button,self.destination_button,self.preview_button):
            widget.configure(state='normal' if ready else 'disabled')
        allowed=bool(self.plan and self.plan.permitted)
        for widget in (self.mode_menu,self.confirm):widget.configure(state='normal' if ready and allowed else 'disabled')
        self.change_confirm.configure(state='normal' if ready and allowed and self.plan.changes_history else 'disabled')
        permitted=allowed and self.confirmed.get() and (not self.plan.changes_history or self.changes.get())
        self.generate_button.configure(state='normal' if ready and permitted else 'disabled')

    def preview(self):
        if self.app.worker.busy or self.app.settings_worker.busy or self.app.workspace is None:return
        if not self.destination:self.choose_destination()
        if not self.destination:return
        self.dataset.invalidate()
        workspace=self.app.workspace;start,end=self.history.start.get(),self.history.end.get()
        layout=self.app.folder_layout;baseline=self.baseline;destination=self.destination
        self.app._start('monthly_update_preview',lambda progress,stop:preview_update(workspace,start,end,layout,destination,
            baseline=baseline,progress=progress,cancelled=stop))

    def previewed(self,plan):
        if plan.dataset:self.dataset.previewed(plan.dataset)
        self.plan=plan;self.reset_confirmation()
        self.recommendation.configure(text=plan.recommendation+(' — initial historical build' if not plan.baseline else ''))
        self.mode_menu.configure(values=list(plan.permitted) or [plan.recommendation])
        self.mode.set(plan.permitted[0] if plan.permitted else plan.recommendation)
        self.history._text(self.dataset.detail,plan.summary())
        self.history._text(self.dataset.technical,json.dumps(asdict(plan),indent=2))
        self.history.summary.configure(text=plan.recommendation+'. Review included/excluded months, revisions, counts, warnings and output location below. No output written.')
        self.busy(False)

    def generate(self):
        if self.app.worker.busy or self.app.settings_worker.busy or not self.plan or not self.confirmed.get():return
        plan=self.plan;mode=self.mode.get()
        if mode not in plan.permitted or (plan.changes_history and not self.changes.get()):return
        if not messagebox.askyesno('Generate this new local version?',mode+'\n'+plan.summary()+'\nConfirm this exact plan? Previous outputs remain unchanged.',parent=self.app):return
        confirmation=plan.confirmation(mode);changes=self.changes.get();workspace=self.app.workspace
        self.reset_confirmation()
        self.app._start('monthly_update_create',lambda progress,stop:generate_update(workspace,plan,
            mode=mode,confirmation=confirmation,changes_confirmed=changes,local_confirmed=True,
            compatibility_acknowledged=True,progress=progress,cancelled=stop))

    def completed(self,path):
        self.dataset.completed(path);self.plan=None
        self.recommendation.configure(text='Saved successfully — new local unapproved version. Choose it explicitly as baseline for the next review.')
        self.busy(False)

    def failed(self):
        self.plan=None;self.dataset.failed()
        self.recommendation.configure(text='Stopped / failed / review required — no new completed output. Review current evidence and preview again.')
        self.busy(False)
