#!/usr/bin/env python3
"""Rebuild a local ledger from recorded events; never fetch sources or invoke models."""
import argparse
import json
from pathlib import Path
from lab import Lab


def replay(recording, db):
    if Path(db).exists():
        raise ValueError('replay destination must not exist')
    lab = Lab(db)
    try:
        lab.init({'question': recording['question'], 'budget': recording['budget']})
        for event in recording['events']:
            phase, data = event['phase'], event['data']
            if phase == 'decide':
                request = lab.request()
                if request['id'] != data['id']:
                    raise ValueError('request sequence differs')
            elif phase == 'act':
                u = data['usage']
                reservation = lab.reserve(data['kind'], u.get('queries', 0), u.get('pages', 0))
                if reservation.get('reservation') != data['reservation']:
                    raise ValueError('reservation sequence differs')
            elif phase == 'observe' and 'reservation' in data:
                lab.observe(data['reservation'], data['result'])
            elif phase == 'verify' and 'response' in data:
                lab.submit(data['request'], data['response'])
        result = lab.export()
        result['replay_notice'] = 'Recorded protocol replay, not a fresh research run or independent evidence verification. New local timestamps are replay times.'
        return result
    finally:
        lab.db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording', required=True)
    parser.add_argument('--db', required=True)
    args = parser.parse_args()
    print(json.dumps(replay(json.loads(Path(args.recording).read_text()), args.db), indent=2))
