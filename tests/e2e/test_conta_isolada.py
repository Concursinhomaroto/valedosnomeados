import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, INIT_JS, BASE, LOCAL_PHASER, make_seed

def conta(email,nome,xp,lm,reinos,fcs=None):
    return make_seed({'studyNickname':nome,'accountEmail':email,'plan':'full',
      'onboardingCompleted':True,'xp':xp,'lastModified':lm,
      'kingdoms':[{'id':'k'+r,'name':r,'icon':'💊'} for r in reinos],
      'topics':{},'flashcards':fcs or {}})

A=conta('A@ex.com','Leo',31998,1_800_000_000_000,['REINO A'],
        {'fcA':{'id':'fcA','mbId':'x','pergunta':'card A','resposta':'r','acertos':1,'erros':0,'dificuldade':2}})
B=conta('B@ex.com','Bia',7777,1_700_000_000_000,['REINO B1','REINO B2'],
        {'fcB':{'id':'fcB','mbId':'x','pergunta':'card B','resposta':'r','acertos':9,'erros':1,'dificuldade':2}})

async def roda(p, uid, email, root_users, ls_pairs):
    init=INIT_JS.replace('TEST_UID_LEO',uid).replace('__SEED__',json.dumps({}))
    init=init.replace("email: 'leonardobrunotlc@gmail.com',", "email: '%s',"%email)
    init=init.replace("window.__root = { users: { %s: { vdn_v1: {} } } };"%uid,
                      "window.__root = { users: %s };"%json.dumps(root_users))
    pre=''.join("try{localStorage.setItem(%s,JSON.stringify(%s));}catch(e){}\n"%(json.dumps(k),json.dumps(v))
                for k,v in ls_pairs)
    browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    ctx=await browser.new_context(service_workers='block',viewport={'width':1200,'height':900})
    page=await ctx.new_page()
    await page.route('**cdnjs.cloudflare.com/ajax/libs/phaser/**', lambda r: asyncio.ensure_future(r.fulfill(path=LOCAL_PHASER)))
    for pat in ['**://www.gstatic.com/**','**://fonts.googleapis.com/**','**://cdn.jsdelivr.net/**','**://www.googletagmanager.com/**']:
        await page.route(pat, lambda r: asyncio.ensure_future(r.abort()))
    await page.add_init_script(pre+init)
    await page.goto(BASE); await page.wait_for_timeout(2200)
    r=await page.evaluate("""async(uid)=>({
        reinos:(db.kingdoms||[]).map(k=>k.name), fcs:Object.keys(db.flashcards||{}),
        apelido:db.studyNickname||null, plano:db.plan, trial:db.trialStartedAt||null,
        onboarding:db.onboardingCompleted,
        fbReinos:(((window.__root.users||{})[uid]||{}).vdn_v1||{}).kingdoms
                  ?((window.__root.users[uid].vdn_v1.kingdoms)||[]).map(k=>k.name):null,
        chaveUid:!!(await idbLer('vdn_local_v1_'+uid)),
        chaveAntiga:!!localStorage.getItem('vdn_local_v1')||!!(await idbLer('vdn_local_v1')),
        idbDeOutroDono:!!(await idbLer('vdn_local_v1_UID_NOVO')),
        carimboVazouProDb:('_uid' in db)
      })""", uid)
    await browser.close()
    return r

async def main():
    async with async_playwright() as p:
        print('=== 1) conta NOVA num navegador onde outra conta já usou ===')
        r=await roda(p,'UID_NOVO','novo@ex.com',{},[('vdn_local_v1',A)])
        print('   reinos:',r['reinos'][:2],'| fcs:',r['fcs'],'| apelido:',r['apelido'])
        print('   plano:',r['plano'],'| trial:',r['trial'],'| onboarding:',r['onboarding'])
        assert 'REINO A' not in r['reinos'], 'vazou dado da outra conta'
        assert r['fcs']==[] and r['apelido'] is None
        assert r['plano']=='trial' and r['trial'], 'conta nova tem que entrar no trial, nao herdar o plano pago'
        assert r['onboarding'] is False, 'conta nova tem que ver o onboarding'
        assert r['fbReinos'] is None, 'nao pode gravar nada na conta nova'
        print('   OK — nao herda dado, nao herda plano pago, ve o onboarding')

        print('\n=== 2) conta EXISTENTE logando depois de outra conta (perda de dados) ===')
        r=await roda(p,'UID_B','B@ex.com',{'UID_B':{'vdn_v1':B}},[('vdn_local_v1',A)])
        print('   reinos:',r['reinos'],'| fcs:',r['fcs'],'| apelido:',r['apelido'])
        print('   no Firebase depois:',r['fbReinos'])
        assert r['reinos']==['REINO B1','REINO B2'], r['reinos']
        assert r['fcs']==['fcB'] and r['apelido']=='Bia'
        assert r['fbReinos']==['REINO B1','REINO B2'], 'a conta B foi sobrescrita no servidor'
        print('   OK — a conta B mantem o proprio historico, no app e no servidor')

        print('\n=== 3) MESMA conta, cache antigo mais novo que o servidor (estudo offline) ===')
        Bnovo=json.loads(json.dumps(B)); Bnovo['xp']=99999; Bnovo['lastModified']=1_900_000_000_000
        Bnovo['kingdoms']=[{'id':'kOFF','name':'REINO FEITO OFFLINE','icon':'💊'}]
        r=await roda(p,'UID_B','B@ex.com',{'UID_B':{'vdn_v1':B}},[('vdn_local_v1',Bnovo)])
        print('   reinos:',r['reinos'])
        assert r['reinos']==['REINO FEITO OFFLINE'], r['reinos']
        assert r['fbReinos']==['REINO FEITO OFFLINE'], 'o offline devia subir pro servidor'
        print('   OK — o trabalho offline do proprio dono continua sendo recuperado')

        print('\n=== 4) higiene das chaves e do carimbo ===')
        print('   copia no IndexedDB, na chave com uid:',r['chaveUid'],'| chave antiga removida:',not r['chaveAntiga'])
        print('   copia de outro dono no IndexedDB?',r['idbDeOutroDono'])
        assert not r['idbDeOutroDono'], 'nao pode existir copia de outra conta neste IndexedDB'
        print('   carimbo _uid vazou pro db?',r['carimboVazouProDb'])
        assert r['chaveUid'], 'devia gravar no IndexedDB, na chave com uid'
        assert not r['chaveAntiga'], 'a copia antiga do proprio dono devia ser migrada e removida'
        assert not r['carimboVazouProDb'], '_uid nao pode entrar no db (iria pro Firebase)'
        print('   OK')
        print('\nOK')
asyncio.run(main())
