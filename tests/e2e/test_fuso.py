import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, INIT_JS, BASE, LOCAL_PHASER, make_seed
import json
async def roda(p,tz,hora):
    init=INIT_JS.replace('__SEED__',json.dumps(make_seed({'studyNickname':'Leo'})))
    b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx=await b.new_context(service_workers='block',viewport={'width':1200,'height':900},
                            timezone_id=tz)
    page=await ctx.new_page()
    await page.route('**cdnjs.cloudflare.com/ajax/libs/phaser/**', lambda r: asyncio.ensure_future(r.fulfill(path=LOCAL_PHASER)))
    for pat in ['**://www.gstatic.com/**','**://fonts.googleapis.com/**','**://cdn.jsdelivr.net/**','**://www.googletagmanager.com/**']:
        await page.route(pat, lambda r: asyncio.ensure_future(r.abort()))
    await page.add_init_script("Date.now=(o=>()=>%d)();"%hora + init)
    await page.goto(BASE); await page.wait_for_timeout(1800)
    r=await page.evaluate("""()=>{
      const t=new Date(); t.setHours(0,0,0,0);
      return {agoraLocal:new Date().toString().slice(0,24),
              todayStr:todayStr(), grafico:t.toISOString().slice(0,10)};}""")
    await b.close(); return r
async def main():
    async with async_playwright() as p:
        # 2026-09-08 02:21 UTC  ==  2026-09-07 23:21 em Brasilia
        ms=1789266060000
        for tz in ['America/Sao_Paulo','Europe/Lisbon','Asia/Tokyo']:
            r=await roda(p,tz,ms)
            ok='IGUAIS' if r['todayStr']==r['grafico'] else '>>> DIVERGEM <<<'
            print('%-20s local=%s | todayStr()=%s | data dos gráficos=%s  %s'%(
                tz, r['agoraLocal'][:21], r['todayStr'], r['grafico'], ok))
asyncio.run(main())
