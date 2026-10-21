"""Check the saved Wren monthly answer and its desktop/mobile presentation."""
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    subprocess.run(['node','scripts/monthly_preview.mjs'],cwd=ROOT,check=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page()
        page.goto('http://127.0.0.1:4173/')
        page.get_by_label('Verified examples',exact=True).check()
        monthly=page.locator('#questions > details').filter(has_text='Top three campaigns based on revenue generation per month')
        monthly.locator('> summary').click()
        assert monthly.locator('tbody tr').count()==36
        page.set_content((ROOT/'target/campaign-monthly/preview.html').read_text(encoding='utf-8'))
        assert page.locator('th').all_text_contents()==['Reporting month','Campaign ID','Campaign name','Attributed net revenue GBP','Monthly rank']
        assert page.locator('tbody tr').count()==36
        assert 'Reporting date' not in page.inner_text('main')
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(ROOT/f'docs/assets/screenshots/ask-campaign-monthly-{width}.png'),full_page=True)
        browser.close()
    print('PASS: monthly headers, 36 rows, desktop/mobile screenshots, no page overflow')
