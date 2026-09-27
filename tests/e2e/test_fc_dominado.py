import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={}
def card(i,mb,tipo):
    c={'id':'c%d'%i,'mbId':mb,'pergunta':'P%d'%i,'resposta':'R%d'%i,'tags':'',
       'dificuldade':2,'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
    if tipo=='due': c.update({'acertos':1,'ultimaRevisao':'2026-01-02T10:00:00Z','sm2':{'ef':2.5,'reps':1,'interval':1}})
    if tipo=='ok':  c.update({'acertos':3,'ultimaRevisao':'2026-09-11T10:00:00Z','sm2':{'ef':2.6,'reps':3,'interval':60}})
    return c
i=0
for mb,n,d,o in [('t1',2,2,1),('t2',2,1,1)]:
    for _ in range(n): i+=1; FC['c%d'%i]=card(i,mb,'new')
    for _ in range(d): i+=1; FC['c%d'%i]=card(i,mb,'due')
    for _ in range(o): i+=1; FC['c%d'%i]=card(i,mb,'ok')
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Saúde Mental','subtopics':[]},{'id':'t2','name':'SUS','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{showScreen('flashcards');fcSelectedMb=null;fcInit();renderFCMbList();renderFCMain();}")
        await page.wait_for_timeout(400)

        est=lambda: page.evaluate("""()=>{const all=getAllFCEverywhere();
            const g=t=>all.filter(c=>fcStatus(c)===t).map(c=>c.id);
            return {novo:g('new'),due:g('due'),dom:g('dominado'),
                    emDia:all.filter(c=>!['due','new','dominado'].includes(fcStatus(c))).map(c=>c.id),
                    fila:(fcStudyCards||[]).map(c=>c.id)};}""")

        print('--- antes'); print('   ',await est())

        # domina um card que estava VENCIDO, no meio de uma sessao
        await page.evaluate("()=>fcOverviewClick('due')")
        await page.wait_for_timeout(300)
        antes=await est()
        alvo=antes['fila'][0]
        await page.evaluate("(id)=>fcStudyDominar(id)",alvo)
        await page.wait_for_timeout(400)
        dep=await est()
        print('\n--- dominou %s (estava vencido), no meio da sessão'%alvo)
        print('    saiu da fila desta sessão: %s'%(alvo not in dep['fila']))
        print('    virou dominado           : %s'%(alvo in dep['dom']))
        print('    ainda conta como vencido : %s  (tem que ser False)'%(alvo in dep['due']))
        print('    conta como "em dia"      : %s  (tem que ser False)'%(alvo in dep['emDia']))

        # nao volta em nenhuma fila normal
        for tipo in ['due','new','ok']:
            await page.evaluate("(t)=>{fcVoltar();return fcOverviewClick(t);}",tipo)
            await page.wait_for_timeout(250)
            f=await page.evaluate("()=>(fcStudyCards||[]).map(c=>c.id)")
            print('    fila "%s" contém o dominado? %s'%(tipo,alvo in f))
        await page.evaluate("()=>{fcVoltar();return fcStudyAllKingdoms();}")
        await page.wait_for_timeout(250)
        f=await page.evaluate("()=>(fcStudyCards||[]).map(c=>c.id)")
        print('    "Estudar tudo" contém o dominado? %s  (tem que ser False)'%(alvo in f))

        # ver os dominados
        await page.evaluate("()=>{fcVoltar();return fcEstudarDominados();}")
        await page.wait_for_timeout(300)
        r=await page.evaluate("()=>({t:(document.querySelector('.fc-title')||{}).textContent,fila:(fcStudyCards||[]).map(c=>c.id)})")
        print('\n--- "Dominados": título=%r fila=%s'%(r['t'].strip(),r['fila']))

        # devolver preserva o historico
        hist=await page.evaluate("(id)=>({ac:db.flashcards[id].acertos,sm2:db.flashcards[id].sm2})",alvo)
        await page.evaluate("(id)=>fcDestravarDominado(id)",alvo)
        await page.wait_for_timeout(300)
        dep2=await est()
        hist2=await page.evaluate("(id)=>({ac:db.flashcards[id].acertos,sm2:db.flashcards[id].sm2,st:fcStatus(db.flashcards[id])})",alvo)
        print('\n--- devolveu: status=%s  (voltou a vencido, não virou "novo")'%hist2['st'])
        print('    histórico preservado: acertos %s->%s | sm2 %s'%(hist['ac'],hist2['ac'],hist2['sm2']==hist['sm2']))
        print('    dominados agora: %s'%dep2['dom'])
        print('\nerros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
