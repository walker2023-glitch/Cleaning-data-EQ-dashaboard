"""Independent test oracles for the documented V3 compatibility contract.

No application classifier/resolver is imported. These check compatibility with
approved provisional rules; they do not approve those rules as business truth.
"""
import re

FACTS = ('repairs', 'service_orders')


def identifier(value):
    if not value.strip():return '', 'missing'
    match=re.fullmatch(r'([REZ])\s*([0-9]+)',value)
    if not match:return value,'unsupported'
    normalized=match[1]+match[2]
    return normalized,'normalized' if value!=normalized else 'unchanged'


def display_name(value):
    return re.sub('puzzi',lambda match:match[0][:3]+match[0][4:],value,flags=re.I)


def equipment(name):
    text=display_name(name).casefold()
    has=lambda *terms:any(term in text for term in terms)
    rules=[
        ('battery' in text and 'backpack' in text,'Battery-powered backpack vacuum'),
        ('battery' in text and has('vacuum','vac'),'Battery-powered vacuum'),
        (has('backpack'),'Backpack Vacuum'),(has('trash'),'Vacuum Trash can'),
        (has('vacuum','vac','versamatic','lindhaus','puzi'),'Vacuum'),
        (has('carpet cleaner head'),'Carpet Cleaner Head'),
        (has('carpet cleaning machine'),'Carpet Cleaning Machine'),
        (has('carpet cleaning','extractor'),'Carpet Cleaning'),
        (has('upholstery cleaner'),'Upholstery Cleaner'),(has('upholstery'),'Upholstery machine'),
        (has('scrubber','i18b','ice','nautilus'),'Scrubber'),(has('burnisher'),'Burnisher'),
        (has('buffer'),'Buffer'),(has('chariot'),'Chariot'),(has('agitator'),'Agitator'),
        (has('swing arm','rx-20'),'Swing Arm'),(has('kaivac'),'Kaivac'),
        (has('dispenser','chemical','mop station'),'Chemical Dispenser'),
        (has('fan','waxie'),'Floor Fan'),(has('ladder'),'Ladder'),(has('lift'),'Lift'),(has('steamer'),'Steamer')]
    for i,(matches,label) in enumerate(rules,1):
        if matches:return label,f'equipment-rule-{i:02}',[term for term in ('vac','ice','trash') if term in text]
    return 'Other','equipment-default',[]


def room_label(value):
    if '\r' in value or '\n' in value:return ''
    match=re.fullmatch(r'(.+?)[^\S\r\n]+([0-9]{1,4}[A-Za-z]?)',value.strip())
    if not match:return ''
    label=match[1].strip()
    if (not label or not label[0].isalpha() or not(label[-1].isalpha() or label[-1]=='.')
        or label.casefold() in ('building','bldg','bldg.','room','rm','rm.','floor')
        or any(not(c.isalpha() or c in " .'-&") for c in label)):return ''
    return label


def building(location,known):
    value=location.strip()
    if not value:return '', 'missing'
    if '\n' in location or '\r' in location:return '', 'ambiguous'
    label=room_label(location)
    if label:return label,'room_pattern'
    if value in known:return value,'observed_building_only'
    return '', 'ambiguous' if any(c.isdigit() or c in '/\\,;:' for c in value) else 'unresolved'


def maintenance(tag,original,cleaned):
    signals=[]
    for text in (tag,original,cleaned):
        signals.append(dict(
            preventive=bool(re.search(r'\b(pm|preventative|preventive|routine|inspection|tune[- ]up|scheduled|annual|quarterly)\b',text,re.I)),
            corrective=bool(re.search(r'\b(repair(s|ed|ing)?|replac(e(d|s|ments?)?|ing)|broken|fault(y)?|failed|failure|leak(s|ing)?|fix(ed|ing)?|damage(d)?|malfunction(ing)?)\b',text,re.I)),
            negative=bool(re.search(r"\b(no|not|never|without|non|cancel(led|ed)?)\b|\bdidn['’]t\b",text,re.I)),
            ambiguous=bool(re.search(r'\b(maybe|possible|possibly|unclear|unsure|suspected|might|may|whether)\b|\?|\bcheck\s+if\b',text,re.I))))
    explicit=tag.strip().casefold()
    pm={'pm','preventive','preventative','preventive maintenance','preventative maintenance'}
    repair={'repair','needed repair','corrective','corrective maintenance'}
    if explicit in pm:signals[0]['preventive']=True
    if explicit in repair:signals[0]['corrective']=True
    preventive=any(s['preventive'] for s in signals);corrective=any(s['corrective'] for s in signals)
    uncertain=any((s['negative'] or s['ambiguous']) and(s['preventive'] or s['corrective']) for s in signals)
    if preventive and corrective or uncertain or explicit and explicit not in pm|repair:return 'Needs Review',signals
    for signal in signals:
        if signal['preventive']:return 'Preventive Maintenance',signals
        if signal['corrective']:return 'Needed Repair',signals
    return 'Unclassified',signals


def resolve_equipment(canonical):
    groups={}
    for kind in FACTS:
        for ordinal,row in enumerate(canonical[kind],1):
            key,_=identifier(row['EquipmentId'])
            if key:groups.setdefault(key,[]).append((kind,ordinal,row))
    resolved={}
    for ordinal,key in enumerate(sorted(groups),1):
        observations=groups[key]
        nonblank=[o for o in observations if o[2]['EquipmentName'].strip()]
        def order(o):
            kind,record,row=o
            return(-int(row['ReportMonth'].replace('-','')),FACTS.index(kind),row.get('RecordId',''),
                row.get('SourceFileSHA256',''),row.get('SourceRecordNumber',''),row.get('CandidateRevisionId',''),row['EquipmentName'],record)
        name=display_name(min(nonblank,key=order)[2]['EquipmentName']) if nonblank else ''
        months=[o[2]['ReportMonth'] for o in observations]
        label,rule,broad=equipment(name)
        resolved[key]=dict(row=dict(EquipmentId=key,EquipmentName=name,EquipmentType=label,
            FirstObservedMonth=min(months),LastObservedMonth=max(months),ObservationCount=str(len(observations)),
            NameConflict=str(len({o[2]['EquipmentName'] for o in nonblank})>1).lower()),ordinal=ordinal,rule=rule,broad=broad)
    return resolved
