import pypdf
r = pypdf.PdfReader('data/wi_scrape/dryer_vent_wizard_id640751.pdf')
out=[]
for i in [1,22,23,24,25,26,27,28,34,35,70,71,72,73,74,75,76,77,78,79,80,81]:
    out.append(f'===PAGE {i+1}')
    out.append(r.pages[i].extract_text())
open('_pages.txt','w',encoding='utf-8').write('\n'.join(out))
print('done',len(out))
