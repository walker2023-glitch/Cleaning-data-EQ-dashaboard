"""Versioned, comparison-only observed equipment and evidence-based maintenance.

All functions operate on copied canonical records. No inventory, cleaner, finance,
filesystem-time, activation or network policy is inferred here.
"""
import json
import re

from equipment_data_manager.comparison_enrichment import FACTS
from equipment_data_manager.processing.models import ProcessingError

NAME_POLICY = 'recent-nonblank-month-repairs-first-v1'
EQUIPMENT_POLICY = 'owner-dax-ordered-v1'
MAINTENANCE_POLICY = 'source-evidence-conservative-v1'
EQUIPMENT_FIELDS = ('EquipmentId', 'EquipmentName', 'EquipmentType', 'FirstObservedMonth',
                    'LastObservedMonth', 'ObservationCount', 'NameConflict')
CLASSIFICATION_FIELDS = ('CanonicalDataset', 'ObservedEquipmentName', 'ResolvedEquipmentName',
                         'EquipmentType', 'MaintenanceType')
AUDIT_FIELDS = ('Dataset', 'CanonicalRecordNumber', 'RecordId', 'ReportMonth',
    'SourceFileSHA256', 'SourceRecordNumber', 'EquipmentId', 'ObservedEquipmentName',
    'ResolvedEquipmentName', 'EquipmentType', 'EquipmentRule', 'EquipmentWarnings',
    'NameConflict', 'EquipmentExportRecordNumber', 'SourceMaintenanceTag',
    'OriginalDescription', 'CleanedDescription', 'MaintenanceType', 'MaintenanceEvidence')
CLASS_DIAGNOSTIC_FIELDS = ('Dataset', 'ExportRecordNumber', 'ReportMonth', 'EquipmentId', 'Issue', 'Explanation')

# Preserve the owner's exact ordered categories, including surprising overlaps:
# e.g. Kaivac hits Vac before the later Kaivac rule. Diagnostics flag broad hits.
EQUIPMENT_RULES = (
    ('Battery-powered backpack vacuum', lambda n: 'battery' in n and 'backpack' in n),
    ('Battery-powered vacuum', lambda n: 'battery' in n and ('vacuum' in n or 'vac' in n)),
    ('Backpack Vacuum', lambda n: 'backpack' in n),
    ('Vacuum Trash can', lambda n: 'trash' in n),
    ('Vacuum', lambda n: any(t in n for t in ('vacuum', 'vac', 'versamatic', 'lindhaus', 'puzi'))),
    ('Carpet Cleaner Head', lambda n: 'carpet cleaner head' in n),
    ('Carpet Cleaning Machine', lambda n: 'carpet cleaning machine' in n),
    ('Carpet Cleaning', lambda n: 'carpet cleaning' in n or 'extractor' in n),
    ('Upholstery Cleaner', lambda n: 'upholstery cleaner' in n),
    ('Upholstery machine', lambda n: 'upholstery' in n),
    ('Scrubber', lambda n: any(t in n for t in ('scrubber', 'i18b', 'ice', 'nautilus'))),
    ('Burnisher', lambda n: 'burnisher' in n), ('Buffer', lambda n: 'buffer' in n),
    ('Chariot', lambda n: 'chariot' in n), ('Agitator', lambda n: 'agitator' in n),
    ('Swing Arm', lambda n: 'swing arm' in n or 'rx-20' in n),
    ('Kaivac', lambda n: 'kaivac' in n),
    ('Chemical Dispenser', lambda n: any(t in n for t in ('dispenser', 'chemical', 'mop station'))),
    ('Floor Fan', lambda n: 'fan' in n or 'waxie' in n),
    ('Ladder', lambda n: 'ladder' in n), ('Lift', lambda n: 'lift' in n),
    ('Steamer', lambda n: 'steamer' in n),
)


def normalize_name(name):
    # Remove one z, preserving all other characters/case and the observed value.
    return re.sub('puzzi', lambda m: m[0][:3] + m[0][4:], name, flags=re.I)


def equipment_type(name):
    folded = normalize_name(name).casefold()
    for ordinal, (label, matches) in enumerate(EQUIPMENT_RULES, 1):
        if matches(folded):
            broad = [term for term in ('vac', 'ice', 'trash') if term in folded]
            return label, f'equipment-rule-{ordinal:02}', broad
    return 'Other', 'equipment-default', []


PREVENTIVE = r'\b(?:pm|preventative|preventive|routine|inspection|tune[- ]up|scheduled|annual|quarterly)\b'
CORRECTIVE = r'\b(?:repair(?:s|ed|ing)?|replac(?:e(?:d|s|ments?)?|ing)|broken|fault(?:y)?|failed|failure|leak(?:s|ing)?|fix(?:ed|ing)?|damage(?:d)?|malfunction(?:ing)?)\b'
NEGATIVE = r'\b(?:no|not|never|without|non|cancel(?:led|ed)?)\b|\bdidn[’\x27]t\b'

AMBIGUOUS = r'\b(?:maybe|possible|possibly|unclear|unsure|suspected|might|may|whether)\b|\?|\bcheck\s+if\b'


def _indicators(text):
    return dict(preventive=bool(re.search(PREVENTIVE, text, re.I)),
        corrective=bool(re.search(CORRECTIVE, text, re.I)),
        negative=bool(re.search(NEGATIVE, text, re.I)),
        ambiguous=bool(re.search(AMBIGUOUS, text, re.I)))


def maintenance_type(tag='', original='', cleaned=''):
    """Priority: explicit tag, original text, secondary cleaned text.

    Contradictions/negated/uncertain indicators always require review, including lower-tier
    contradictions. A preventive keyword alone remains provisional, never proof.
    """
    explicit = tag.strip().casefold()
    pm_tags = {'pm', 'preventive', 'preventative', 'preventive maintenance', 'preventative maintenance'}
    repair_tags = {'repair', 'needed repair', 'corrective', 'corrective maintenance'}
    signals = [_indicators(t) for t in (tag, original, cleaned)]
    if explicit in pm_tags:
        signals[0]['preventive'] = True
    if explicit in repair_tags:
        signals[0]['corrective'] = True
    detail = json.dumps(dict(tag=tag, original=original, cleaned=cleaned, signals=signals), sort_keys=True, ensure_ascii=False)
    preventive = any(s['preventive'] for s in signals)
    corrective = any(s['corrective'] for s in signals)
    if (preventive and corrective) or any((s['negative'] or s['ambiguous']) and (s['preventive'] or s['corrective']) for s in signals):
        return 'Needs Review', detail
    if explicit and explicit not in pm_tags | repair_tags:
        # An unrecognized explicit tag must not silently become an approved label.
        return 'Needs Review', detail
    for signal in signals:
        if signal['preventive']:
            return 'Preventive Maintenance', detail
        if signal['corrective']:
            return 'Needed Repair', detail
    return 'Unclassified', detail


def _selection_key(observation):
    kind, ordinal, row = observation
    # Months are validated ISO YYYY-MM. Latest month, then repairs first, then
    # ascending stable source identifiers; CSV ordinal is final identical-row tie.
    return (-int(row['ReportMonth'].replace('-', '')), FACTS.index(kind),
        row.get('RecordId', ''), row.get('SourceFileSHA256', ''),
        row.get('SourceRecordNumber', ''), row.get('CandidateRevisionId', ''),
        row['EquipmentName'], ordinal)


def classify_records(tables, names):
    """Add v3 lookup/fact columns, observation evidence, diagnostics and links."""
    tables = {kind: [dict(r) for r in records] for kind, records in tables.items()}
    grouped = {}
    for kind in FACTS:
        for ordinal, row in enumerate(tables[kind], 1):
            if row['EquipmentId']:
                grouped.setdefault(row['EquipmentId'], []).append((kind, ordinal, row))
    lookup, resolved, links = [], {}, []
    for export_ordinal, identifier in enumerate(sorted(grouped), 1):
        observations = grouped[identifier]
        nonblank = [o for o in observations if o[2]['EquipmentName'].strip()]
        name = normalize_name(min(nonblank, key=_selection_key)[2]['EquipmentName']) if nonblank else ''
        variants = {o[2]['EquipmentName'] for o in nonblank}
        category, rule, warnings = equipment_type(name)
        months = [o[2]['ReportMonth'] for o in observations]
        item = dict(EquipmentId=identifier, EquipmentName=name, EquipmentType=category,
            FirstObservedMonth=min(months), LastObservedMonth=max(months),
            ObservationCount=str(len(observations)), NameConflict='true' if len(variants)>1 else 'false')
        lookup.append(item)
        resolved[identifier] = (item, rule, warnings, export_ordinal)
        for kind, ordinal, row in observations:
            links.append((export_ordinal, kind, ordinal, row))
    audit, diagnostics, evidence = [], [], {}
    counts = dict(equipment_rows=len(lookup), name_conflict_rows=0, equipment_unclassified_rows=0,
        broad_equipment_match_rows=0, maintenance_unclassified_rows=0, maintenance_review_rows=0,
        lookup_fact_mismatches=0)
    for kind in FACTS:
        for ordinal, row in enumerate(tables[kind], 1):
            observed = row['EquipmentName']
            if row['EquipmentId']:
                item, rule, broad, lookup_ordinal = resolved[row['EquipmentId']]
                name, category, conflict = item['EquipmentName'], item['EquipmentType'], item['NameConflict']
            else:
                name = normalize_name(observed)
                category, rule, broad = equipment_type(name)
                conflict, lookup_ordinal = 'false', ''
            original = row.get('RawDescription', row['Description'])
            tag = row.get('SourceMaintenanceTag', '')
            maintenance, detail = maintenance_type(tag, original, row['Description'])
            row.update(EquipmentName=name, ObservedEquipmentName=observed,
                       EquipmentType=category, MaintenanceType=maintenance)
            info = dict(CanonicalDataset=names[kind], ObservedEquipmentName=observed,
                ResolvedEquipmentName=name, EquipmentType=category, MaintenanceType=maintenance)
            evidence[kind, ordinal] = info
            observation = dict(Dataset=names[kind], CanonicalRecordNumber=ordinal,
                RecordId=row.get('RecordId',''), ReportMonth=row['ReportMonth'],
                SourceFileSHA256=row.get('SourceFileSHA256',''), SourceRecordNumber=row.get('SourceRecordNumber',''),
                EquipmentId=row['EquipmentId'], ObservedEquipmentName=observed, ResolvedEquipmentName=name,
                EquipmentType=category, EquipmentRule=rule, EquipmentWarnings=json.dumps(broad),
                NameConflict=conflict, EquipmentExportRecordNumber=lookup_ordinal,
                SourceMaintenanceTag=tag, OriginalDescription=original, CleanedDescription=row['Description'],
                MaintenanceType=maintenance, MaintenanceEvidence=detail)
            audit.append(observation)
            issues=[]
            if conflict=='true':issues.append(('name_conflict_rows','equipment_name_conflict','Competing observed names retained in equipment_observations.csv; latest nonblank name selected provisionally.'))
            if category=='Other':issues.append(('equipment_unclassified_rows','equipment_unclassified','No ordered equipment keyword matched; Other is retained.'))
            if broad:issues.append(('broad_equipment_match_rows','equipment_broad_keyword','Compatibility substring match may be overbroad: '+', '.join(broad)))
            if maintenance=='Unclassified':issues.append(('maintenance_unclassified_rows','maintenance_unclassified','Insufficient maintenance evidence; no report-type default applied.'))
            if maintenance=='Needs Review':issues.append(('maintenance_review_rows','maintenance_needs_review','Conflicting, negated, uncertain or unrecognized explicit maintenance evidence; inspect observation evidence.'))
            for counter,issue,explanation in issues:
                counts[counter]+=1
                diagnostics.append(dict(Dataset=names[kind],ExportRecordNumber=ordinal,ReportMonth=row['ReportMonth'],
                    EquipmentId=row['EquipmentId'],Issue=issue,Explanation=explanation))
    tables['equipment'] = lookup
    validate_lookup(tables)
    return tables, evidence, audit, diagnostics, counts, links


def validate_lookup(tables):
    """Block structural inconsistencies; business uncertainty is warning-only."""
    lookup={r['EquipmentId']:r for r in tables['equipment']}
    if len(lookup)!=len(tables['equipment']) or '' in lookup:
        raise ProcessingError('comparison_equipment_mismatch')
    seen={}
    for kind in FACTS:
        for row in tables[kind]:
            key=row['EquipmentId']
            if not key:continue
            item=lookup.get(key)
            if item is None or any(row[c]!=item[c] for c in ('EquipmentName','EquipmentType')):
                raise ProcessingError('comparison_equipment_mismatch')
            seen[key]=seen.get(key,0)+1
    if set(seen)!=set(lookup) or any(str(seen[k])!=r['ObservationCount'] for k,r in lookup.items()):
        raise ProcessingError('comparison_equipment_mismatch')


def classification_warnings(counts):
    return ('Observed Equipment lookup is not a complete or authoritative inventory.\n'
        f"Equipment rows: {counts['equipment_rows']}; conflicting-name observations: {counts['name_conflict_rows']}.\n"
        f"Other equipment observations: {counts['equipment_unclassified_rows']}; broad keyword observations: {counts['broad_equipment_match_rows']}.\n"
        f"Unclassified maintenance: {counts['maintenance_unclassified_rows']}; maintenance needing review: {counts['maintenance_review_rows']}.\n"
        'Review audit/classification_diagnostics.csv and audit/equipment_observations.csv.\n'
        'Classification uncertainty is a warning; inconsistent lookup/fact keys, names, types or counts block generation.\n')
