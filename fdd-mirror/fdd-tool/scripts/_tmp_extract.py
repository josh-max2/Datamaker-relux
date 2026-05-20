import pypdf
r = pypdf.PdfReader('data/wi_scrape/101_mobility_id639220.pdf')
ranges = [(1,6),(11,12),(12,18),(18,20),(43,45),(45,51)]
out = []
for a,b in ranges:
    for p in range(a, b+1):
        out.append(f'===PAGE {p}===')
        try:
            out.append(r.pages[p-1].extract_text())
        except Exception as e:
            out.append(f'ERR {e}')
open('_tmp_pages.txt','w',encoding='utf-8').write('\n'.join(out))
