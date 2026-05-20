import pypdf
r = pypdf.PdfReader('data/wi_scrape/aire_master_id640009.pdf')
ranges = [(1,1),(9,14),(35,41)]
out = []
for a,b in ranges:
    for p in range(a, b+1):
        out.append(f'===PAGE {p}===')
        try:
            out.append(r.pages[p-1].extract_text())
        except Exception as e:
            out.append(f'ERR {e}')
open('_tmp_aire.txt','w',encoding='utf-8').write('\n'.join(out))
