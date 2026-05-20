import pypdf
r = pypdf.PdfReader('data/wi_scrape/certapro_painters_id640884.pdf')
out=[]
for i in [1,14,15,16,46,47,48,49,50,51,52,53,54,55,56,57]:
    out.append(f'===PAGE {i+1}===')
    try:
        out.append(r.pages[i].extract_text())
    except Exception as e:
        out.append(f'ERR {e}')
open('_tmp_out.txt','w',encoding='utf-8').write('\n'.join(out))
print('done')
