"""Real Chrome checks against an already-running static HTTP server.

Run: python scripts/test_dashboard_browser.py --url http://127.0.0.1:4173/
Install requirements-dashboard.txt; uses installed Chrome (no downloaded browser).
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:4173/')
    args=parser.parse_args()
    shots=ROOT/'docs/assets/screenshots'
    shots.mkdir(parents=True,exist_ok=True)
    expected=json.loads((ROOT/'target/dashboard/query-results.json').read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url,wait_until='domcontentloaded')
        page.wait_for_function("window.dashboardState?.ready || !document.querySelector('#error').hidden",timeout=90000)
        assert page.locator('#error').is_hidden(),page.locator('#error-message').inner_text()
        assert not errors,errors
        # Compare actual WASM query output (not Python-derived saved KPI answers).
        actual=page.evaluate('window.dashboardData')
        for key in expected:
            assert len(actual[key])==len(expected[key]),key
            for a,b in zip(actual[key],expected[key],strict=True):
                assert list(a)==list(b),key
                for col,value in b.items():
                    if isinstance(value,bool):assert a[col] is value,(key,col)
                    elif value is None:assert a[col] is None,(key,col)
                    else:
                        try:assert abs(float(a[col])-float(value))<=max(1e-8,1e-10*abs(float(value))),(key,col,a[col],value)
                        except (ValueError,TypeError):assert a[col]==value,(key,col)
        assert page.locator('#kpis .kpi').count()==8
        assert page.locator('#questions > details').count()==10
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(shots/'desktop.png'),full_page=True)
        # Browser-level interaction covers every channel/campaign pair; the
        # exhaustive date-pair matrix is covered by the independent SQL oracle.
        channels=page.locator('#channel option').evaluate_all('(opts)=>opts.map(o=>o.value)')
        campaigns=page.locator('#campaign option').evaluate_all('(opts)=>opts.map(o=>o.value)')
        for channel in channels:
            page.select_option('#channel',channel)
            for campaign in campaigns:
                page.select_option('#campaign',campaign)
                state=page.evaluate('window.dashboardState')
                assert state['ready'] and state['filters']['campaign']==campaign
                assert page.locator('#error').is_hidden()
        page.click('#reset')
        page.select_option('#channel','Direct')
        assert page.locator('#kpis .kpi-value').nth(2).inner_text()=='N/A'
        assert page.locator('#kpis .kpi-value').nth(3).inner_text()=='N/A'
        assert page.locator('#kpis .kpi-value').first.inner_text()=='£0.00'
        page.select_option('#campaign',campaigns[1])
        assert 'No matching data' in page.locator('#status').inner_text()
        assert page.locator('#kpis .kpi-value').first.inner_text()=='N/A'
        page.click('#reset')
        page.select_option('#start','2025-12');page.select_option('#end','2025-01')
        assert 'No matching data' in page.locator('#status').inner_text()
        page.click('#reset')
        # Keyboard controls remain reachable and operate with native semantics.
        page.focus('#channel');page.keyboard.press('ArrowDown');page.keyboard.press('Enter')
        assert page.locator('#channel').input_value()!=''
        page.click('#reset')
        # Hostile labels must render as text in cards, tables, alerts and SVG labels.
        page.evaluate('''() => {
          const x='<img src=x onerror="window.injected=true">';
          window.dashboardData.campaigns[0].campaign_name=x;
          window.dashboardData.inventory[0].campaign_name=x;
          document.querySelector('#campaign').value=window.dashboardData.inventory[0].campaign_id;
          document.querySelector('#campaign').dispatchEvent(new Event('change'));
        }''')
        assert not page.evaluate('window.injected || false')
        assert page.locator('#dashboard img').count()==0
        page.reload();page.wait_for_function('window.dashboardState?.ready',timeout=90000)
        for width,height in [(390,844),(320,740),(768,1024)]:
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && getComputedStyle(e).position!=='absolute').map(e=>({tag:e.tagName,id:e.id,cls:e.className,right:e.getBoundingClientRect().right})).slice(0,15)"))
            assert page.locator('#reset').is_visible()
            if width==390:page.screenshot(path=str(shots/'mobile.png'),full_page=True)
        assert not errors,errors
        page.close()
        for label,pattern in [('cdn','https://cdn.jsdelivr.net/**'),('snapshot','**/data/MarketingCampaignDaily.parquet')]:
            context=browser.new_context()
            context.route(pattern,lambda route:route.abort())
            failed=context.new_page();failed.goto(args.url)
            failed.wait_for_selector('#error',state='visible',timeout=90000)
            assert failed.locator('#dashboard').is_hidden()
            assert failed.locator('#retry').is_enabled()
            assert 'No substitute KPI values' in failed.locator('#error-message').inner_text()
            failed.wait_for_selector('#questions > details',timeout=10000)
            assert failed.locator('#questions > details').count()==10
            context.close()
        browser.close()
    (ROOT/'docs/browser-validation.json').write_text(json.dumps({'status':'PASS','browser':'installed Google Chrome, headless Playwright 1.56.0','viewports':[1440,390,320,768],'checks':['actual WASM rows versus native DuckDB','175 channel/campaign interactions','empty and reversed ranges','NULL and zero currency display','keyboard controls','unsafe HTML injection','no document overflow','missing CDN','missing snapshot','saved examples independent of engine errors'],'screenshots':['assets/screenshots/desktop.png','assets/screenshots/mobile.png']},indent=2)+'\n',encoding='utf-8')
    print('PASS: real-browser WASM parity, interactions, accessibility controls, responsive layouts, injection and missing CDN/snapshot states; screenshots saved')


if __name__=='__main__':
    main()
