import sys, json
sys.path.insert(0, 'src')
from pdf_utils import extract_pages, section_text
from pathlib import Path
pages = extract_pages(Path('data/wi_scrape/aaac_wildlife_removal_id639780.pdf'))
ranges = {
    'cover': (1,2),
    'item5': (10,12),
    'item6': (12,19),
    'item7': (19,21),
    'item19': (47,51),
    'item20': (51,55),
}
out = {k: section_text(pages, s, e) for k,(s,e) in ranges.items()}
Path('output/_aaac_text.json').write_text(json.dumps(out), encoding='utf-8')
print('OK', {k:len(v) for k,v in out.items()})
