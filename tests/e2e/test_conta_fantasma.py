import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, INIT_JS, BASE, LOCAL_PHASER, make_seed

async def roda(p, root_users, titulo):
    init=INIT_JS.replace('__SEED__',json.dumps({}))
    init=init.replace("window.__root = { users: { TEST_UID_LEO: { vdn_v1: {} } } };",
                      "window.__root = { users: %s };"%json.dumps(root_users))
    b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx=await b.new_context(service_workers='block',viewport={'width':1200,'height':900})
    page=await ctx.new_page()
    await page.route('**cdnjs.cloudflare.com/ajax/libs/phaser/**', lambda r: asyncio.ensure_future(r.fulfill(path=LOCAL_PHASER)))
    for pat in ['**://www.gstatic.com/**','**://fonts.googleapis.com/**','**://cdn.jsdelivr.net/**','**://www.googletagmanager.com/**']:
        await page.route(pat, lambda r: asyncio.ensure_future(r.abort()))
    await page.add_init_script(init)
    await page.goto(BASE); await page.wait_for_timeout(2500)
    r=await page.evaluate("""()=>({plan:db.plan,trialStartedAt:db.trialStartedAt||null,
        acessoCompleto:hasFullAccess(),noTrial:isInTrialWindow(),
        planoServidor:JSON.stringify(planoAtual())})""")
    print('--- %s'%titulo)
    for k,v in r.items(): print('    %-16s %s'%(k+':',v))
    await b.close()
    return r

async def main():
    async with async_playwright() as p:
        # o caso do print: users/{uid} existe, mas SEM vdn_v1 (so o backupMeta)
        r1=await roda(p,{'TEST_UID_LEO':{'vdn_v1_backupMeta':{'ultima':'2026-09-12'}}},
                      'CONTA FANTASMA: users/uid existe, sem vdn_v1')
        print('    >>> essa pessoa tem acesso pago de graca? %s\n'%
              ('SIM — FURO' if (r1['acessoCompleto'] and not r1['noTrial']) else
               'NAO (esta em trial, como deveria)'))

        # como o painel do admin LE esse mesmo no
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        page=await (await b.new_context()).new_page()
        await page.set_content('<div id=x></div>')
        r=await page.evaluate("""()=>{
            const users={u1:{vdn_v1_backupMeta:{}},                        // fantasma
                         u2:{vdn_v1:{accountEmail:'a@x.com',plan:'trial'}},// trial normal
                         u3:{vdn_v1:{accountEmail:'b@x.com',plan:'full'}}};// vitalicio de verdade
            return Object.entries(users).map(([uid,u])=>{
                const d=(u&&u.vdn_v1)||{};
                return {uid,email:d.accountEmail||'(sem e-mail salvo)',
                        full:d.plan!=='trial', temPagamento:!!d.lastPaymentAt};});}""")
        print('--- COMO O PAINEL LE CADA CASO (logica atual do renderAdminResults)')
        for x in r:
            st='Acesso completo permanente' if (x['full'] and not x['temPagamento']) else 'Trial, sem pagamento ainda'
            print('    %-4s %-22s -> %s'%(x['uid'],x['email'],st))
        await b.close()
asyncio.run(main())
