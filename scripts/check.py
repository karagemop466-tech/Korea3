from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

class Check(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.rows=[]; self.row=None; self.in_body=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='tbody': self.in_body=True
        if tag=='tr' and self.in_body: self.row=[]
        if tag=='a':
            link=attrs.get('href',''); self.links.append(link)
            if self.row is not None: self.row.append(link)
    def handle_endtag(self,tag):
        if tag=='tr' and self.row is not None: self.rows.append(self.row); self.row=None
        if tag=='tbody': self.in_body=False

files=list(Path('.').glob('*.html'))
assert len(files)==7
for path in files:
    parser=Check(); parser.feed(path.read_text())
    assert parser.rows, path
    for row in parser.rows:
        assert any(urlparse(x).scheme=='https' and urlparse(x).netloc for x in row), (path,row)
    for link in parser.links:
        parsed=urlparse(link)
        if not parsed.scheme and not link.startswith('#'): assert Path(parsed.path).is_file(), (path,link)
assert Path('style.css').is_file()
print('OK: seven pages, local links, and a HTTPS source on every table row')
