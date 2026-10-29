"""Record a LOCAL, UNSENT, UNAPPROVED request for an existing candidate month.

Use the invented output of create_powerbi_pilot.py for an offline demonstration.
No identity is authenticated; no approval/publication or network operation exists.
"""
import argparse
import json
from pathlib import Path
from equipment_data_manager.processing.repair_financial import powerbi_coordinator
from equipment_data_manager.review import ReviewService

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-folder',type=Path,required=True)
    parser.add_argument('--raw-folder',type=Path,required=True)
    parser.add_argument('--month',required=True)
    parser.add_argument('--note',required=True)
    args = parser.parse_args()
    service = ReviewService(powerbi_coordinator(args.candidate_folder),raw_folder=args.raw_folder)
    captured = service.capture(args.month)
    record = service.request(args.month,captured['fingerprint'],args.note)
    print(json.dumps(dict(request_id=record['request_id'],status=service.status(record),
        approval_enabled=False,publication_enabled=False,request_sent=False)))
