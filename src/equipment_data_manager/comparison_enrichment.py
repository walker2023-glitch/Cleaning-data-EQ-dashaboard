"""Conservative comparison-only enrichment; no inventory or financial inference."""
from dataclasses import dataclass
import json
import re


ID_POLICY = 'rez-spacing-v1'
BUILDING_POLICY = 'room-suffix-v1'
FACTS = ('repairs', 'service_orders')
DIAGNOSTIC_FIELDS = ('Dataset', 'ExportRecordNumber', 'ReportMonth', 'Issue',
    'CanonicalEquipmentId', 'RawEquipmentId', 'EquipmentId', 'OriginalVariants',
    'Location', 'Building', 'LegacyBuilding', 'LegacyBuildingPolicy', 'Explanation')
EVIDENCE_FIELDS = ('CanonicalEquipmentId', 'EquipmentId', 'RawEquipmentId', 'Location',
    'Building', 'BuildingStatus', 'EquipmentIdStatus', 'LegacyBuilding', 'LegacyBuildingPolicy', 'Collision')
EXPLANATIONS = {
    'id_missing': 'Equipment ID is missing. Check the source report; no prefix was inferred.',
    'id_unsupported': 'ID format is outside uppercase R/E/Z plus ASCII digits. It was left unchanged; confirm it with the data owner.',
    'id_collision': 'Different canonical IDs converge on this ID. Confirm whether these are aliases before joining equipment; all transactions remain.',
    'building_missing': 'Location is empty. Check the source; Building remains blank.',
    'building_unresolved': 'Location has no recognized room suffix or observed building-only match. Confirm a Building_Dim key; Building remains blank.',
    'building_ambiguous': 'Location contains numbers in the building label, multiple locations or an unsupported room format. Confirm the building; no value was guessed.',
    'legacy_building_difference': 'The conservative Building differs from the documented legacy rule for this report. Compare Building_Dim and the backup PBIX before migration.',
}


@dataclass(frozen=True)
class Resolution:
    value: str
    status: str


def normalize_equipment_id(identifier: str) -> Resolution:
    """Remove ONLY whitespace between a known uppercase prefix and ASCII digits."""
    if not identifier or identifier.isspace():
        return Resolution('', 'missing')
    match = re.fullmatch(r'([REZ])\s*([0-9]+)', identifier)
    if match is None:
        return Resolution(identifier, 'unsupported')
    value = ''.join(match.groups())
    return Resolution(value, 'unchanged' if value == identifier else 'normalized')


def _room_building(location):
    # Horizontal separation, 1–4 ASCII room digits, optional single suffix letter.
    # No building number, multi-location delimiter, floor/range or line-break guess.
    if any(c in location for c in '\r\n'):
        return ''
    match = re.fullmatch(r'(.+?)[^\S\r\n]+([0-9]{1,4}[A-Za-z]?)', location.strip())
    if match is None:
        return ''
    label = match[1].strip()
    if (not label or not label[0].isalpha() or not (label[-1].isalpha() or label[-1] == '.')
            or label.casefold() in {'building', 'bldg', 'bldg.', 'room', 'rm', 'rm.', 'floor'}):
        return ''
    if any(not (c.isalpha() or c in " .'-&") for c in label):
        return ''
    return label


def resolve_building(location: str, recognized_buildings=()) -> Resolution:
    """Likely labels from a narrow format, never an authoritative dimension key.

    Building-only recognition is exact and case-sensitive. The export supplies
    labels observed in room-qualified locations in this same selected snapshot.
    There is no hardcoded departmental vocabulary or inferred alias expansion.
    """
    text = location.strip()
    if not text:
        return Resolution('', 'missing')
    if any(c in location for c in '\r\n'):
        return Resolution('', 'ambiguous')
    building = _room_building(location)
    if building:
        return Resolution(building, 'room_pattern')
    if text in recognized_buildings:
        return Resolution(text, 'observed_building_only')
    ambiguous = any(c.isdigit() or c in '/\\,;:\r\n' for c in text)
    return Resolution('', 'ambiguous' if ambiguous else 'unresolved')


def legacy_building(location, kind):
    """Documented PBIX reference rules, not verified execution of the M runtime."""
    if kind == 'repairs':
        return re.split(r'[0-9]', location.strip(), maxsplit=1)[0].strip(), 'repairs_before_first_digit'
    # Preserve the distinct service last-literal-space policy. A no-delimiter
    # input has no usable reference here; actual PBIX error handling is unknown.
    return location.rsplit(' ', 1)[0] if ' ' in location else '', 'service_before_final_space'


def enrich_records(canonical, names):
    """Return copied records, per-occurrence evidence and deterministic issues."""
    recognized = {_room_building(row['Location']) for kind in FACTS for row in canonical[kind]}
    recognized.discard('')
    variants = {}
    for kind in FACTS:
        for row in canonical[kind]:
            result = normalize_equipment_id(row['EquipmentId'])
            if result.status in ('normalized', 'unchanged'):
                variants.setdefault(result.value, set()).add(row['EquipmentId'])
    tables = {kind: [dict(row) for row in rows] for kind, rows in canonical.items()}
    evidence, diagnostics = {}, []
    counts = dict(normalized_rows=0, collision_groups=0, collision_rows=0,
        unsupported_ids=0, missing_ids=0, unresolved_buildings=0, legacy_building_differences=0)
    counts['collision_groups'] = sum(len(v) > 1 for v in variants.values())
    for kind in FACTS:
        for ordinal, row in enumerate(tables[kind], 1):
            original = row['EquipmentId']
            identifier = normalize_equipment_id(original)
            building = resolve_building(row['Location'], recognized)
            legacy, policy = legacy_building(row['Location'], kind)
            collision = len(variants.get(identifier.value, ())) > 1
            row.update(EquipmentId=identifier.value, Building=building.value)
            info = dict(CanonicalEquipmentId=original, EquipmentId=identifier.value,
                RawEquipmentId=row['RawEquipmentId'], Location=row['Location'], Building=building.value,
                BuildingStatus=building.status, EquipmentIdStatus=identifier.status,
                LegacyBuilding=legacy, LegacyBuildingPolicy=policy, Collision='true' if collision else 'false')
            evidence[kind, ordinal] = info
            issues = []
            counts['normalized_rows'] += identifier.status == 'normalized'
            if identifier.status in ('missing', 'unsupported'):
                issues.append('id_' + identifier.status)
                counts['missing_ids' if identifier.status == 'missing' else 'unsupported_ids'] += 1
            if collision:
                issues.append('id_collision'); counts['collision_rows'] += 1
            if building.status in ('missing', 'ambiguous', 'unresolved'):
                issues.append('building_' + building.status); counts['unresolved_buildings'] += 1
            if building.value != legacy:
                issues.append('legacy_building_difference'); counts['legacy_building_differences'] += 1
            for issue in issues:
                entry = {key: info.get(key, '') for key in DIAGNOSTIC_FIELDS}
                entry.update(Dataset=names[kind], ExportRecordNumber=ordinal, ReportMonth=row['ReportMonth'],
                    Issue=issue, OriginalVariants=json.dumps(sorted(variants[identifier.value]), ensure_ascii=False)
                    if collision else '', Explanation=EXPLANATIONS[issue])
                diagnostics.append(entry)
    return tables, evidence, diagnostics, counts


def warnings_text(counts):
    return ('Development comparison warnings — not business approval\n'
        'Building labels are format-based observations, not validated Building_Dim keys.\n'
        f"Supported IDs normalized: {counts['normalized_rows']} row(s).\n"
        f"ID collisions: {counts['collision_groups']} group(s), {counts['collision_rows']} row(s).\n"
        f"Unsupported IDs left unchanged: {counts['unsupported_ids']}; missing IDs: {counts['missing_ids']}.\n"
        f"Unresolved Building values: {counts['unresolved_buildings']}; differences from legacy rules: {counts['legacy_building_differences']}.\n"
        'Review affected IDs and locations in audit/diagnostics.csv; each issue identifies its dataset and record number.\n'
        'Confirm aliases and Building_Dim matches with the data owner before changing model relationships.\n'
        'Every transaction is retained. Original IDs, locations and financial evidence remain in audit/canonical and audit/lineage.csv.\n')
