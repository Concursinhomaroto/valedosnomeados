import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={}
def card(i,tipo):
    c={'id':'c%d'%i,'mbId':'t1','pergunta':'P%d'%i,'resposta':'R%d'%i,'tags':'','dificuldade':2,
       'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
    if tipo=='due': c.update({'acertos':1,'ultimaRevisao':'2026-01-02T10:00:00Z','sm2':{'ef':2.5,'reps':1,'interval':1}})
    if tipo=='ok':  c.update({'acertos':3,'ultimaRevisao':'2026-09-11T10:00:00Z','sm2':{'ef':2.6,'reps':3,'interval':60}})
    return c
i=0
for tipo,q in [('new',9),('due',5),('ok',3)]:
    for _ in range(q): i+=1; FC['c%d'%i]=card(i,tipo)
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Enfermagem','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{showScreen('flashcards');selectFCBoss('t1');}""")
        await page.wait_for_timeout(400)
        est=lambda: page.evaluate("()=>({filtro:fcStudyFilter,n:fcStudyCards.length,"
            "status:[...new Set(fcStudyCards.map(c=>fcStatus(c)))].sort()})")
        print('17 cards no baralho: 9 novos, 5 vencidos, 3 em dia\n')
        for tipo,esperado in [('all',17),('new',9),('due',5),('ok',3),('new',9)]:
            await page.evaluate("(t)=>fcBossStudy(t)",tipo)
            await page.wait_for_timeout(300)
            e=await est()
            ok='OK' if e['n']==esperado else '<<< ERRADO'
            print('   clicou "%-4s" -> fila com %2d cards (esperado %2d) status=%-22s %s'%(
                  tipo,e['n'],esperado,','.join(e['status']),ok))
        print('\nerros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
