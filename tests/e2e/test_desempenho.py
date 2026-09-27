import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1';S='s1'
FC={}
for i in range(500):
    FC['fc%d'%i]={'id':'fc%d'%i,'mbId':T,'subId':S,'pergunta':'Pergunta número %d sobre conduta clínica'%i,
      'resposta':'Resposta %d'%i,'tags':'','dificuldade':2,'acertos':0,'erros':0,'lastConf':0,
      'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
FC['achavel']={'id':'achavel','mbId':T,'subId':S,'pergunta':'Sistematização da Assistência de Enfermagem',
  'resposta':'SAE','tags':'','dificuldade':2,'acertos':0,'erros':0,'lastConf':0,
  'criacao':'2026-01-01T10:00:00Z','ultimaRevisao':None}
seed=make_seed({'studyNickname':'Leo','flashcards':FC,'kingdoms':[{'id':K,'name':'Enf','icon':'💉'}],
 'topics':{K:[{'id':T,'name':'Chefão','subtopics':[{'id':S,'name':'A','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            await page.evaluate("()=>{selectFCBoss('t1');showScreen('flashcards');}")
            await page.wait_for_timeout(700)
            r=await page.evaluate("()=>({cards:document.querySelectorAll('.fc-grid-card').length,rodape:!!document.querySelector('.fc-grid-mais')})")
            print('1) primeiro lote ->',r['cards'],'cards na tela | aviso de "mostrar mais":',r['rodape'])
            assert r['cards']==60 and r['rodape']

            await page.evaluate("()=>fcGridMostrarMais()"); await page.wait_for_timeout(400)
            n=await page.evaluate("()=>document.querySelectorAll('.fc-grid-card').length")
            print('2) depois de "Mostrar mais" ->',n,'cards')
            assert n==120

            print('3) a busca continua achando card que está fora do lote')
            await page.evaluate("()=>{document.getElementById('fc-filter-q').value='Sistematiza';fcBuscaDigitou();}")
            await page.wait_for_timeout(600)
            r=await page.evaluate("""()=>{const c=[...document.querySelectorAll('.fc-card-q')].map(e=>e.textContent);
              return {n:c.length, achou:c.some(t=>t.includes('Sistematiza'))};}""")
            print('   resultados:',r['n'],'| achou o card escondido:',r['achou'])
            assert r['achou'], 'a busca nao acha card fora do lote desenhado'
            print('4) buscar reinicia o lote ->', await page.evaluate("()=>fcGridLimite"))
            assert await page.evaluate("()=>fcGridLimite")==60

            print('5) tempo de render com 500 cards')
            ms=await page.evaluate("()=>{document.getElementById('fc-filter-q').value='';const a=performance.now();renderFCMain();return Math.round(performance.now()-a);}")
            print('   renderFCMain:',ms,'ms')
            assert ms<200, f'render ainda lento: {ms}ms'

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
