"""Employee-facing results derived only from existing engine evidence."""
from equipment_data_manager.processing.models import ProcessingStatus

LABELS = {
    'saved': 'Saved successfully',
    'unchanged': 'Already processed / unchanged',
    'review': 'Needs review',
    'failed': 'Failed',
    'stopped': 'Stopped / not processed',
}


def outcome(result):
    if result.code == 'cancelled':
        return 'stopped'
    if result.status == ProcessingStatus.SUCCESS:
        # A preview success alone is not proof of a saved candidate.
        return 'saved' if result.artifact is not None else 'review'
    if result.status == ProcessingStatus.SKIPPED:
        return 'unchanged'
    if result.status == ProcessingStatus.NEEDS_REVIEW:
        return 'review'
    return 'failed'


def counts(entries):
    totals = dict.fromkeys(LABELS, 0)
    totals['warnings'] = 0
    for entry in entries:
        totals[outcome(entry.result)] += 1
        totals['warnings'] += bool(entry.result.warnings)
    return totals


def summary(entries):
    totals = counts(entries)
    return '  |  '.join(f'{label}: {totals[key]}' for key, label in LABELS.items()) + f"  |  With warnings: {totals['warnings']}"


def run_message(entries):
    totals = counts(entries)
    if not entries:
        return 'No reports were processed. Select reports and preview before processing.'
    if totals['failed']:
        caption = 'Run finished with failed reports.'
    elif totals['stopped']:
        caption = 'Run stopped; some reports were not processed.'
    elif totals['review']:
        caption = 'Run finished with reports needing review.'
    else:
        caption = 'Run finished.'
    return (caption + f" {totals['saved']} saved, {totals['unchanged']} unchanged, {totals['review']} need review, "
        f"{totals['failed']} failed, {totals['stopped']} stopped. "
        'Review each row and warning. Local candidates only; no production approval.')


def next_step(result):
    return {
        'saved': 'Next: inspect counts, missing values and warnings. Use Process Multiple Months → Power BI snapshot to combine reviewed saved reports. No production data was updated.',
        'unchanged': 'Next: inspect the existing saved report and its warnings. No new revision was written.',
        'review': 'Next: return to Process Reports, preview and review the affected report. Correction approval alone saves nothing; processing is a separate action.',
        'failed': 'Next: read the explanation, resolve the source or folder problem, then preview again. Use Technical details if your maintainer needs diagnostic evidence.',
        'stopped': 'Next: preview again to process remaining reports. Previously saved reports and revisions remain available in Settings → Processing History.',
    }[outcome(result)]
