import pypdf
r = pypdf.PdfReader('data/wi_scrape/alair_homes_master_id640085.pdf')
pages = [1,19,20,21,22,23,24,25,26,27,28,52,53,54,55,56]
out = []
for p in pages:
    out.append(f'===PAGE {p}===')
    try:
        out.append(r.pages[p-1].extract_text())
    except Exception as e:
        out.append(f'ERR {e}')
open('_tmp_alair.txt','w',encoding='utf-8').write('\n'.join(out))
