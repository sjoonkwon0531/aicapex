"""Copy the refresh pipeline's out/*.csv into public/capex/data/ under the page's dataset ids.
Usage: python3 tools/capex/prepare_data.py <pipeline out/ folder>
The page shows seven companies (the four hyperscalers, Oracle, Apple as control, Nvidia as supplier);
the pipeline also emits a wider control group, which is dropped here."""
import csv, os, sys

SRC = sys.argv[1]
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'capex', 'data')
KEEP = {'MSFT', 'GOOGL', 'AMZN', 'META', 'ORCL', 'AAPL', 'NVDA'}
MAP = {  # dataset id -> (pipeline file, filter by ticker?)
    'quarterly': ('quarterly_panel.csv', True),
    'era': ('era_by_company.csv', True),
    'periods': ('core4_periods.csv', False),
    'leases': ('lease_capex_annual.csv', True),
    'commit': ('lease_commitments_q.csv', False),
    'nonlease': ('nonlease_commitments_q.csv', False),
    'snapshot': ('commitments_snapshot.csv', False),
    'kr_mem': ('kr_memory_exports_q.csv', False),
    'amzn_seg': ('amzn_segment_capex.csv', False),   # hand-maintained; copied only if present
}
os.makedirs(DST, exist_ok=True)
for ds, (fn, filt) in MAP.items():
    src = os.path.join(SRC, fn)
    if not os.path.exists(src):
        print('missing', fn, '(kept previous', ds + '.csv)'); continue
    with open(src, newline='', encoding='utf-8') as f:
        r = csv.reader(f); head = next(r); rows = list(r)
    if filt:
        i = head.index('ticker'); rows = [x for x in rows if x[i] in KEEP]
    with open(os.path.join(DST, ds + '.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(head); w.writerows(rows)
    print(ds, len(rows), 'rows')
