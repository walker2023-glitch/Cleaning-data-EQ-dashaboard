"""Settings form only. Filesystem work and persistence run outside Tk."""
import customtkinter as ctk

from equipment_data_manager.settings import FOLDER_KEYS, Preferences, UserSettings

LABELS = {'raw_folder': 'Raw Data Folder', 'candidate_folder': 'Candidate Output Folder',
          'approved_folder': 'Approved Output Folder (reserved)'}
DESCRIPTIONS = {
    'raw_folder': 'Original reports, arranged by year-month and report type. Originals are never overwritten.',
    'candidate_folder': 'Cleaned candidates, history and review packets. Choose a trusted local disk outside sync services.',
    'approved_folder': 'Future approved exports only. Saving this setting does not publish or approve reports.'}


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='white', corner_radius=10)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0,weight=1)
        self.content=ctk.CTkScrollableFrame(self,fg_color='white')
        self.content.grid(row=0,column=0,sticky='nsew')
        self.content.grid_columnconfigure(0,weight=1)
        self.footer=ctk.CTkFrame(self,fg_color='white')
        self.footer.grid(row=1,column=0,sticky='ew')
        self.footer.grid_columnconfigure(0,weight=1)
        self.welcome = ctk.CTkLabel(self.content, text='Settings', anchor='w', font=ctk.CTkFont(size=22, weight='bold'), text_color='#172B4D')
        self.welcome.grid(row=0, column=0, sticky='ew', padx=22, pady=(18,4))
        ctk.CTkLabel(self.content, text='Choose folders with Browse, confirm local candidate storage, then Check Locations and Save Settings.',
            wraplength=820, justify='left', anchor='w', text_color='#52647A').grid(row=1,column=0,sticky='ew',padx=22,pady=(0,12))
        self.path_vars, self.entries, self.browse_buttons, self.indicators = {}, {}, {}, {}
        for index, key in enumerate(FOLDER_KEYS):
            card = ctk.CTkFrame(self.content, fg_color='#F3F6FA')
            card.grid(row=index+2,column=0,sticky='ew',padx=22,pady=6)
            card.grid_columnconfigure(0,weight=1)
            ctk.CTkLabel(card,text=LABELS[key],anchor='w',font=ctk.CTkFont(size=15,weight='bold'),text_color='#172B4D').grid(row=0,column=0,sticky='ew',padx=12,pady=(8,2))
            ctk.CTkLabel(card,text=DESCRIPTIONS[key],wraplength=760,justify='left',anchor='w',text_color='#52647A').grid(row=1,column=0,columnspan=2,sticky='ew',padx=12,pady=(0,5))
            variable = ctk.StringVar(value='')
            self.path_vars[key] = variable
            self.entries[key] = ctk.CTkEntry(card,textvariable=variable,state='readonly',height=32)
            self.entries[key].grid(row=2,column=0,sticky='ew',padx=(12,8))
            button=ctk.CTkButton(card,text='Browse...',width=100,command=lambda key=key: app.browse_setting(key),fg_color='#172B4D')
            button.grid(row=2,column=1,padx=(0,12))
            self.browse_buttons[key]=button
            indicator=ctk.CTkLabel(card,text='Not checked',anchor='w',wraplength=780,justify='left',text_color='#754C0B')
            indicator.grid(row=3,column=0,columnspan=2,sticky='ew',padx=12,pady=(3,8))
            self.indicators[key]=indicator
            if key=='candidate_folder':
                self.recommended_button=ctk.CTkButton(card,text='Use recommended local folder',command=app.use_recommended_candidate,
                    fg_color='#E4EDF4',text_color='#172B4D',width=235)
                self.recommended_button.grid(row=4,column=0,columnspan=2,sticky='w',padx=12,pady=(0,8))
            variable.trace_add('write',lambda *args,k=key: self.indicators[k].configure(text='Not checked',text_color='#754C0B'))
        self.local_confirmed=ctk.BooleanVar(value=False)
        self.local_check=ctk.CTkCheckBox(self.content,text='I confirm candidate history is on this computer and is not synchronized or shared.',
            variable=self.local_confirmed,text_color='#24354B',fg_color='#087F8C')
        self.local_check.grid(row=5,column=0,sticky='w',padx=24,pady=(12,8))
        self.preferred_format=ctk.StringVar(value='Power BI CSV candidate')
        preferences=ctk.CTkFrame(self.content,fg_color='transparent');preferences.grid(row=6,column=0,sticky='ew',padx=22,pady=8)
        ctk.CTkLabel(preferences,text='Preferred output format',text_color='#24354B').pack(side='left',padx=(0,12))
        self.format_picker=ctk.CTkComboBox(preferences,variable=self.preferred_format,values=['Power BI CSV candidate','Legacy candidate'],state='readonly',width=210)
        self.format_picker.pack(side='left')
        ctk.CTkLabel(self.content,text='Guided Mode & Help: use the switch and Brief / Detailed choice in the left navigation. F1 opens help for a control.',
            anchor='w',justify='left',wraplength=820,text_color='#52647A').grid(row=7,column=0,sticky='ew',padx=22,pady=8)
        actions=ctk.CTkFrame(self.footer,fg_color='transparent');actions.grid(row=0,column=0,sticky='ew',padx=22,pady=10)
        self.check_button=ctk.CTkButton(actions,text='Check Locations',command=app.check_settings,fg_color='#172B4D')
        self.check_button.pack(side='left')
        self.save_button=ctk.CTkButton(actions,text='Save Settings',command=app.save_settings,fg_color='#087F8C')
        self.save_button.pack(side='left',padx=10)
        self.reset_button=ctk.CTkButton(actions,text='Reset to Defaults',command=app.reset_settings,fg_color='#172B4D')
        self.reset_button.pack(side='left')
        self.message=ctk.CTkLabel(self.footer,text='Your settings contain no credentials. Existing reports and history are not moved.',anchor='w',justify='left',wraplength=820,text_color='#24354B')
        self.message.grid(row=1,column=0,sticky='ew',padx=22,pady=8)
        ctk.CTkLabel(self.content,text='Equipment Data Manager | Local/offline prototype | Production accuracy unverified',anchor='w',wraplength=820,text_color='#52647A').grid(row=10,column=0,sticky='ew',padx=22,pady=8)
        self.advanced_button=ctk.CTkButton(self.content,text='Advanced Settings (show)',command=self.toggle_advanced,fg_color='#E4EDF4',text_color='#172B4D')
        self.advanced_button.grid(row=11,column=0,sticky='w',padx=22,pady=8)
        self.advanced=ctk.CTkFrame(self.content,fg_color='#F3F6FA');self.advanced.grid_columnconfigure(0,weight=1)
        self.import_button=ctk.CTkButton(self.advanced,text='Import Settings',command=app.import_settings,fg_color='#172B4D')
        self.import_button.grid(row=0,column=0,sticky='w',padx=12,pady=10)
        self.export_button=ctk.CTkButton(self.advanced,text='Export Sanitized Template',command=app.export_settings_template,fg_color='#172B4D')
        self.export_button.grid(row=0,column=1,sticky='w',padx=12,pady=10)
        self.advanced_info=ctk.CTkLabel(self.advanced,text='',wraplength=790,anchor='w',justify='left',text_color='#52647A')
        self.advanced_info.grid(row=3,column=0,columnspan=2,sticky='ew',padx=12,pady=12)
        self.advanced_visible=False

    def toggle_advanced(self):
        self.advanced_visible=not self.advanced_visible
        if self.advanced_visible:
            self.advanced.grid(row=12,column=0,sticky='ew',padx=22,pady=(0,16))
        else:
            self.advanced.grid_remove()
        self.advanced_button.configure(text='Advanced Settings (hide)' if self.advanced_visible else 'Advanced Settings (show)')

    def populate(self, settings):
        for key in FOLDER_KEYS:
            self.path_vars[key].set(settings.folders[key])
        self.local_confirmed.set(settings.preferences.candidate_local_confirmed)
        self.preferred_format.set('Power BI CSV candidate' if settings.preferences.output_format=='powerbi' else 'Legacy candidate')

    def snapshot(self):
        return UserSettings({key: var.get() for key,var in self.path_vars.items()}, Preferences(
            self.app.guided.get(), self.app.explanation_level.get().lower(),
            'powerbi' if self.preferred_format.get()=='Power BI CSV candidate' else 'legacy', self.local_confirmed.get()))

    def show_check(self, check):
        for key in FOLDER_KEYS:
            text=check.messages.get(key,'Check this folder again.')
            ready=text.startswith('Ready')
            creation=text.startswith('Needs creation')
            self.indicators[key].configure(text=text if ready or creation else 'Needs attention: '+text,
                text_color='#087F8C' if ready else '#754C0B' if creation else '#9F2639')

    def busy(self, value):
        for widget in (*self.browse_buttons.values(),self.recommended_button,self.local_check,self.check_button,self.save_button,self.reset_button,self.import_button,self.export_button):
            widget.configure(state='disabled' if value else 'normal')
        self.format_picker.configure(state='disabled' if value else 'readonly')
