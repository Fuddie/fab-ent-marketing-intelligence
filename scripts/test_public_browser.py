"""Public-origin checks with static assets and no local or CDN services."""
from pathlib import Path
import mimetypes
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]/'docs'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page()
    local=[]
    page.on('request',lambda r:local.append(r.url) if '127.0.0.1' in r.url or 'localhost' in r.url else None)
    def asset(route):
        name=route.request.url.split('portfolio.example/',1)[1] or 'index.html'
        path=(ROOT/name).resolve()
        assert path.is_relative_to(ROOT.resolve())
        route.fulfill(body=path.read_bytes(),content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
    page.route('https://portfolio.example/**',asset)
    page.route('https://cdn.jsdelivr.net/**',lambda r:r.abort())
    page.goto('https://portfolio.example/')
    page.wait_for_function("document.querySelector('#ai-connection').textContent.includes('only on localhost')")
    page.get_by_label('Verified examples',exact=True).check()
    for width in [1440,390]:
        page.set_viewport_size({'width':width,'height':950})
        saved=page.locator('#questions > details').first
        if not saved.evaluate('(e)=>e.open'):saved.locator('> summary').click()
        assert saved.locator('.answer-kpi').count()==1
        assert saved.locator('table').count()==0
        assert not saved.locator('.answer-technical').evaluate('(e)=>e.open')
        assert 'Saved verified example' in saved.inner_text()
        other=page.locator('#questions > details').nth(2)
        if not other.evaluate('(e)=>e.open'):other.locator('> summary').click()
        assert other.locator('tbody tr').count()==5
        assert other.locator('.answer-summary').count()==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.get_by_label('Local questions',exact=True).check()
    page.fill('#ai-question','What is total marketing spend?')
    page.click('#ask-submit')
    page.wait_for_function("document.querySelector('#ai-result').textContent.includes('only on localhost')")
    assert not local,local
    browser.close()
print('PASS: public origin; 2 viewports; saved KPI/table; collapsed metadata; no loopback requests; local-only message; CDN unavailable')
