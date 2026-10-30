"""Equipment Data Manager local desktop. Tk is only touched on its main thread."""

import argparse
from datetime import date
import gc
from time import monotonic
from importlib.resources import files
import os
from pathlib import Path
from queue import Empty
import subprocess
import sys
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from equipment_data_manager.processing.cleaners import validate_period
from equipment_data_manager.processing.models import ProcessingError, ProcessingStatus, ReportType
from equipment_data_manager.settings import default_settings_path, candidate_location_error, FOLDER_KEYS
from equipment_data_manager.ui.preferences import SettingsMixin
from equipment_data_manager.ui.settings_page import SettingsPage
from equipment_data_manager.ui.guidance import Guidance
from equipment_data_manager.ui.help_content import HELP, missing_help
from equipment_data_manager.monthly import Workspace, discover, export_review_packet, load_workspace
from equipment_data_manager.ui.messages import diagnostic_lines, error_message, result_label, warning_message
from equipment_data_manager.ui.worker import BackgroundWorker
from equipment_data_manager.ui.workflow import DesktopWorkflow, SUPPORTED_REPORTS, selected_files

NAVY = "#172B4D"
TEAL = "#087F8C"
BACKGROUND = "#F3F6FA"
TEXT = "#24354B"
MUTED = "#52647A"
UI_FONT = "Segoe UI" if sys.platform == "win32" else "Helvetica"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")


def window_size(screen_width, screen_height, scale):
    """Logical dimensions fit a scaled primary display, leaving taskbar space."""
    return min(1280,max(360,int(screen_width/scale)-40)), min(920,max(360,int(screen_height/scale)-64))


def default_output_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "EquipmentDataManager/Candidates"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/EquipmentDataManager/Candidates"
    return Path.home() / ".local/share/EquipmentDataManager/Candidates"


def sample_path(kind: ReportType) -> Path:
    name = {ReportType.REPAIRS: "repairs_sample.csv",
            ReportType.SERVICE_ORDERS: "service_sample.csv",
            ReportType.TMA_WORK_ORDERS: "tma_sample.xlsx"}[kind]
    return Path(str(files("equipment_data_manager").joinpath("resources", "samples", name)))


def open_directory(path: Path):
    if not path.is_dir():
        raise OSError("Folder is unavailable")
    if sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class EquipmentDataManager(SettingsMixin, ctk.CTk):
    def __init__(self, output_root: Path | None = None, *, workflow=None, settings_path: Path | None = None):
        ctk.set_appearance_mode("light")
        ctk.ThemeManager.theme["CTkFont"]["family"] = UI_FONT
        super().__init__()
        self.title("Equipment Data Manager")
        width,height=window_size(self.winfo_screenwidth(),self.winfo_screenheight(),self._get_window_scaling())
        self.compact_layout=height<800
        scale=self._get_window_scaling()
        left=max(0,int((self.winfo_screenwidth()-width*scale)/2))
        top=max(0,int((self.winfo_screenheight()-height*scale)/2)-16)
        self.geometry(f'{width}x{height}+{left}+{top}')
        self.minsize(min(1100,width),min(800,height))
        self.configure(fg_color=BACKGROUND)
        self.workflow = workflow or DesktopWorkflow(output_root or default_output_root(), output_format="powerbi")
        # CPython can run cyclic finalizers on whichever thread allocates.
        # CTk font/widget finalizers call Tcl, so collect cycles only here on the
        # GUI thread for this single-window app, including while pandas runs.
        self._gc_was_enabled = gc.isenabled()
        gc.disable()
        self._last_gc = monotonic()
        self.worker = BackgroundWorker()
        self.initial_output_root = self.workflow.base_output_root
        autoload = settings_path is not None or (output_root is None and workflow is None)
        self.initialize_settings(settings_path or (default_settings_path() if autoload else self.initial_output_root / 'app-settings.toml'))
        self.guided = ctk.BooleanVar(value=True)
        self.explanation_level = ctk.StringVar(value='Detailed')
        self._restoring_period = False
        self._period_user_changed = False
        self.last_packet = None
        self.workspace = None
        self.monthly_selection = None
        self.sources = ()
        self.previews = ()
        self.results = ()
        self.history_entries = ()
        self.approvals = {}
        self.job = None
        self.close_pending = False
        self.dialog = None
        self.page = "Process Reports"
        self.output_format = ctk.StringVar(value="Power BI CSV candidate" if self.workflow.output_format == "powerbi" else "Legacy candidate")
        self.report = ctk.StringVar(value=ReportType.REPAIRS.value)
        self.month = ctk.StringVar(value=MONTHS[date.today().month - 1])
        self.year = ctk.StringVar(value=str(date.today().year))
        self.month_confirmed = ctk.BooleanVar(value=False)
        self.status = ctk.StringVar(value="Select a report type and local report files, or try a synthetic sample.")
        self._build()
        self.report.trace_add("write", self._report_changed)
        self.month.trace_add("write", self._selection_changed)
        self.year.trace_add("write", self._selection_changed)
        self.month.trace_add("write", self.reporting_month_changed)
        self.year.trace_add("write", self.reporting_month_changed)
        self.guidance = Guidance(self, self.help_context, self.open_context_help,
            self.guided.get, lambda: self.explanation_level.get().lower())
        self.register_guidance()
        self.protocol("WM_DELETE_WINDOW", self.request_close)
        self.poll_id = self.after(75, self._poll)
        if autoload:
            self.show_page('Settings')
            self.settings_page.welcome.configure(text='Welcome: set up your folders')
            self.load_startup_settings()

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        rail_class=ctk.CTkScrollableFrame if self.compact_layout else ctk.CTkFrame
        rail = rail_class(self, fg_color=NAVY, corner_radius=0, width=220)
        rail.grid(row=0, column=0, sticky="nsew")
        if not self.compact_layout:
            rail.grid_propagate(False)
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(8, weight=1)
        ctk.CTkLabel(rail, text="EDM", text_color="white", font=ctk.CTkFont(size=30, weight="bold")).grid(row=0, column=0, padx=24, pady=(32, 4), sticky="w")
        ctk.CTkLabel(rail, text="Equipment\nData Manager", justify="left", text_color="white", font=ctk.CTkFont(size=18, weight="bold")).grid(row=1, column=0, padx=24, pady=(0, 32), sticky="w")
        self.navigation = {}
        for row, name in enumerate(("Process Reports", "Results", "History", "Review & Approval", "Settings", "Help"), 2):
            button = ctk.CTkButton(rail, text=name, anchor="w", height=44, fg_color="transparent", hover_color="#294160", command=lambda value=name: self.show_page(value))
            button.grid(row=row, column=0, padx=14, pady=4, sticky="ew")
            self.navigation[name] = button
        self.guided_switch = ctk.CTkSwitch(rail, text='Guided Mode', variable=self.guided,
            command=self.help_preferences_changed, text_color='white', progress_color=TEAL)
        self.guided_switch.grid(row=9,column=0,sticky='w',padx=20,pady=(8,6))
        self.help_level = ctk.CTkComboBox(rail, variable=self.explanation_level, values=['Brief','Detailed'],
            state='readonly',width=175,command=self.help_preferences_changed)
        self.help_level.grid(row=10,column=0,padx=20,pady=6)
        self.context_help_button=ctk.CTkButton(rail,text='Explain this step · F1',command=self.open_context_help,fg_color='#294160',width=175)
        self.context_help_button.grid(row=11,column=0,padx=20,pady=6)
        ctk.CTkLabel(rail, text="LOCAL / OFFLINE", text_color="#BDE5E8", font=ctk.CTkFont(size=12, weight="bold")).grid(row=12, column=0, padx=24, pady=(12, 4), sticky="w")
        ctk.CTkLabel(rail, text="Desktop prototype\nMicrosoft connection is not enabled", justify="left", wraplength=175, text_color="#D3DFEF", font=ctk.CTkFont(size=11)).grid(row=13, column=0, padx=24, pady=(0, 24), sticky="w")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=28, pady=24)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)
        self.heading = ctk.CTkLabel(main, text="Process Reports", text_color=NAVY, font=ctk.CTkFont(size=28, weight="bold"), anchor="w")
        self.heading.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(main, text="Prepare equipment reports with a clear review at every step.", text_color=MUTED, anchor="w").grid(row=1, column=0, pady=(2, 16), sticky="ew")
        ctk.CTkLabel(main, text="PROTOTYPE  |  Production accuracy has not been verified. Outputs are local candidates for review.", text_color="#754C0B", fg_color="#FFF2D9", corner_radius=8, height=42, wraplength=900).grid(row=2, column=0, pady=(0, 16), sticky="ew")
        self.body = ctk.CTkFrame(main, fg_color="transparent")
        self.body.grid(row=3, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.settings_page = SettingsPage(self.body, self)
        from equipment_data_manager.ui.review_page import ReviewPage
        self.business_review_page = ReviewPage(self.body, self)
        page_class=ctk.CTkScrollableFrame if self.compact_layout else ctk.CTkFrame
        self.processing_page = page_class(self.body, fg_color="transparent")
        self.processing_page.grid(row=0, column=0, sticky="nsew")
        self.processing_page.grid_columnconfigure(0, weight=1)
        self.processing_page.grid_rowconfigure(1, weight=1)
        self._build_controls()
        self.table_frame = ctk.CTkFrame(self.processing_page, fg_color="white", corner_radius=10)
        self.table_frame.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(1, weight=1, minsize=150 if self.compact_layout else 0)
        self.summary = ctk.CTkLabel(self.table_frame, text="No files selected", text_color=TEXT, anchor="w", font=ctk.CTkFont(size=15, weight="bold"))
        self.summary.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 6))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("EDM.Treeview", background="white", foreground=TEXT, rowheight=32, fieldbackground="white", font=(UI_FONT, 10))
        style.configure("EDM.Treeview.Heading", background="#EAF0F7", foreground=NAVY, font=(UI_FONT, 10, "bold"), padding=8)
        style.map("EDM.Treeview", background=[("selected", "#D7EFF0")], foreground=[("selected", NAVY)])
        holder = ctk.CTkFrame(self.table_frame, fg_color="white")
        holder.grid(row=1, column=0, sticky="nsew", padx=16)
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(holder, columns=("file", "type", "month", "status", "rows"), show="headings", style="EDM.Treeview", selectmode="browse", height=5)
        for name, title, width in (("file", "Filename", 210), ("type", "Report type", 170), ("month", "Month", 80), ("status", "Review status", 235), ("rows", "Rows out", 100)):
            self.table.heading(name, text=title)
            self.table.column(name, width=width, minwidth=60, stretch=name in ("file", "status"))
        self.table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scroll.set)
        horizontal = ttk.Scrollbar(holder, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(xscrollcommand=horizontal.set)
        self.table.bind("<<TreeviewSelect>>", self._show_detail)
        self.detail = ctk.CTkTextbox(self.table_frame, height=80, fg_color="#F7F9FC", text_color=TEXT, wrap="word", font=(UI_FONT, 12))
        self.detail.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 8))
        self._detail_text("Select a row to see its counts, warnings and next steps. Your original files stay unchanged.")
        self.review_button = ctk.CTkButton(self.table_frame, text="Review correction...", command=self.review_correction, fg_color=TEAL, state="disabled")
        self.review_button.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 12))

        self.history_page = ctk.CTkFrame(self.body, fg_color="white", corner_radius=10)
        self.history_page.grid_columnconfigure(0, weight=1)
        self.history_page.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.history_page, text="Completed local revisions | Current and previous candidates; not production validation.", text_color=MUTED, anchor="w").grid(row=0, column=0, padx=18, pady=16, sticky="ew")
        self.history_table = ttk.Treeview(self.history_page, columns=("type", "period", "status", "rows", "revision"), show="headings", style="EDM.Treeview", selectmode="browse")
        for column, title in (("type", "Report type"), ("period", "Month"), ("status", "Revision"), ("rows", "Rows out"), ("revision", "Reference")):
            self.history_table.heading(column, text=title)
            self.history_table.column(column, width=150)
        self.history_table.grid(row=1, column=0, sticky="nsew", padx=18)
        actions = ctk.CTkFrame(self.history_page, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=18, pady=16)
        ctk.CTkButton(actions, text="Refresh history", command=self.load_history, fg_color=TEAL).pack(side="left")
        ctk.CTkButton(actions, text="Open selected revision folder", command=self.open_history_output, fg_color=NAVY).pack(side="left", padx=12)
        self.help_page = ctk.CTkFrame(self.body, fg_color="white", corner_radius=10)
        import platform
        import pandas as pd
        from equipment_data_manager.processing import coordinator as engine_module
        from equipment_data_manager.processing.models import ReportType as Kind
        adapter = self.workflow.coordinator.cleaners.get(Kind.TMA_WORK_ORDERS)
        self.runtime_info = (f"January diagnostics v1 | Python {platform.python_version()} | pandas {pd.__version__}\n"
                             f"Engine: {engine_module.__file__}\n"
                             f"TMA adapter: {type(adapter).__name__ if adapter else 'Unavailable'}")
        self.settings_page.advanced_info.configure(text=self.runtime_info + '\nLocal settings: ' + str(self.settings_store.path))
        self.help_page.grid_columnconfigure(0,weight=1)
        self.help_page.grid_rowconfigure(2,weight=1)
        ctk.CTkLabel(self.help_page,text='Offline help: use F1 on a control, or choose a topic below.',
            text_color=TEXT,anchor='w').grid(row=0,column=0,sticky='ew',padx=22,pady=16)
        self.help_topic=ctk.StringVar(value=HELP['status'].title)
        topics=ctk.CTkFrame(self.help_page,fg_color='transparent')
        topics.grid(row=1,column=0,sticky='ew',padx=22,pady=(0,12))
        self.help_topic_picker=ctk.CTkComboBox(topics,variable=self.help_topic,
            values=[item.title for item in HELP.values()],state='readonly',width=320,command=lambda *_:self.refresh_help())
        self.help_topic_picker.pack(side='left')
        ctk.CTkButton(topics,text='Employee guide',command=self.show_employee_guide,fg_color=NAVY).pack(side='left',padx=12)
        self.help_text=ctk.CTkTextbox(self.help_page,wrap='word',fg_color='#F7F9FC',text_color=TEXT,font=(UI_FONT,14))
        self.help_text.grid(row=2,column=0,sticky='nsew',padx=22,pady=(0,22))

        footer = ctk.CTkFrame(main, fg_color="transparent")
        self.app_footer=footer
        footer.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(footer, progress_color=TEAL, height=6)
        self.progress.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.progress.set(0)
        ctk.CTkLabel(footer, textvariable=self.status, text_color=TEXT, wraplength=710, anchor="w", justify="left").grid(row=1, column=0, sticky="ew", pady=(8, 4))
        self.stop_button = ctk.CTkButton(footer, text="Stop after current file", command=self.stop_work, fg_color=NAVY, state="disabled", width=175)
        self.stop_button.grid(row=1, column=1, padx=(12, 0))
        self.output_button = ctk.CTkButton(footer, text="Open output folder", command=self.open_output, fg_color=NAVY, width=155)
        self.output_button.grid(row=1, column=2, padx=(12, 0))
        self.folder_label = ctk.CTkLabel(footer, text=f"Local output: {self.workflow.output_root}", text_color=MUTED, anchor="w", wraplength=850, font=ctk.CTkFont(size=11))
        self.folder_label.grid(row=2, column=0, columnspan=3, sticky="ew")
        self.show_page("Process Reports")

    def _build_controls(self):
        self.controls = ctk.CTkFrame(self.processing_page, fg_color="white", corner_radius=10)
        self.controls.grid(row=0, column=0, sticky="ew")
        self.controls.grid_columnconfigure((0, 1, 2), weight=1)
        self.report_buttons = []
        for column, (kind, title) in enumerate(SUPPORTED_REPORTS.items()):
            card = ctk.CTkFrame(self.controls, fg_color="#EDF5F7", corner_radius=8)
            card.grid(row=0, column=column, padx=(16 if column == 0 else 8, 8), pady=(10, 8), sticky="nsew")
            button = ctk.CTkRadioButton(card, text=title, variable=self.report, value=kind.value, fg_color=TEAL, text_color=NAVY, font=ctk.CTkFont(size=14, weight="bold"))
            button.pack(anchor="w", padx=14, pady=(10, 4))
            ctk.CTkLabel(card, text="TMA | XLSX candidate" if kind == ReportType.TMA_WORK_ORDERS else "CompuClean | Local CSV", text_color=MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14, pady=(0, 8))
            self.report_buttons.append(button)
        row = ctk.CTkFrame(self.controls, fg_color="transparent")
        row.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        self.select_button = ctk.CTkButton(row, text="Select local raw files", command=self.select_files, fg_color=NAVY, height=36)
        self.select_button.pack(side="left")
        self.sample_button = ctk.CTkButton(row, text="Load synthetic sample", command=self.load_sample, fg_color="#E4EDF4", text_color=NAVY, hover_color="#D5E3EF", height=36)
        self.sample_button.pack(side="left", padx=10)
        self.folder_button = ctk.CTkButton(self.settings_page.advanced, text="Choose output folder", command=self.choose_output, fg_color="#E4EDF4", text_color=NAVY, hover_color="#D5E3EF", height=36)
        self.folder_button.grid(row=2,column=0,sticky='w',padx=12,pady=8)
        self.settings_shortcut=ctk.CTkButton(row,text='Settings',command=lambda:self.show_page('Settings'),fg_color=NAVY,width=120)
        self.settings_shortcut.pack(side='left')
        settings = ctk.CTkFrame(self.controls, fg_color="transparent")
        settings.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkLabel(settings, text="Reporting month", text_color=TEXT).pack(side="left", padx=(0, 12))
        self.month_selector = ctk.CTkComboBox(settings, variable=self.month, values=list(MONTHS), state="readonly", width=135)
        self.month_selector.pack(side="left")
        self.year_entry = ctk.CTkEntry(settings, textvariable=self.year, width=70)
        self.year_entry.pack(side="left", padx=8)
        self.month_check = ctk.CTkCheckBox(settings, text="I confirmed this reporting month", variable=self.month_confirmed, fg_color=TEAL, text_color=TEXT, command=self._confirmation_changed)
        self.month_check.pack(side="left", padx=12)
        formats = ctk.CTkFrame(self.controls, fg_color="transparent")
        formats.grid(row=3, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkLabel(formats, text="Output format", text_color=TEXT).pack(side="left", padx=(0, 12))
        self.format_selector = ctk.CTkComboBox(formats, variable=self.output_format,
            values=["Power BI CSV candidate", "Legacy candidate"], state="readonly", width=210,
            command=self._output_format_changed)
        self.format_selector.pack(side="left")
        ctk.CTkLabel(formats, text="Power BI format recommended | Candidates require validation", text_color="#754C0B").pack(side="left", padx=12)
        buttons = ctk.CTkFrame(self.controls, fg_color="transparent")
        buttons.grid(row=4, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 16))
        self.preview_button = ctk.CTkButton(buttons, text="1  Preview Processing", command=self.start_preview, fg_color=NAVY, height=40, width=200)
        self.preview_button.pack(side="left")
        self.process_button = ctk.CTkButton(buttons, text="2  Process Reports", command=self.start_process, fg_color=TEAL, height=40, width=200, state="disabled")
        self.process_button.pack(side="left", padx=12)
        self.packet_button = ctk.CTkButton(buttons, text="Export review packet", command=self.export_packet,
            fg_color=NAVY, height=40, width=165)
        self.packet_button.pack(side="left")
        monthly = row
        self.workspace_button = ctk.CTkButton(self.settings_page.advanced, text="Load folder configuration", command=self.choose_workspace, fg_color=NAVY, width=165)
        self.workspace_button.grid(row=1,column=0,sticky='w',padx=12,pady=8)
        self.scan_button = ctk.CTkButton(monthly, text="Discover month", command=self.scan_month, fg_color=TEAL, width=125)
        self.scan_button.pack(side="left", padx=10)
        self.checklist = ctk.CTkLabel(self.controls, text="Monthly checklist: load a folder configuration to discover all three reports.",
            text_color=MUTED, wraplength=850, anchor="w", justify="left")
        self.checklist.grid(row=5, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))

    def _report_changed(self, *_):
        if self.monthly_selection is not None:
            self.sources = ()
        self.monthly_selection = None
        self.checklist.configure(text="Individual report selection. Load a folder configuration and Discover month to check all report types.")
        self._selection_changed()

    def choose_workspace(self):
        if self.worker.busy:
            return
        path = filedialog.askopenfilename(parent=self, title="Load local folder configuration", filetypes=[("TOML configuration", "*.toml")])
        if path:
            try:
                workspace = load_workspace(Path(path))
            except ProcessingError:
                self.status.set("Invalid folder configuration. Supply three separate raw, candidate and approved folders; see the monthly workflow guide.")
                return
            problem = candidate_location_error(workspace.candidate_folder)
            if problem:
                self.status.set(problem)
                return
            for key in FOLDER_KEYS:
                self.settings_page.path_vars[key].set(str(getattr(workspace,key)))
            self.settings_page.local_confirmed.set(False)
            self.settings_page.message.configure(text='Legacy folder configuration loaded for this session. Check local storage and Save Settings to remember it.')
            self.workspace = workspace
            self.monthly_selection = None
            self.sources = ()
            self.results = ()
            self.workflow = DesktopWorkflow(workspace.candidate_folder, output_format="powerbi")
            self.output_format.set("Power BI CSV candidate")
            self._selection_changed()
            self.folder_label.configure(text=f"Local candidates: {self.workflow.output_root}")
            self.checklist.configure(text="Folder configuration loaded. Select a month, then Discover month. Approved folder is reserved and never written.")
            self.status.set("Configuration loaded. Synchronization has not been verified.")

    def scan_month(self):
        if self.worker.busy:
            return
        if self.workspace is None:
            self.status.set("Load folder configuration first. See workspace.example.toml and docs/monthly_workflow.md.")
            return
        try:
            period = self.period()
        except ProcessingError:
            self.status.set(error_message("invalid_reporting_period"))
            return
        workspace = self.workspace
        self.previews = ()
        self.approvals.clear()
        self.month_confirmed.set(False)
        self._start("discover", lambda progress, stop: discover(workspace, period))

    def export_packet(self):
        if self.worker.busy:
            return
        if self.workspace is None or self.workflow.output_format != "powerbi":
            self.status.set("Load a folder configuration and use Power BI CSV candidate mode before exporting a review packet.")
            return
        try:
            period = self.period()
        except ProcessingError:
            self.status.set(error_message("invalid_reporting_period"))
            return
        workspace, coordinator = self.workspace, self.workflow.coordinator
        self._start("packet", lambda progress, stop: export_review_packet(workspace, coordinator, period))

    def period(self):
        if self.month.get() not in MONTHS:
            raise ProcessingError("invalid_reporting_period")
        value = f"{self.year.get()}-{MONTHS.index(self.month.get()) + 1:02d}"
        validate_period(value)
        return value

    def _selection_changed(self, *_):
        self.previews = ()
        self.approvals.clear()
        self.month_confirmed.set(False)
        self.process_button.configure(state="disabled")
        self.review_button.configure(state="disabled")
        if self.page == "Process Reports":
            self._show_selection()

    def _confirmation_changed(self):
        if not self.month_confirmed.get():
            self._selection_changed()
            self.status.set("Confirm the reporting month and preview again before processing.")

    def set_files(self, paths):
        if self.worker.busy:
            return
        self.monthly_selection = None
        self.sources = selected_files(paths)
        self._selection_changed()
        self.show_page("Process Reports")
        self.status.set(f"{len(self.sources)} file(s) selected. Confirm the report type and month, then preview.")

    def select_files(self):
        is_tma = self.report.get() == ReportType.TMA_WORK_ORDERS.value
        paths = filedialog.askopenfilenames(
            parent=self, title="Select local raw reports",
            filetypes=[("TMA XLSX reports", "*.xlsx"), ("Legacy XLS (unsupported)", "*.xls")] if is_tma else [("CSV reports", "*.csv")],
        )
        if paths:
            self.set_files(paths)

    def load_sample(self):
        if self.worker.busy:
            return
        kind = ReportType(self.report.get())
        month = "January" if kind == ReportType.TMA_WORK_ORDERS else "September"
        self.month.set(month)
        self.year.set("2026")
        self.set_files([str(sample_path(kind))])
        self.status.set(f"Synthetic sample loaded | {month} 2026. Confirm the month, then preview. No departmental data is included.")

    def _output_format_changed(self, *_):
        if self.worker.busy:
            return
        kind = "powerbi" if self.output_format.get() == "Power BI CSV candidate" else "legacy"
        self.workflow = DesktopWorkflow(self.workflow.base_output_root, source=self.workflow.source, output_format=kind)
        self.results = ()
        self._selection_changed()
        self.folder_label.configure(text=f"Local output: {self.workflow.output_root}")
        self.status.set("Output format changed. Confirm the month and preview again. Production publication is blocked.")

    def choose_output(self):
        if self.worker.busy:
            return
        folder = filedialog.askdirectory(parent=self, title="Choose local candidate output folder")
        if folder:
            if self.workspace is not None:
                try:
                    Workspace(self.workspace.raw_folder, Path(folder), self.workspace.approved_folder).validate()
                except ProcessingError:
                    self.status.set("Choose a candidate folder separate from the configured raw and approved folders.")
                    return
            kind = "powerbi" if self.output_format.get() == "Power BI CSV candidate" else "legacy"
            problem = candidate_location_error(Path(folder))
            if problem:
                self.status.set(problem)
                return
            self.workspace = None
            self.monthly_selection = None
            self.workflow = DesktopWorkflow(Path(folder), output_format=kind)
            self.results = ()
            self._selection_changed()
            self.folder_label.configure(text=f"Local output: {self.workflow.output_root}")
            self.status.set("Output folder changed. Preview again against this folder's processing history.")

    def start_preview(self):
        if self.worker.busy:
            return
        self.previews = ()
        self.approvals.clear()
        self.process_button.configure(state="disabled")
        if not self.sources:
            self.status.set("Select local files or load a synthetic sample before previewing.")
            return
        if not self.month_confirmed.get():
            self.status.set("Confirm the reporting month using the checkbox before previewing.")
            return
        try:
            period, kind = self.period(), ReportType(self.report.get())
        except (ProcessingError, ValueError):
            self.status.set(error_message("invalid_reporting_period"))
            return
        if self.monthly_selection and self.monthly_selection.period != period:
            self.status.set("Reporting month changed. Discover month again before previewing.")
            return
        sources = self.sources
        self.show_page("Process Reports")
        if self.monthly_selection:
            selection = self.monthly_selection
            self._start("preview", lambda progress, stop: self.workflow.preview_month(selection, progress, stop))
        else:
            self._start("preview", lambda progress, stop: self.workflow.preview(sources, kind, period, progress, stop))

    def can_process(self):
        return bool(self.previews) and self.month_confirmed.get() and all(
            entry.result.status in (ProcessingStatus.SUCCESS, ProcessingStatus.SKIPPED) or
            (entry.result.status == ProcessingStatus.NEEDS_REVIEW and
             self.approvals.get(index) == entry.result.replacement_token)
            for index, entry in enumerate(self.previews)
        )

    def start_process(self):
        if self.worker.busy:
            return
        if not self.can_process():
            self.status.set("Preview first. Resolve selection errors and approve each correction before processing.")
            return
        entries, approvals = self.previews, dict(self.approvals)
        self._start("process", lambda progress, stop: self.workflow.process(entries, approvals, progress, stop))

    def _start(self, kind, operation):
        if self.settings_blocking():
            self.status.set('Finish checking or saving settings before processing reports.')
            return
        if kind in ('preview','process','packet','history','business_review'):
            problem=candidate_location_error(self.workflow.base_output_root)
            if problem:
                self.status.set(problem)
                return
        if self.worker.start(operation):
            self.job = kind
            self.progress.set(0)
            self._busy_controls(True)
            self.status.set("Previewing reports..." if kind == "preview" else "Processing reports... Original files remain unchanged.")

    def _busy_controls(self, busy):
        busy = busy or self.settings_blocking()
        self.settings_page.busy(busy)
        self.business_review_page.busy(busy)
        state = "disabled" if busy else "normal"
        for widget in (self.select_button, self.sample_button, self.folder_button, self.preview_button,
                       self.workspace_button, self.scan_button, self.packet_button, self.settings_shortcut,
                       self.year_entry, self.month_check, *self.report_buttons, *self.navigation.values()):
            widget.configure(state=state)
        self.month_selector.configure(state="disabled" if busy else "readonly")
        self.format_selector.configure(state="disabled" if busy else "readonly")
        self.process_button.configure(state="normal" if not busy and self.can_process() else "disabled")
        self.review_button.configure(state="disabled")
        self.stop_button.configure(state="normal" if busy else "disabled")

    def _collect_gui_cycles(self):
        if monotonic() - self._last_gc >= 1:
            gc.collect()
            self._last_gc = monotonic()

    def _poll(self):
        self._collect_gui_cycles()
        if self.poll_settings():
            return
        try:
            while True:
                event = self.worker.events.get_nowait()
                if event.kind == "progress":
                    done, total = event.payload
                    self.progress.set(done / total if total else 1)
                    self.status.set(f"{done} of {total} files checked. Please wait...")
                else:
                    self.worker.busy = False
                    self._busy_controls(False)
                    if event.kind == "error":
                        self.previews = ()
                        self.process_button.configure(state="disabled")
                        self.status.set(event.payload + (" Check local folder availability; synchronization is unverified." if self.job in ("discover", "packet") else ""))
                        if self.job == "business_review":
                            self.business_review_page.failed()
                    elif self.job == "business_review":
                        self.business_review_page.completed(event.payload)
                    elif self.job == "discover":
                        self.monthly_selection = event.payload
                        self.sources = tuple(source for _, source in self.monthly_selection.files)
                        self.show_page("Process Reports")
                        self.checklist.configure(text=self.monthly_selection.summary + " No outputs are approved for Power BI.")
                        self.status.set("Discovery complete. Confirm the month, then preview all discovered reports. Sync is unverified.")
                    elif self.job == "packet":
                        self.last_packet=event.payload
                        self.status.set(f"Candidate review packet saved: {event.payload}. Not approved for production Power BI. Sync is unverified.")
                    elif self.job == "preview":
                        self.previews = event.payload
                        self.show_page("Process Reports")
                        self.process_button.configure(state="normal" if self.can_process() else "disabled")
                        self.status.set("Preview complete. Review each row and its warnings before processing.")
                    elif self.job == "process":
                        self.business_review_page.invalidate('Processing finished. Refresh current candidate revisions before review.')
                        self.results = event.payload
                        self.previews = ()
                        self.approvals.clear()
                        self.show_page("Results")
                        self.process_button.configure(state="disabled")
                        self.status.set("Run complete. Review results below. Preview again to process more reports.")
                    elif self.job == "history":
                        self.history_entries = event.payload
                        self._render_history()
                        self.status.set(f"{len(self.history_entries)} completed local revision(s). All remain unverified candidates.")
                    if self.close_pending and not self.settings_worker.busy:
                        self._close()
                        return
        except Empty:
            pass
        self.poll_id = self.after(75, self._poll)

    def stop_work(self):
        self.worker.stop()
        self.stop_button.configure(state="disabled")
        self.status.set("Stopping after the current file. Completed files remain saved.")

    def show_page(self, name):
        if hasattr(self, "guidance"):
            self.guidance.hide()
        if name in ("Process Reports","Results"):
            self.last_report_page=name
        self.page = name
        if name in ('Settings','Help'):
            self.app_footer.grid_remove()
        else:
            self.app_footer.grid()
        for label, button in self.navigation.items():
            button.configure(fg_color=TEAL if label == name else "transparent")
        self.heading.configure(text="Processing results" if name == "Results" else name)
        for frame in (self.processing_page, self.history_page, self.help_page, self.settings_page, self.business_review_page):
            frame.grid_remove()
        if name in ("Process Reports", "Results"):
            self.processing_page.grid(row=0, column=0, sticky="nsew")
            if name == "Results":
                self._render(self.results, preview=False)
            elif self.previews:
                self._render(self.previews, preview=True)
            else:
                self._show_selection()
        elif name == "History":
            self.history_page.grid(row=0, column=0, sticky="nsew")
            self.load_history()
        elif name == "Review & Approval":
            self.business_review_page.grid(row=0,column=0,sticky="nsew")
            self.business_review_page.selection_label()
        elif name == "Settings":
            self.settings_page.grid(row=0,column=0,sticky="nsew")
        else:
            self.help_page.grid(row=0, column=0, sticky="nsew")
            self.refresh_help()

    def _clear_table(self):
        self.table.delete(*self.table.get_children())
        self.review_button.configure(state="disabled")

    def _show_selection(self):
        self._clear_table()
        try:
            period = self.period()
        except ProcessingError:
            period = "Choose month"
        kinds = dict((source, kind) for kind, source in self.monthly_selection.files) if self.monthly_selection else {}
        for index, source in enumerate(self.sources):
            self.table.insert("", "end", iid=str(index), values=(source.name, SUPPORTED_REPORTS.get(kinds.get(source, self.report.get()), "Unsupported"), period, "Preview required", "-"))
        self.summary.configure(text=f"Selected files  |  {len(self.sources)}")
        self._detail_text("Confirm the reporting month, then Preview Processing. No output is created during preview.")

    def _render(self, entries, *, preview):
        self._clear_table()
        counts = {status: 0 for status in ProcessingStatus}
        warning_files = 0
        for index, item in enumerate(entries):
            entry = item if preview else item.preview
            result = item.result
            counts[result.status] += 1
            warning_files += bool(result.warnings)
            label = result_label(result, preview=preview)
            if preview and index in self.approvals:
                label = "Correction approved for this preview"
            self.table.insert("", "end", iid=str(index), values=(entry.source.name, SUPPORTED_REPORTS.get(entry.report_type, "TMA Work Orders"), entry.period, label, result.output_rows if result.output_rows is not None else "-"))
        self.summary.configure(text=(f"{'Preview' if preview else 'Results'}  |  "
            f"{counts[ProcessingStatus.SUCCESS]} {'new' if preview else 'saved'}   "
            f"{counts[ProcessingStatus.SKIPPED]} skipped   {counts[ProcessingStatus.NEEDS_REVIEW]} review   "
            f"{counts[ProcessingStatus.FAILURE]} errors   {warning_files} with warnings"))
        if entries:
            self.table.selection_set("0")
            self._show_detail()
        else:
            self._detail_text("No processing results yet. Start with Process Reports.")

    def _detail_text(self, text):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def _selected_index(self):
        selection = self.table.selection()
        return int(selection[0]) if selection else None

    def _show_detail(self, *_):
        index = self._selected_index()
        entries = self.previews if self.page == "Process Reports" else self.results
        if index is None or index >= len(entries):
            return
        item = entries[index]
        entry = item if self.page == "Process Reports" else item.preview
        result = item.result
        text = [f"{entry.source.name}  |  {entry.period}  |  {self.output_format.get()}",
                f"Rows read: {result.input_rows if result.input_rows is not None else 'Not available'}  |  Rows out: {result.output_rows if result.output_rows is not None else 'Not available'}"]
        if result.status in (ProcessingStatus.FAILURE, ProcessingStatus.NEEDS_REVIEW):
            text.append(error_message(result.code))
        if result.previous:
            text.append(f"Current output: {result.previous.output_rows} rows. Previous revision will be retained.")
        if result.diagnostics:
            text.extend(diagnostic_lines(result.diagnostics))
        text.extend(warning_message(warning) for warning in result.warnings)
        if result.cleaned:
            for metric in result.cleaned.reconciliation_metrics:
                text.append(f"{metric.name}: {metric.value}")
        text.append(f"Selected file: {entry.source.reference}")
        if result.output_location:
            text.append(f"Candidate: {result.output_location}")
        self._detail_text("\n".join(text))
        self.review_button.configure(state="normal" if self.page == "Process Reports" and not self.worker.busy and result.status == ProcessingStatus.NEEDS_REVIEW else "disabled")

    def review_correction(self):
        index = self._selected_index()
        if self.worker.busy or index is None or index >= len(self.previews):
            return
        entry = self.previews[index]
        result = entry.result
        if result.status != ProcessingStatus.NEEDS_REVIEW or result.previous is None:
            return
        dialog = ctk.CTkToplevel(self)
        self.dialog = dialog
        dialog.title("Review corrected monthly report")
        dialog.geometry("640x580")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Review this correction", font=ctk.CTkFont(size=23, weight="bold"), text_color=NAVY).pack(anchor="w", padx=24, pady=(24, 12))
        summary = f"{entry.source.name}\n{SUPPORTED_REPORTS[entry.report_type]} | {entry.period}\n\nCurrent output: {result.previous.output_rows} rows\nProposed output: {result.output_rows} rows\n\nA new local candidate will be selected. The previous revision stays in History.\nProduction accuracy remains unverified."
        if result.cleaned:
            summary += "\n\nProposed totals (not baseline-validated):\n" + "\n".join(f"{metric.name}: {metric.value}" for metric in result.cleaned.reconciliation_metrics)
        ctk.CTkLabel(dialog, text=summary, justify="left", wraplength=580, text_color=TEXT).pack(anchor="w", padx=24)

        def open_previous():
            try:
                open_directory(result.previous.output_path.parent)
            except OSError:
                messagebox.showerror("Folder unavailable", "The current revision folder could not be opened. Keep the history intact.", parent=dialog)

        ctk.CTkButton(dialog, text="Open current revision folder", command=open_previous, fg_color=NAVY).pack(anchor="w", padx=24, pady=(12, 0))
        approved = ctk.BooleanVar(value=False)
        check = ctk.CTkCheckBox(dialog, text="I reviewed and approve this new monthly revision", variable=approved, fg_color=TEAL)
        check.pack(anchor="w", padx=24, pady=16)

        def accept():
            if approved.get() and index < len(self.previews) and self.previews[index] is entry:
                self.approvals[index] = result.replacement_token
                dialog.destroy()
                self._render(self.previews, preview=True)
                self.process_button.configure(state="normal" if self.can_process() else "disabled")
                self.status.set("Correction approved for this preview. Process Reports will recheck the file and current revision.")

        button = ctk.CTkButton(dialog, text="Confirm correction", command=accept, state="disabled", fg_color=TEAL)
        button.pack(anchor="e", padx=24, pady=(0, 16))
        check.configure(command=lambda: button.configure(state="normal" if approved.get() else "disabled"))
        dialog.confirmation_check = check
        dialog.confirm_button = button

    def load_history(self):
        if self.worker.busy:
            return
        self._start("history", lambda progress, stop: self.workflow.coordinator.store.history())

    def _render_history(self):
        self.history_table.delete(*self.history_table.get_children())
        for index, entry in enumerate(self.history_entries):
            self.history_table.insert("", "end", iid=str(index), values=(SUPPORTED_REPORTS.get(entry.report_type, "Unsupported"), entry.period, "Current candidate" if entry.is_current else "Previous candidate", entry.artifact.output_rows, entry.artifact.revision_id[:12]))

    def open_output(self):
        folder = self.workflow.output_root
        index = self._selected_index()
        if self.page == "Results" and index is not None and index < len(self.results):
            location = self.results[index].result.output_location
            if location is not None:
                folder = location.parent
        try:
            open_directory(folder)
        except OSError:
            self.status.set("The output folder is not available yet. Process a report or choose another local folder.")

    def open_history_output(self):
        selected = self.history_table.selection()
        if selected:
            try:
                open_directory(self.history_entries[int(selected[0])].artifact.output_path.parent)
            except OSError:
                self.status.set("This revision folder is missing or unavailable. Keep the remaining history intact.")

    def request_close(self):
        self.flush_help_preferences()
        if not self.worker.busy and self.settings_worker.busy and self.settings_task == 'preferences':
            self.close_pending = True
            return
        if self.worker.busy or self.settings_worker.busy:
            if messagebox.askyesno("Finish current operation?", "Finish the active file or folder/settings check, then close? Completed outputs and saved settings will remain.", parent=self):
                self.close_pending = True
                self.stop_work()
                self.settings_worker.stop()
        else:
            self._close()

    def _close(self):
        self.guidance.hide()
        self.settings_worker.close(wait=True)
        self.worker.close(wait=True)
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.after_cancel(self.poll_id)
        self.destroy()
        gc.collect()
        if self._gc_was_enabled:
            gc.enable()

    def register_guidance(self):
        controls={self.scan_button:'discover',self.preview_button:'preview',self.process_button:'process',
            self.packet_button:'packet',self.review_button:'correction',self.month_selector:'month',
            self.year_entry:'month',self.month_check:'month',self.workspace_button:'load_config',
            self.sample_button:'sample',self.select_button:'select_files',self.stop_button:'stop',
            self.output_button:'output',self.folder_button:'candidate_folder',self.guided_switch:'guided',
            self.help_level:'detail',self.table:'status',self.detail:'warnings',self.checklist:'discover',
            self.history_table:'history',self.settings_shortcut:'save_settings',
            self.settings_page.check_button:'check_locations',self.settings_page.save_button:'save_settings',
            self.settings_page.reset_button:'reset',self.settings_page.import_button:'import_settings',
            self.settings_page.export_button:'export_settings',self.settings_page.local_check:'candidate_folder',
            self.settings_page.recommended_button:'candidate_folder',
            self.business_review_page.load_button:'business_review',self.business_review_page.evidence:'validation_evidence',
            self.business_review_page.request_button:'request_approval',self.business_review_page.note:'validation_evidence',
            self.business_review_page.approve_button:'approval_status',self.business_review_page.publish_button:'publication_readiness',
            self.business_review_page.history_button:'publication_history',
            self.business_review_page.month_picker:'review_month',self.business_review_page.year_entry:'review_month',
            self.business_review_page.month_caption:'review_month',self.business_review_page.tabs:'review_sections',
            self.business_review_page.counts:'review_sections',self.business_review_page.financial:'review_sections',
            self.business_review_page.issues:'warnings',self.business_review_page.revisions:'validation_evidence',
            self.business_review_page.review_history:'review_stages',self.business_review_page.sign_in_button:'review_identity',
            self.settings_page.m365_check_button:'m365_test_config',self.settings_page.graph_button:'storage_connection',self.settings_page.connection_status:'storage_connection'}
        for widget,key in controls.items():
            self.guidance.register(widget,key)
        for widget,kind in zip(self.report_buttons,SUPPORTED_REPORTS):
            self.guidance.register(widget,kind.value)
        for key in FOLDER_KEYS:
            for widget in (self.settings_page.entries[key],self.settings_page.browse_buttons[key],self.settings_page.indicators[key]):
                self.guidance.register(widget,key)
        for name,widget in self.navigation.items():
            self.guidance.register(widget, 'business_review' if name=='Review & Approval' else 'history' if name=='History' else 'save_settings' if name=='Settings' else 'status')
        for widget in self.business_review_page.stage_labels:
            self.guidance.register(widget,'review_stages')
        self.guidance.register(self.format_selector,'powerbi')
        self.guidance.register(self.settings_page.format_picker,'powerbi')

    def help_context(self,key):
        if key=='review_identity':
            return self.business_review_page.identity_provider.readiness().explanation
        if key=='review_month':
            return f'Current selection: {self.month.get()} {self.year.get()}. Saved reporting period: {self.saved_settings.preferences.reporting_period or "none yet"}. Month confirmation is never restored.'
        if key=='legacy' or key=='powerbi':
            active='Legacy candidate' if self.workflow.output_format=='legacy' else 'Power BI CSV candidate'
            return f'Current processing format: {active}. Changing format requires another preview; histories are separate.'
        if key=='discover' and self.workspace is None:
            return 'Monthly discovery is unavailable until folders are configured. Open Settings, Browse to all three folders, then Save Settings.'
        if key=='process':
            if self.worker.busy:
                return 'An operation is running. Let it finish, or Stop After Current File. Help does not change the run.'
            if not self.month_confirmed.get():
                return 'Select and confirm the month represented by the reports before processing.'
            if not self.previews:
                return 'Process Reports is unavailable until you select files and successfully Preview Processing.'
            if any(e.result.status==ProcessingStatus.NEEDS_REVIEW and i not in self.approvals for i,e in enumerate(self.previews)):
                return 'A potential correction needs explicit review. Select its row and use Review Correction before processing.'
            if not self.can_process():
                return 'Resolve preview errors first. Select the rejected row and read its dates, counts and next step.'
        if key=='correction' and not any(e.result.status==ProcessingStatus.NEEDS_REVIEW for e in self.previews):
            return 'Review Correction is available only for a potential correction found by preview. Select that row to review it; ordinary new or duplicate reports do not need correction approval.'
        if key=='preview' and not self.sources:
            return 'Select local raw files or Discover Month before previewing. Samples are available for practice.'
        if key=='packet' and self.last_packet is not None:
            return f'Last exported packet: {self.last_packet}. It is for review only and is not approved for production Power BI.'
        if self.monthly_selection is not None and self.monthly_selection.missing and key in ('discover','status','packet'):
            return missing_help({k.value for k in self.monthly_selection.missing})
        items=self.previews if getattr(self,'last_report_page','Process Reports')!='Results' else self.results
        index=self._selected_index()
        if items and index is not None and index<len(items) and key in ('status','warnings','correction','process'):
            result=items[index].result
            if result.status==ProcessingStatus.SKIPPED:
                return 'Duplicate source: this content is already processed. It will skip rather than add another candidate.'
            if result.status==ProcessingStatus.NEEDS_REVIEW:
                return 'Potential correction: another candidate exists for this report type/month. Review both versions; confirmation is not financial approval.'
            if result.status==ProcessingStatus.FAILURE:
                return error_message(result.code)+' Select this row to inspect its local date/count details. Do not rename unsupported XLS files.'
            if any('repair_source_totals_differ' in note or 'repair_cost_mapping_unverified' in note for note in result.warnings):
                return HELP['warnings'].brief+' '+HELP['warnings'].warning+' Compare source and candidate totals with the financial reviewer.'
            if result.output_location is not None:
                return f'Candidate saved at {result.output_location}. Review it and its warnings before exporting a packet; production accuracy remains unverified.'
        if key in ('status','month') and not self.month_confirmed.get():
            return 'Choose the source reporting month and confirm it using the checkbox. The download date is not necessarily the reporting month.'
        return ''

    def refresh_help(self):
        if not hasattr(self,'guidance'):
            return
        key=next((k for k,entry in HELP.items() if entry.title==self.help_topic.get()),'status')
        self.help_text.configure(state='normal')
        self.help_text.delete('1.0','end')
        self.help_text.insert('1.0',HELP[key].title+'\n\n'+self.guidance.text(key))
        self.help_text.configure(state='disabled')

    def open_context_help(self,key=None):
        if key is None:
            key=('save_settings' if self.workspace is None else 'month' if not self.month_confirmed.get()
                else 'status' if self.results and getattr(self,'last_report_page','')=='Results'
                else 'correction' if any(e.result.status==ProcessingStatus.NEEDS_REVIEW for e in self.previews)
                else 'process' if self.previews else 'preview' if self.sources else 'discover')
        self.help_topic.set(HELP[key].title)
        self.show_page('Help')
        self.help_topic_picker.focus_set()

    def show_employee_guide(self):
        guide=files('equipment_data_manager').joinpath('resources','guides','user_guide.md').read_text(encoding='utf-8')
        self.help_text.configure(state='normal')
        self.help_text.delete('1.0','end')
        self.help_text.insert('1.0',guide)
        self.help_text.configure(state='disabled')

    def report_callback_exception(self, *_):
        self.previews = ()
        self.process_button.configure(state="disabled")
        self.status.set("An unexpected interface error occurred. Preview again before processing.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Equipment Data Manager local desktop")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--settings-file", type=Path, help="Use a separate local preferences file for a setup preview")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-restore-settings",type=Path,help=argparse.SUPPRESS)
    parser.add_argument("--check-m365-components",type=Path,help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check_m365_components:
        from equipment_data_manager.m365_components import main as component_main
        return component_main(["--output",str(args.check_m365_components)])
    if args.smoke_restore_settings:
        from equipment_data_manager.ui.smoke import run_restore_smoke
        return run_restore_smoke(args.smoke_restore_settings,args.smoke_dir)
    if args.smoke_test:
        from equipment_data_manager.ui.smoke import run_smoke
        return run_smoke(args.smoke_dir)
    app = EquipmentDataManager(args.output_dir,settings_path=args.settings_file)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
