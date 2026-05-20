import pypdf
r = pypdf.PdfReader('data/wi_scrape/aire_serv_id640749.pdf')
ranges = [(2,2),(23,24),(27,29),(39,40),(81,91)]
out = []
for a,b in ranges:
    for p in range(a, b+1):
        out.append(f'===PAGE {p}===')
        try:
            out.append(r.pages[p-1].extract_text())
        except Exception as e:
            out.append(f'ERR {e}')
open('_tmp_aire_serv.txt','w',encoding='utf-8').write('\n'.join(out))
print('done')
