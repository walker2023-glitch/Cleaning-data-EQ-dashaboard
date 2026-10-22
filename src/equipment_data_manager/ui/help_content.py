"""Offline help registry. Update entries here without changing event handlers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class HelpEntry:
    control_id: str
    title: str
    brief: str
    detailed: str
    dashboard: str
    affects: str
    next_step: str
    warning: str = ''
    guide: str = 'user_guide.md'

    def text(self, level='detailed', context=''):
        if level == 'brief':
            return '\n\n'.join(part for part in (self.brief, context, 'Warning: '+self.warning if self.warning else '') if part)
        return '\n\n'.join(part for part in (self.detailed, self.dashboard,
            f'Files and information: {self.affects}', f'Next: {self.next_step}',
            'Warning: '+self.warning if self.warning else '', context) if part)


HELP = {}


def entry(key, title, brief, detail, affects, next_step, warning='', dashboard='This prepares maintenance information for the Equipment Maintenance Dashboard.'):
    HELP[key] = HelpEntry(key, title, brief, detail, dashboard, affects, next_step, warning)


entry('discover', 'Discover month', 'Searches your Raw Data folders for reports belonging to the selected month.',
    'Checks whether the selected month has CompuClean Repair Reports, Service Orders Lists, and TMA Work Orders. This helps identify missing information before updating the Equipment Maintenance Dashboard.',
    'Direct files in Raw Data / year-month / report type. Historical subfolders are not scanned.',
    'Review the files and missing-report checklist, confirm the month, then select Preview Processing.',
    'Discovery does not download reports or verify OneDrive synchronization.')
entry('preview', 'Preview Processing', 'Checks the selected files without creating cleaned outputs.',
    'Examines reports for supported formats, reporting dates, duplicates, existing revisions and potential problems. Preview does not modify original reports or publish data to Power BI.',
    'Selected raw files and the current candidate history, read only.', 'Review every warning and resolve errors or corrections before processing.')
entry('process', 'Process Reports', 'Runs the cleaning process and creates candidate files.',
    'Uses the existing cleaning engine to transform selected reports into consistent CSV files. Original reports are preserved. Results are candidates for review; they are not automatically approved, uploaded to SharePoint or loaded into Power BI.',
    'Selected source files are read; new candidate revisions are saved in the Candidate Output folder.',
    'Review Results, then export a review packet when all three current report types are available.',
    'Existing financial calculations remain unverified; a successful run is not business approval.')
entry('packet', 'Export Review Packet', "Creates a review package containing the selected month's current cleaned reports.",
    'Collects one current candidate per report type for the selected month, with hashes, counts and warnings. This packet is for inspection and comparison, not an approved production release.',
    'A new immutable folder under Candidate Output / review_packets. It uses last successful current candidates, not an unsaved correction.',
    'Inspect the packet and follow the separate departmental validation procedure.', 'A failed later attempt does not replace the last successful candidate. Check that the intended source revisions were processed.')
entry('correction', 'Review Correction', 'Reviews changes to a report that has already been processed.',
    'Shows current and proposed candidate counts and totals. Confirming a correction allows processing to select a new candidate revision while preserving the earlier version. It does not provide business or financial approval.',
    'Only the proposed report type/month and its source-bound correction acknowledgement.',
    'Compare both candidates, check the explicit confirmation box, then Process Reports.', 'Changing the source or current revision requires another preview and review.')
entry('powerbi', 'Power BI CSV Candidate', 'Creates standardized CSV files designed for Power BI review.',
    'Produces header-first CSVs with consistent columns, ISO dates, text identifiers, reporting-month information and source tracking. These simplify imports but still require validation before production use.',
    'Separate normalized candidate history; original cleaning rules remain unchanged.',
    'Preview and process, then compare candidate counts and totals with trusted examples.', 'Recommended format; candidates are not approved or automatically published.')
entry('legacy', 'Legacy CSV', 'Produces the original report-style cleaned output.',
    'Uses the previous output format for compatibility and comparison. Repair and TMA files can include titles and introductory rows, making them less suitable for direct folder ingestion.',
    'Separate legacy candidate revisions, with the same cleaning calculations and exclusions.',
    'Use for comparison; choose Power BI CSV Candidate for standardized review tables.')
entry('history', 'History', 'Shows previously processed candidate versions.',
    'Locate current and previous saved revisions for troubleshooting and recovery. This history contains candidates, not business-approved releases or a permanent log of failed attempts.',
    'Completed local candidate revisions in the selected output format/store.', 'Select a revision and open its folder to inspect it.',
    'Power BI must not automatically combine historical revision folders.')
entry('load_config', 'Load Folder Configuration', 'Loads an existing folder configuration for this session.',
    'Advanced compatibility option for existing three-folder TOML files. Most employees should use Settings and Save Settings instead. Loading a legacy file does not automatically save it as your startup preferences.',
    'Folder routing and the active candidate store; files are not moved.', 'Use Settings to validate and save the folder choices for future launches.')
entry('month', 'Reporting Month', 'Selects the month represented by the reports.',
    'Choose the month covered by the source reports, not necessarily the month they were downloaded. Incorrect selection can cause a valid report to be rejected.',
    'The month passed to the existing date and reporting-period checks.', 'Confirm the source month with the checkbox; discover again if you changed months.')
entry('raw_folder', 'Raw Data Folder', 'Holds the original CompuClean and TMA reports.',
    'Choose the root containing year-month folders with repairs, service_orders and tma_work_orders subfolders. The application reads these reports and never overwrites them.',
    'Original CSV/XLSX exports only.', 'Select the root using Browse, then Check Locations.',
    'Synced sources must be locally available. The app cannot verify cloud synchronization.')
entry('candidate_folder', 'Candidate Output Folder', 'Stores cleaned candidates, processing history and review packets on this computer.',
    'Choose a trusted local disk folder outside OneDrive, SharePoint, network shares and other sync services. Shared or synced history can cause conflicts and damage the selected-version record.',
    'New candidate files and local processing history; existing history is never moved when settings change.',
    'Use Browse and confirm local storage. Ask IT if the location is managed by a sync service.',
    'Known network/sync locations are blocked. Detection cannot identify every third-party sync configuration.')
entry('approved_folder', 'Approved Output Folder', 'Reserves a location for future approved exports.',
    'Select a separate location for a future approved Power BI workflow. This version cannot publish approved outputs there. An empty folder may be created only with your confirmation.',
    'A reserved location; no report is copied or approved by saving this setting.',
    'Keep it separate from raw and candidate folders; follow the separate approval procedure.',
    'No production publishing is implemented.')
entry('repairs', 'CompuClean Repair Reports', 'Provides equipment repair history, labor hours and cost-related values.',
    'CompuClean Repair Reports supply equipment information, repair history and labor/cost estimates for the dashboard. Select a supported CSV export for its actual reporting month.',
    'Equipment IDs, locations, dates, repair counts, hours and existing financial estimates.',
    'Preview the CSV and inspect counts, dates and financial warnings.', 'Repair financial mapping, default hours and labor rate still need business validation.')
entry('service_orders', 'CompuClean Service Orders Lists', 'Provides scheduled and completed service activity.',
    'Service Orders Lists contain scheduled/completed dates, equipment information, service descriptions and status. Preserved descriptions and source tags may support future preventive-versus-corrective analysis.',
    'Supported CompuClean service CSV exports and their existing date/exclusion rules.',
    'Preview dates, statuses, exclusions and missing-price warnings.', 'Maintenance classification is a future design, not an implemented feature.')
entry('tma_work_orders', 'TMA Work Orders', 'Provides supported TMA XLSX work orders supplied by Tim.',
    'TMA Work Orders are currently supplied by Tim and may describe Facilities activities not captured in CompuClean equipment repair history. Only the supported XLSX title/header/footer layout is enabled.',
    'Work-order IDs, request dates, requestors, requests and assignments.',
    'Choose the original supported XLSX export and its reporting month.', 'Legacy XLS is unsupported until verified. Do not rename an XLS extension to pretend it is XLSX.')
entry('select_files', 'Select Local Raw Files', 'Selects original files for one report type.',
    'Use the file picker for the selected report type, or Discover Month to find all three types through your saved folder settings.',
    'Selected raw CSVs, or TMA XLSX files.', 'Confirm the report type/month and Preview Processing.')
entry('sample', 'Load Synthetic Sample', 'Loads an invented example for practice.',
    'Bundled samples contain invented data. CompuClean samples use September 2026; TMA uses January 2026.',
    'Only synthetic samples and any candidates you choose to process.', 'Confirm the sample month and try preview before processing.')
entry('stop', 'Stop After Current File', 'Stops remaining files after the active file finishes.',
    'Processing does not interrupt a file during its safe commit. Completed candidates remain saved; a monthly run is not one transaction.',
    'Files not yet started; completed outputs are retained.', 'Review partial results and preview again before continuing.')
entry('output', 'Open Output Folder', 'Opens the selected candidate folder on this computer.',
    'Opens a selected saved result or the active candidate root. It does not upload files or open an approved release.',
    'Local folder navigation only.', 'Inspect the CSV in an authorized viewer; retain its warnings and source metadata.')
entry('save_settings', 'Save Settings', 'Validates and remembers your folder choices and preferences.',
    'Checks separate folder locations and local candidate storage, then saves preferences atomically on this computer. Missing folders require explicit confirmation before creation.',
    'Only local application settings and explicitly confirmed empty folders; existing reports/history are not moved.',
    'After saving, select a month on Process Reports and Discover Month.')
entry('check_locations', 'Check Locations', 'Checks the selected folders and access.',
    'Checks folder separation, availability and local candidate storage. A temporary access probe may be created and removed in the candidate folder; original reports are never touched.',
    'Folder metadata/access checks, not report contents or cloud synchronization.', 'Resolve each message, then Save Settings. Missing locations need confirmation.')
entry('reset', 'Reset to Defaults', 'Forgets saved folder choices after confirmation.',
    'Resets local application preferences to Guided Mode Detailed and Power BI CSV Candidate. It does not delete, move or clean up reports, history or review packets.',
    'Only this application settings file; all data folders remain unchanged.', 'Choose folders again and Save Settings.')
entry('guided', 'Guided Mode', 'Shows explanations while you use the application.',
    'Enable offline hover and focus explanations. Turn them off at any time without changing processing behavior. F1 and the Help page remain available even when Guided Mode is off.',
    'Help display and the saved preference only.', 'Choose Brief or Detailed explanations to suit your experience.')
entry('detail', 'Explanation Detail', 'Chooses Brief or Detailed help.',
    'Brief gives a short description. Detailed adds dashboard context, affected files, next steps and limitations. Your choice is remembered.',
    'Help wording only, never cleaning behavior.', 'Hover over a control, focus it, or press F1 to read help.')
entry('import_settings', 'Import Settings', 'Imports an existing local TOML settings file.',
    'Advanced users can import versioned settings or the older three-folder workspace format. Imported choices are a draft until validated and saved.',
    'Settings fields only; no source reports or candidate history are copied.', 'Check Locations, confirm local candidate storage and Save Settings.')
entry('export_settings', 'Export Sanitized Template', 'Saves a blank, credential-free settings template.',
    'Exports the supported configuration shape with blank folders and default preferences. It omits your actual paths and preferences; it is not a backup of organizational settings.',
    'Only the new file selected in the save dialog, with overwrite confirmation.', 'Provide to a maintainer if they need the supported settings format.')
entry('status', 'Status and Next Step', 'Explains the current step and what needs attention.',
    'Read the current status and select a report row for its counts, dates, errors and warnings. Errors stop the affected operation; warnings need review and are not financial approval.',
    'Displayed processing information only.', 'Use the instructions below or F1 on the relevant control.')
entry('warnings', 'Warnings and Financial Review', 'Warnings identify information that needs review.',
    'Repair source financial totals may disagree with calculated estimates. Field meanings, rate/default policies and trusted baseline comparisons are unresolved. Do not ignore this warning or treat candidate success as approval.',
    'Interpretation of candidate counts, estimates and source totals.', 'Compare with trusted expected outputs and obtain the designated financial reviewer\'s decision.',
    'Existing calculations are preserved. Production publication remains blocked.')


def missing_help(kinds):
    notes = []
    if 'repairs' in kinds:
        notes.append('Missing CompuClean Repair Report: obtain its CSV export for this month.')
    if 'service_orders' in kinds:
        notes.append('Missing CompuClean Service Orders List: obtain its CSV export for this month.')
    if 'tma_work_orders' in kinds:
        notes.append('Missing TMA Work Orders: request the supported XLSX report currently supplied by Tim.')
    return '\n'.join(notes)
