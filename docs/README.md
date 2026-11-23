# Equipment Maintenance Analytics — Master Guide

**Purpose:** A starting point for employees, dashboard users, and future maintainers to understand the project, how it changed, what the tools currently do, and where to find detailed instructions.

**Status:** Initial guide. Repository information checked against main commit dc73a80 on November 23, 2026. Several history details are owner-reported; SharePoint destinations are placeholders until approved links are provided.

> **Read this first:** Equipment Data Manager currently creates local review candidates and test datasets. It does not automatically collect reports from SharePoint, publish approved data, or refresh a production Power BI dashboard. An output file is not automatically approved for business use.

## How to use this guide

The linked superscript number after a topic jumps to its explanation below. The topic index is also a table of contents. Each glossary entry has a placeholder for a departmental SharePoint page. Replace placeholders when the department provides approved URLs.

Status labels distinguish evidence from plans:

- **Verified in repository:** supported by code or documentation on the current main branch.
- **Project-history account:** based on the project owner's description; confirm dates, roles, and decisions before treating it as official history.
- **Owner-reported / needs confirmation:** reported by the owner, but the relevant Power BI file, source reports, or departmental acceptance evidence was not inspected.
- **In progress or unmerged:** not part of the verified main-branch baseline.
- **Future direction:** a goal, not a current capability.

## Topic index

1. [Project purpose and audience](#1-project-purpose-and-audience)
2. [Project history](#2-project-history)
3. [Systems and data flow](#3-systems-and-data-flow)
4. [Current capabilities and limits](#4-current-capabilities-and-limits)
5. [Monthly source-report workflow](#5-monthly-source-report-workflow)
6. [Department folder layout](#6-department-folder-layout)
7. [Power BI datasets and their status](#7-power-bi-datasets-and-their-status)
8. [Detailed guides](#8-detailed-guides)
9. [Glossary](#9-glossary)
10. [Resources and project links](#10-resources-and-project-links)
11. [Open questions and maintenance](#11-open-questions-and-maintenance)

## 1. Project purpose and audience

Equipment Maintenance Analytics brings maintenance reports together so Facilities Management employees can review repair and service activity, related costs and labor, and equipment information.

The project has two related parts:

- **Equipment Data Manager (EDM):** a Python desktop application that reads supported maintenance reports and creates local reviewable candidate data.
- **Equipment Maintenance Dashboard:** a Power BI report intended to present maintenance and equipment information.

These are separate tools. Processing a report in EDM does not itself change or refresh a Power BI report. See [Systems and data flow](#3-systems-and-data-flow) and [Power BI datasets](#7-power-bi-datasets-and-their-status).

## 2. Project history

This section records the project owner's account of how the work developed. The sequence is useful context; dates, stakeholder titles, and decisions should be confirmed before this section is treated as an official departmental history.

### Earlier prototype

The project began with work by Abraham Yim. The predecessor repository, [Equipment Lifecycle Analytics](https://github.com/walker2023-glitch/Equipment-Lifecycle-Analytics), describes a Python Dash dashboard and offline data-cleaning tools. It is separate from the current Equipment Data Manager repository. Treat it as predecessor material, not as the current employee workflow.

The original planning document is titled **SIT 0-1 Equipment Dashboard SOP.docx** and is stored in an archived departmental SharePoint location. **SharePoint link: to be added.** It may not describe the current application or workflow.

### How the project changed

**Project-history account:** The initial goal was to help the person responsible for repairs review repair activity, equipment across campus, and related costs. Deployment and access limitations in the early Python-based approach led the project toward Power BI for dashboard viewing. Data processing continued separately and later became the Equipment Data Manager desktop application.

Power BI report sharing still depends on departmental workspace, access, and licensing arrangements. This guide does not promise that every employee can open every Power BI file.

### Additional goals and dashboard ideas

**Owner-reported / needs confirmation:** The project later added requests for a meeting overview, equipment lookup, and equipment counts by building. The owner reports some campus equipment totals may be incomplete because CompuClean does not represent every item, including some sanitizer equipment. Treat these counts as provisional until the data owner confirms the inventory source and reconciles totals.

The owner also reports that an hourly-rate slider was being developed to let users adjust labor assumptions. The current Power BI file was not reviewed for this guide, so the slider's implementation and approval status are unverified.

### Why the data manager exists

The dashboard depends on reports collected from more than one system, and not all employees can retrieve every report directly. The current design therefore includes a desktop application for processing downloaded reports before data is considered for Power BI.

**Future direction:** Make report intake and processing easier, possibly by detecting new source files and preparing data for dashboard use. Automatic SharePoint intake, cleaning, upload, approval, and dashboard refresh are not verified capabilities. See [Current capabilities and limits](#4-current-capabilities-and-limits).

## 3. Systems and data flow

The intended high-level path is:

1. A designated report collector obtains the monthly CompuClean Repair Report, CompuClean Service Orders List, and TMA Work Orders report.
2. Original reports are saved in the correct raw-data month folder and preserved without editing.
3. An employee downloads or selects locally available reports and uses EDM to discover, preview, process, and review them.
4. EDM writes local candidates and, when explicitly requested, a historical snapshot or a development comparison export.
5. An authorized maintainer or user evaluates output in a separate Power BI test copy. Production use requires departmental validation and approval.

The first four steps describe the local-tool design. Production activation and refresh are separate departmental decisions and are not performed automatically by EDM.

[Power BI¹](#power-bi), [Power Query²](#power-query), [CSV³](#csv), and [PBIX⁴](#pbix) appear throughout the project. Definitions and SharePoint-link placeholders are in the [glossary](#9-glossary).

## 4. Current capabilities and limits

This describes the repository's documented main-branch baseline as reviewed November 23, 2026. Check the linked guides and approved release before following exact screen labels.

### Verified in repository

- EDM is a local Python desktop application with workflows for selecting, discovering, previewing, and processing supported reports.
- The application supports CompuClean CSV inputs and supported TMA XLSX or genuine XLS workbook layouts. Unsupported or ambiguous layouts should stop for review.
- Processing creates local candidate revisions. Unchanged inputs can be skipped; corrections require review and successful processing to save a new revision.
- Historical workflows support discovery and review of multiple months. Batch processing creates local candidates after a plan is reviewed and confirmed.
- A historical Power BI snapshot generator creates a canonical four-table local dataset from selected candidate revisions. Outputs are unverified and are not published or refreshed automatically.
- A separate five-table comparison export, comparison-preview-v3, adds observed equipment and maintenance classifications for development comparison. It is explicitly CandidateUnverified / NotApproved, not an approved production export.
- Some Microsoft 365 configuration checks are offline checks only. A valid local configuration check does not mean the app is connected, authorized, or synchronized.

### Not implemented as an employee production workflow

- EDM does not automatically watch SharePoint for new reports.
- EDM does not automatically download CompuClean reports or retrieve the emailed TMA report.
- EDM does not automatically upload candidate or approved files to SharePoint.
- EDM does not provide departmental business approval or production publishing.
- EDM does not refresh or modify the production Power BI report.
- A successful parse, matching total, candidate file, or snapshot is not by itself proof of business accuracy or approval.

The department's preferred Power BI refresh process is manual. The approved PBIX, data connection, validation owner, and publication steps still need documentation in focused departmental guides.

### In progress or unmerged

The employee-interface simplification work was found on the branch [feature/employee-interface-simplification](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard/tree/feature/employee-interface-simplification), one commit ahead of main during review. It changes navigation and labels, including moving processing history into Settings. Do not assume those branch labels are in the main release until the change is merged and Windows acceptance is complete.

## 5. Monthly source-report workflow

The three primary reports currently described for monthly processing are:

| Report | Source | Format and notes |
|---|---|---|
| CompuClean Repair Report | CompuClean → Equipment → Repair Report | Supported UTF-8 CSV. Includes repair records, equipment identifiers, labor hours, repair details, and financial source fields. |
| CompuClean Service Orders List | CompuClean → Equipment → Service Orders List | Supported UTF-8 CSV. Includes service activity, descriptions, dates, and statuses. |
| TMA Work Orders | Sent by the designated employee with TMA access | Supported XLSX or genuine XLS layouts. Project notes say ordinary employees do not currently retrieve it directly. |

The intended routine is to obtain all three reports, save unchanged originals in the correct raw-data month folder, make the needed files locally available, then use EDM to preview and process them. Employees should confirm the reporting month and review warnings and results. Exact CompuClean export controls, filters, and the current report collector must be confirmed with the department before employee instructions are finalized.

See the [employee guide](user_guide.md), [monthly workflow](monthly_workflow.md), and future [data source guide](#11-open-questions-and-maintenance) for detailed procedures. A candidate or snapshot should not be used in a production dashboard until the documented validation process is completed.

## 6. Department folder layout

The intended SharePoint location is **Equipment Maintenance Analytics**. The structure below is documented by the project owner; verify live folder names and access before instructing employees to move or create files.

    Equipment Maintenance Analytics/
    ├── 01_Raw_Data/
    │   └── YYYY/
    │       └── YYYY-MM (Month)/
    ├── 02_Cleaned_Data/
    │   └── YYYY/
    │       └── YYYY-MM (Month)/
    ├── 03_Power_BI/
    │   └── Backups/
    ├── 04_Scripts/
    └── 05_Documentation/

Known qualifications:

- 01_Raw_Data exists and contains original reports grouped by year and month.
- 02_Cleaned_Data was empty at the last review. Its monthly layout is a future convention, not evidence that production cleaned outputs are currently stored there.
- 03_Power_BI contains departmental dashboard files. The Backups convention is approved, but confirm the folder exists before referring employees to it.
- 04_Scripts contains technical resources.
- 05_Documentation is the intended location for approved employee documentation.
- Do not assume a 06_Logs folder exists.
- A separate Equipment Dashboard Data folder has an unknown purpose; this guide does not direct employees to use it.
- Do not reorganize SharePoint folders as part of following this guide.

**SharePoint project-folder link: to be added.** See [Detailed guides](#8-detailed-guides) for the future file-layout procedure.

## 7. Power BI datasets and their status

The repository describes two distinct outputs. They serve different purposes and are not interchangeable.

### Canonical historical snapshot: four tables

A canonical snapshot contains:

- Repairs_History.csv
- ServiceOrders_History.csv
- TMAWorkOrders_History.csv
- RepairFinancialSummaries.csv

It combines selected local candidate revisions into a historical dataset and includes manifests, hashes, counts, and compatibility information. Its status is **CandidateUnverified**. Missing or invalid source months block generation. It is a local test dataset; it does not approve data, edit a PBIX, publish to SharePoint, or refresh a dashboard.

### Development comparison export: five tables

The development export includes the four tables above and adds Equipment_History.csv. It also adds normalized equipment identifiers, observed equipment information, and a provisional maintenance classification.

This export is designed for disconnected testing in a backup PBIX. Building labels and classifications need review; the equipment lookup is based on observed records and is not a complete asset inventory. Its status is **CandidateUnverified / NotApproved**, not an approved production format.

### Dashboard model acceptance

Before using either output in a departmental dashboard, the owner must verify the intended PBIX, table schemas, text handling for equipment identifiers, relationships, measures, counts, missing values, and financial values. A successful syntax check or synthetic test does not prove that the real Power BI model and visuals are correct.

See the [historical snapshot guide](historical_powerbi_dataset.md), [ordered dataset columns](historical_dataset_columns.md), [Power BI compatibility findings](historical_powerbi_compatibility.md), and [V3 comparison guide](comparison_exports_v3.md).

## 8. Detailed guides

This page is an overview. Use the focused guide for detailed steps:

| Topic | Repository guide |
|---|---|
| Start here; project status | This page |
| Employee use of EDM | [User guide](user_guide.md) |
| Configure folders and recover settings | [Settings guide](settings_guide.md) |
| Monthly report handling | [Monthly workflow](monthly_workflow.md) |
| Find months and source reports | [Historical discovery](historical_backfill.md) |
| Plan and run historical batches | [Historical batch processing](historical_batch_processing.md) |
| Create a canonical four-table snapshot | [Historical Power BI dataset](historical_powerbi_dataset.md) |
| Understand the architecture | [Cleaning architecture](cleaning_architecture.md) and [desktop architecture](desktop_architecture.md) |
| Understand V3 development comparison output | [V3 comparison](comparison_exports_v3.md) |
| Review evidence and remaining blockers | [Inputs needed](inputs_needed.md) and [milestone status](milestones.md) |
| Build and distribute a Windows review package | [Windows packaging](windows_packaging.md) |

Some technical documents preserve dated history and may contain older statements superseded by a newer status section. Read each guide's current-status note before relying on older sections. Employee procedures should use exact labels in the approved build.

## 9. Glossary

Each SharePoint destination below is a placeholder. Replace it with the approved page or document URL when supplied. Repository guides provide additional technical detail in the meantime.

### Power BI

Microsoft's reporting and data-visualization application used for the equipment maintenance dashboard. Access and sharing depend on the department's Microsoft environment and licensing.

**SharePoint page:** to be added · **More detail:** [historical dataset guide](historical_powerbi_dataset.md)

### Power Automate

Microsoft's workflow-automation service. It is a possible future tool for automating approved steps; this guide does not document an active production flow for this project.

**SharePoint page:** to be added · **More detail:** [current capabilities and limits](#4-current-capabilities-and-limits)

### TMA

The work-order system that provides the TMA Work Orders report. Project notes say the monthly report is supplied by a designated employee with TMA access.

**SharePoint page:** to be added · **More detail:** [source-report workflow](#5-monthly-source-report-workflow)

### CompuClean

The source system for the Repair Report and Service Orders List. Correct export controls and departmental filters need confirmation before detailed employee instructions are finalized.

**SharePoint page:** to be added · **More detail:** [source-report workflow](#5-monthly-source-report-workflow)

### Python

A programming language used to build EDM and the predecessor dashboard/data tools. Ordinary employees are expected to use an approved Windows application build; maintainers may use the repository's developer instructions.

**SharePoint page:** to be added · **More detail:** [Windows packaging guide](windows_packaging.md)

### Equipment Data Manager (EDM)

The local desktop application that previews and processes supported maintenance reports into candidate data. It does not itself approve, publish, or refresh production Power BI.

**SharePoint page:** to be added · **More detail:** [repository user guide](user_guide.md)

### Power Query

The data-import and transformation language used by Power BI. Changing queries requires testing in a backup PBIX.

**SharePoint page:** to be added · **More detail:** [V3 comparison guide](comparison_exports_v3.md)

### DAX

Data Analysis Expressions, the formula language used for Power BI measures and calculated columns.

**SharePoint page:** to be added · **More detail:** [Power BI compatibility findings](historical_powerbi_compatibility.md)

### PBIX

The file format used by Power BI Desktop reports. A backup PBIX is a separate test copy; editing or refreshing it does not update the production report unless someone separately approves and publishes the change.

**SharePoint page:** to be added · **More detail:** [historical dataset guide](historical_powerbi_dataset.md)

### Candidate

A local output revision created by EDM. A candidate is not automatically approved, published, or suitable for production reporting.

**SharePoint page:** to be added · **More detail:** [monthly workflow](monthly_workflow.md)

### Canonical historical snapshot

The four-table dataset assembled from selected candidate revisions for compatibility and Power BI testing. It is unverified and is not a business approval.

**SharePoint page:** to be added · **More detail:** [historical dataset guide](historical_powerbi_dataset.md)

### Development comparison export

A five-table V3 dataset adding an observed equipment lookup and provisional classifications for development testing. It is not the approved production export.

**SharePoint page:** to be added · **More detail:** [V3 comparison guide](comparison_exports_v3.md)

### SharePoint

The department's collaboration and document-storage environment. The project uses it for raw report organization and intends it as the employee documentation location. The current application does not automatically upload outputs or verify cloud synchronization.

**SharePoint page:** to be added · **More detail:** [department folder layout](#6-department-folder-layout)

### CSV

A comma-separated values text file used for source reports and EDM output datasets. Equipment identifiers should be treated as text so leading zeros are not lost.

**SharePoint page:** to be added · **More detail:** [ordered dataset columns](historical_dataset_columns.md)

## 10. Resources and project links

### Current project

- [Equipment Data Manager repository](https://github.com/walker2023-glitch/Cleaning-data-EQ-dashaboard)
- [Employee guide in the repository](user_guide.md)
- **Department SharePoint project folder:** link to be added
- **Documentation location, Equipment Maintenance Analytics/05_Documentation:** link to be added
- **Current Power BI dashboard:** link to be added

### Earlier project

- [Predecessor Equipment Lifecycle Analytics repository](https://github.com/walker2023-glitch/Equipment-Lifecycle-Analytics)
- **Archived SIT 0-1 Equipment Dashboard SOP.docx:** approved SharePoint link to be added
- **Predecessor repository README:** [view the README](https://github.com/walker2023-glitch/Equipment-Lifecycle-Analytics/blob/main/README.md). It contains developer setup information; it is not an approved employee run procedure. A reviewed local-only maintainer procedure is still needed.

### Learning and AI planning resources

- **LinkedIn Learning:** [Power BI Essential Training](https://www.linkedin.com/learning/power-bi-essential-training-25882735/get-the-competitive-edge-in-business-analysis-with-power-bi) (course access may require BYU-Idaho sign-in).
- **LinkedIn Learning:** [Microsoft Power Automate Essential Training](https://www.linkedin.com/learning/microsoft-power-automate-essential-training-26159458/save-time-by-automating-common-business-processes) (course access may require BYU-Idaho sign-in).
- **Planning conversation used to develop EDM:** approved link or summary to be added.
- **Reusable AI instructions for planning or maintaining EDM:** approved prompt to be added.

The private SharePoint links supplied for the project folder, 05_Documentation, 03_Power_BI, the source guide, the shortcut guide, and the two archived SOPs belong in the internal SharePoint copy. They remain placeholders in this public repository copy.

Do not put private reports, credentials, tokens, or unnecessary personal data into public repositories or AI prompts.

## 11. Open questions and maintenance

Resolve these before treating this page as a complete employee reference:

- Add approved SharePoint links for the project folder, documentation folder, dashboard, and glossary topics.
- Confirm who currently collects each report and the correct CompuClean export settings, date filters, and equipment/building scope.
- Confirm the current status and acceptance of the hourly-rate slider and meeting overview in the Power BI file.
- Confirm the authoritative equipment-count source and how missing assets such as sanitizers should be accounted for.
- Confirm the approved production PBIX, who validates updates, how manual refresh is performed, and who can publish.
- Confirm the employee-interface branch merge and Windows acceptance before updating exact UI labels.
- Add an approved employee installation guide and separate maintainer setup guide.
- Decide whether and when SharePoint intake, processing, approval, and refresh automation will be pursued.

**Repository source of truth:** Keep this guide in the current GitHub repository and link to it from the approved SharePoint documentation area. When the two copies differ, check GitHub main and this page's review date, then update the approved SharePoint copy through the department's normal process.

**Last reviewed:** November 23, 2026
