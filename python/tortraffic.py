import requests
import datetime
import csv
import sys
import io


def main(argv):
    try:
        start = argv[1]
    except IndexError:
        start = '2010-01-01'
    today = datetime.date.today().isoformat()
    resp = requests.get(f'https://metrics.torproject.org/bandwidth.csv?start={start}&end={today}')
    resp.raise_for_status()
    csvlines = [l for l in resp.text.split('\n') if l and l[0] != '#']
    csvbuf = io.StringIO('\n'.join(csvlines))
    total = 0
    for line in csv.DictReader(csvbuf):
        try:
            total += float(line['bwhist'])*60*60*24  # Gbit/s to Gbit/d
        except ValueError:
            pass
    # Convert Gbits to Gbytes
    total /= 8
    for s in ('G', 'T', 'P', 'E'):
        if total < 1024:
            print(f'{total:0.2f}{s}B')
            break
        total /= 1024


if __name__ == '__main__':
    main(sys.argv)
