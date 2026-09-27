import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
FC={}
def card(i,tipo):
    c={'id':'c%d'%i,'mbId':'t1','pergunta':'P%d'%i,'resposta':'R%d'%i,'tags':'','dificuldade':2,
       'acertos':0,'erros':0,'lastConf':0,'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
    if tipo=='due': c.update({'acertos':1,'ultimaRevisao':'2026-01-02T10:00:00Z','sm2':{'ef':2.5,'reps':1,'interval':1}})
    if tipo=='ok':  c.update({'acertos':3,'ultimaRevisao':'2026-09-11T10:00:00Z','sm2':{'ef':2.6,'reps':3,'interval':60}})
    if tipo=='dom': c.update({'acertos':5,'ultimaRevisao':'2026-09-11T10:00:00Z','dominado':True,
                              'sm2':{'ef':2.8,'reps':5,'interval':90}})
    return c
i=0
for tipo,qtd in [('new',7),('due',5),('ok',3),('dom',4)]:
    for _ in range(qtd): i+=1; FC['c%d'%i]=card(i,tipo)
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'flashcards':FC,
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
  'topics':{'k1':[{'id':'t1','name':'Centro Cirúrgico','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{showScreen('flashcards');fcSelectedMb=null;fcInit();renderFCMbList();renderFCMain();renderFCSidebarSummary();}")
        await page.wait_for_timeout(500)
        r=await page.evaluate("""()=>{
            const el=document.getElementById('fc-sidebar-summary');
            return [...el.querySelectorAll('.fc-sidebar-stat-row')].map(x=>({
                rotulo:(x.childNodes[1]&&x.childNodes[1].textContent||'').trim(),
                n:parseInt((x.querySelector('b')||{}).textContent||'0',10),
                clicavel:x.classList.contains('fc-stat-click')}));}""")
        print('--- Resumo Geral (7 novos, 5 vencidos, 3 em dia, 4 dominados = 19)')
        for x in r: print('    %-16s %3d   clicável: %s'%(x['rotulo'],x['n'],x['clicavel']))
        soma=sum(x['n'] for x in r)
        print('    soma das linhas: %d   (tem que ser 19, sem contar duas vezes)'%soma)

        cl=await page.evaluate("""()=>{
            const el=document.getElementById('fc-sidebar-summary');
            const lin=[...el.querySelectorAll('.fc-sidebar-stat-row')].find(x=>x.textContent.includes('Dominados'));
            lin.click(); return {titulo:(document.querySelector('.fc-title')||{}).textContent||'',
                                 fila:(fcStudyCards||[]).map(c=>c.id).length,
                                 sodominados:(fcStudyCards||[]).every(c=>fcStatus(c)==='dominado')};}""")
        await page.wait_for_timeout(400)
        print('\n--- clicou em "Dominados": %s'%cl)
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
