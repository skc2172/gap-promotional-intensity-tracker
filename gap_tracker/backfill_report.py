"""Offline HTML audit and readable backfill inventory from preserved evidence."""
import hashlib
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from gap_tracker.backfill import ROOT, read_index
from gap_tracker.categories import CATEGORIES


def audit_html():
    output=[]
    for key in CATEGORIES:
        path=ROOT/key/'html-selection.json'
        if not path.exists():
            output.append({'category_key':key,'status':'html_inspection_not_completed'})
            continue
        for a in json.loads(path.read_text()):
            item={'category_key':key,'timestamp':a['candidate']['timestamp'],
                  'raw_file':a['raw_file'],'archive_url':a['archive_url']}
            if not a['actual_archive_timestamp']:
                item['status']='replay_unavailable_or_timestamp_unverified'
            else:
                body=Path(a['raw_file']).read_bytes()
                if hashlib.sha256(body).hexdigest()!=a['sha256']:
                    raise ValueError('HTML evidence hash mismatch')
                soup=BeautifulSoup(body,'html.parser')
                text=soup.get_text(' ',strip=True)
                links=soup.select('a[href*="pid="]')
                prices=re.findall(r'\$\s*\d+(?:\.\d{2})?',text)
                item.update(title=soup.title.get_text() if soup.title else None,
                            product_links=len(links), visible_price_tokens=len(prices))
                item['status']=('unsupported_html_product_color_price_mapping' if links else
                                'no_supported_product_price_records')
                item['reason']='No validated per-color reference/current price mapping in this HTML adapter; navigation, style price ranges and promotional messages are not observations.'
            output.append(item)
    folder=Path('data/processed/backfill');folder.mkdir(parents=True,exist_ok=True)
    (folder/'html-audit.json').write_text(json.dumps(output,indent=2)+'\n')
    return output


if __name__=='__main__':
    print('HTML captures audited:',len(audit_html()))
