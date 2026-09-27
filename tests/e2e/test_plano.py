import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def cenario(p, campos, titulo):
    seed=make_seed({'studyNickname':'Leo', **campos})
    b,page,errs=await setup_page(p,seed)
    return b,page,errs

async def main():
    async with async_playwright() as p:
        print('=== 1) teste vencido: o truque do console nao libera mais ===')
        b,page,e=await cenario(p,{'plan':'trial','trialStartedAt':'2020-01-01'},'')
        try:
            antes=await page.evaluate("()=>hasFullAccess()")
            r=await page.evaluate("""()=>{
              db.plan='full'; db.lastPaymentAt='2030-01-01'; db.planType='vitalicio';
              saveDB();
              return {acesso:hasFullAccess(), planoNaMemoria:db.plan};}""")
            await page.wait_for_timeout(2500)
            serv=await page.evaluate("()=>((window.__root.users.TEST_UID_LEO||{}).vdn_v1||{})")
            print('   acesso antes:',antes,'-> depois do truque:',r['acesso'],'(db.plan na memoria:',r['planoNaMemoria']+')')
            print('   o que foi ENVIADO ao servidor -> plan:',repr(serv.get('plan')),
                  '| lastPaymentAt:',repr(serv.get('lastPaymentAt')),'| planType:',repr(serv.get('planType')))
            assert antes is False and r['acesso'] is False, 'o bypass ainda funciona'
            assert serv.get('plan')=='trial', 'o cliente enviou um plano forjado pro servidor'
            assert not serv.get('lastPaymentAt'), 'o cliente enviou lastPaymentAt forjado'
            print('   OK — nao libera na sessao E nao envia nada forjado')
        finally: await b.close()

        print('\n=== 2) quem PAGA continua com acesso ===')
        b,page,e=await cenario(p,{'plan':'trial','trialStartedAt':'2020-01-01',
                                  'lastPaymentAt':'2026-09-01','planType':'mensal'},'')
        try:
            r=await page.evaluate("()=>({acesso:hasFullAccess(),dias:daysOfAccessLeft()})")
            print('   pagou em 01/09, plano mensal ->',r)
            assert r['acesso'] is True, 'assinante perdeu acesso'
            print('   OK')
        finally: await b.close()

        print('\n=== 3) conta LEGADA (sem campo de plano) continua liberada ===')
        b,page,e=await cenario(p,{'xp':500},'')
        try:
            r=await page.evaluate("()=>({acesso:hasFullAccess(),plano:planoAtual().plan})")
            print('   sem plan no servidor ->',r)
            assert r['acesso'] is True, 'conta antiga foi travada'
            print('   OK')
        finally: await b.close()

        print('\n=== 4) vitalicio (plan=full, sem pagamento) ===')
        b,page,e=await cenario(p,{'plan':'full'},'')
        try:
            r=await page.evaluate("()=>hasFullAccess()")
            print('   plan=full ->',r); assert r is True
            print('   OK')
        finally: await b.close()

        print('\n=== 5) trial dentro do prazo continua valendo ===')
        from datetime import date
        hoje=date.today().isoformat()
        b,page,e=await cenario(p,{'plan':'trial','trialStartedAt':hoje},'')
        try:
            r=await page.evaluate("()=>({acesso:hasFullAccess(),trial:isInTrialWindow()})")
            print('   trial comecou hoje ->',r); assert r['acesso'] is True
            print('   OK')
        finally: await b.close()

        print('\n=== 6) admin confirmando pagamento continua funcionando ===')
        b,page,e=await cenario(p,{'plan':'trial','trialStartedAt':'2020-01-01'},'')
        try:
            await page.evaluate("()=>{window.confirm=()=>true;}")
            await page.evaluate("()=>adminConfirmPayment('TEST_UID_LEO','anual')")
            await page.wait_for_timeout(800)
            serv=await page.evaluate("()=>((window.__root.users.TEST_UID_LEO||{}).vdn_v1||{})")
            print('   servidor apos confirmar ->  lastPaymentAt:',repr(serv.get('lastPaymentAt')),
                  '| planType:',repr(serv.get('planType')))
            assert serv.get('planType')=='anual' and serv.get('lastPaymentAt')
            print('   OK')
        finally: await b.close()
        print('\nOK')
asyncio.run(main())
