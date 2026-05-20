import pypdf
r = pypdf.PdfReader('data/wi_scrape/advantaclean_id640768.pdf')
ranges = [(1,1),(14,21),(49,56)]
out = []
for a,b in ranges:
    for p in range(a, b+1):
        out.append(f'===PAGE {p}===')
        try:
            out.append(r.pages[p-1].extract_text())
        except Exception as e:
            out.append(f'ERR {e}')
open('_tmp_ac.txt','w',encoding='utf-8').write('\n'.join(out))
print('OK')
