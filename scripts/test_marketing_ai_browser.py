"""Ask UI desktop/mobile tests with deterministic service responses and offline mode."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('http://127.0.0.1:4174/**',lambda r:r.abort())
        page.goto('http://127.0.0.1:4173/')
        page.wait_for_selector('#questions > details',state='attached')
        page.wait_for_function("document.querySelector('#ai-connection').textContent.includes('unavailable')")
        page.get_by_label('Verified examples',exact=True).check()
        assert page.locator('#verified').is_visible()
        assert page.locator('#questions > details').count()==len(json.loads((Path(__file__).resolve().parents[1]/'docs/verified.json').read_text()))
        page.fill('#question-search','total marketing spend')
        assert page.locator('#questions > details:visible').count()==1
        page.fill('#question-search','')
        page.get_by_label('Local questions',exact=True).check()
        page.locator('#suggestions button').first.click()
        assert 'highest net revenue' in page.input_value('#ai-question')
        assert page.locator('#ai-question').get_attribute('maxlength')=='500'
        assert not page.locator('#use-filters').is_checked()
        page.fill('#ai-question','What is total marketing spend?')
        page.click('#ask-submit')
        page.wait_for_function("document.querySelector('#ai-result').textContent.includes('unavailable')")
        page.unroute('http://127.0.0.1:4174/**')
        result={'answer':'<img src=x onerror="window.injected=true">','rows':[{'metric':None}],
                'cached':False,'model':'MarketingMonthlyOverview','codex_model':'mock','reasoning':'low',
                'duration_ms':42,'filters':None,'validation':'PASS','assumptions':['Fixed snapshot'],
                'ordering':'metric','semantic_sql':'SELECT <unsafe>'}
        page.route('**/ask',lambda r:r.fulfill(status=200,content_type='application/json',
            headers={'Access-Control-Allow-Origin':'http://127.0.0.1:4173'},body=json.dumps(result)))
        page.click('#ask-submit')
        page.wait_for_selector('#ai-result .answer-kpi')
        assert page.locator('#ai-result table').count()==0
        assert page.locator('.answer-verified').inner_text()=='\u2713 Verified by Wren'
        assert not page.locator('.answer-technical').evaluate('(e)=>e.open')
        assert page.locator('#ai-result img').count()==0
        assert not page.evaluate('window.injected || false')
        assert 'N/A' in page.locator('#ai-result').inner_text()
        page.locator('.answer-technical summary').click()
        assert 'Complete snapshot' in page.locator('#ai-result').inner_text()
        # Explicit opt-in sends the current filters; default sent null above.
        sent=[]
        page.unroute('**/ask')
        def capture(route):
            sent.append(route.request.post_data_json)
            scoped=dict(result,filters=sent[-1]['filters'])
            route.fulfill(status=200,content_type='application/json',
                headers={'Access-Control-Allow-Origin':'http://127.0.0.1:4173'},body=json.dumps(scoped))
        page.route('**/ask',capture)
        selected={'start':'2025-03','end':'2025-05','channel':'Meta Paid Social','campaign':'CAM-0001'}
        page.evaluate('(filters)=>{window.dashboardState={ready:true,filters}}',selected)
        page.check('#use-filters');page.click('#ask-submit')
        page.wait_for_function("document.querySelector('#ai-result').textContent.includes('2025-03')")
        page.locator('.answer-technical summary').click()
        assert sent[-1]['filters']==selected
        # Business output: units, readable labels, metadata disclosure and screenshots.
        page.unroute('**/ask')
        shots=Path(__file__).resolve().parents[1]/'docs/assets/screenshots'
        shots.mkdir(parents=True,exist_ok=True)
        def show(rows,columns=None):
            page.unroute('**/ask')
            payload=dict(result,rows=rows,columns=columns or [])
            page.route('**/ask',lambda r:r.fulfill(status=200,content_type='application/json',
                headers={'Access-Control-Allow-Origin':'http://127.0.0.1:4173'},body=json.dumps(payload)))
            page.click('#ask-submit')
            page.wait_for_function("document.querySelector('#ai-result').getAttribute('aria-busy')==='false'")
        for key,value,expected in [('total_spend_gbp','1234567.8','\u00a31,234,567.80'),
                ('attribution_pct',42.5,'42.50%'),('net_roas',3.25,'3.25x'),
                ('eligible_conversions',12345,'12,345'),('reporting_month','2025-03-01','Mar 2025'),
                ('total_spend_gbp',0,'\u00a30.00')]:
            show([{key:value}])
            assert page.locator('.answer-value').inner_text()==expected
            assert page.locator('#ai-result table').count()==0
            assert not page.locator('.answer-technical').evaluate('(e)=>e.open')
        show([{'total':1234567.8}],[{'key':'total','unit':'currency'}])
        assert page.locator('.answer-value').inner_text()=='\u00a31,234,567.80'
        show([{'total_marketing_spend_gbp':1234567.8}])
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000})
            page.locator('#ai-result').screenshot(path=str(shots/f'ask-kpi-{width}.png'))
        show([{'marketing_channel':'Meta Paid Social','net_revenue_gbp':'123456.78','net_roas':3.2},
              {'marketing_channel':'Google Paid Search','net_revenue_gbp':None,'net_roas':0}])
        assert page.locator('.answer-summary').is_visible()
        assert page.locator('#ai-result th').all_text_contents()==['Marketing channel','Net revenue GBP','Net ROAS']
        assert '\u00a3123,456.78' in page.locator('#ai-result tbody').inner_text()
        assert 'N/A' in page.locator('#ai-result tbody').inner_text()
        for width in [1440,390,320]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            if width!=320:page.locator('#ai-result').screenshot(path=str(shots/f'ask-table-{width}.png'))
        page.locator('.answer-technical summary').click()
        assert 'SELECT <unsafe>' in page.locator('.answer-technical').inner_text()
        assert page.locator('#ai-result img').count()==0
        page.unroute('**/ask')
        show([{'campaign_name':'<img src=x onerror="window.injected=true">','spend_gbp':12},
              {'campaign_name':'Safe','spend_gbp':0}])
        assert page.locator('#ai-result img').count()==0
        assert not page.evaluate('window.injected || false')
        page.unroute('**/ask')
        for code,message in [(400,'Invalid marketing question.'),(504,'The 90-second limit was reached.'),(500,'Execution failed.')]:
            def fail(route):
                route.fulfill(status=code,content_type='application/json',
                    headers={'Access-Control-Allow-Origin':'http://127.0.0.1:4173'},body=json.dumps({'error':message}))
            page.route('**/ask',fail)
            page.click('#ask-submit')
            page.wait_for_function('(m)=>document.querySelector("#ai-result").textContent.includes(m)',arg=message)
            page.unroute('**/ask')
        page.route('**/ask',lambda r:r.fulfill(status=200,content_type='application/json',
            headers={'Access-Control-Allow-Origin':'http://127.0.0.1:4173'},body=json.dumps(dict(result,rows=[]))))
        page.click('#ask-submit')
        page.wait_for_function("document.querySelector('#ai-result').textContent.includes('No matching data')")
        for width in [1440,390,320]:
            page.set_viewport_size({'width':width,'height':900})
            page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,page.evaluate("({w:document.documentElement.scrollWidth,els:[...document.querySelectorAll('*')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>({tag:e.tagName,id:e.id,scroll:e.scrollWidth,client:e.clientWidth,overflow:getComputedStyle(e).overflow}))})"),page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && !e.closest('svg') && getComputedStyle(e).position!=='absolute').map(e=>({tag:e.tagName,id:e.id,right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})).slice(-15)"))
        assert not errors,errors
        browser.close()
    print('PASS: Ask UI modes, offline saved answers, search, suggestions, limits, filters, escaped results, NULLs, empty/error/timeout states and desktop/mobile layout')

if __name__=='__main__':main()
