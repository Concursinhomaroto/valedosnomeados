import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

# O caso do print: tres causas convergindo no mesmo "Desenrolar dos Conflitos",
# que por sua vez leva a uma subarvore longa.
CONVERGE={
 'raizId':'n1',
 'nos':{
  'n1':{'texto':'Revolta da Vacina','tipo':'inicio','ramos':[
        {'rotulo':'Sanitária','to':'c1'},{'rotulo':'Urbana','to':'c2'},{'rotulo':'Política','to':'c3'}]},
  'c1':{'texto':'Campanha invasiva da vacina','tipo':'acao','ramos':[{'to':'d1'}]},
  'c2':{'texto':'Reforma urbana de Pereira Passos','tipo':'acao','ramos':[{'to':'d1'}]},
  'c3':{'texto':'Oposição positivista','tipo':'acao','ramos':[{'to':'d1'}]},
  'd1':{'texto':'Desenrolar dos Conflitos','tipo':'decisao','ramos':[
        {'rotulo':'Popular','to':'p1'},{'rotulo':'Militar','to':'m1'}]},
  'p1':{'texto':'Barricadas e Liga Contra a Vacina','tipo':'acao','ramos':[{'to':'f1'}]},
  'm1':{'texto':'Tentativa de golpe (14/11/1904)','tipo':'acao','ramos':[{'to':'f2'}]},
  'f1':{'texto':'Estado de Sítio em 16/11/1904','tipo':'fim','ramos':[]},
  'f2':{'texto':'Movimento militar sufocado','tipo':'fim','ramos':[]}}}

CICLO={'raizId':'a','nos':{
  'a':{'texto':'A','tipo':'inicio','ramos':[{'to':'b'}]},
  'b':{'texto':'B','tipo':'acao','ramos':[{'to':'a'}]}}}

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Leo'}))
        try:
            r=await page.evaluate("""(f) => {
              const html=fluxoRenderNode(f.nos,f.raizId);
              const d=document.createElement('div'); d.innerHTML=html;
              const txt=[...d.querySelectorAll('.fluxo-node:not(.fluxo-node-ref)')]
                          .map(e=>e.textContent.trim());
              const conta=(s)=>txt.filter(t=>t.indexOf(s)>=0).length;
              return {total:txt.length,
                      desenrolar:conta('Desenrolar dos Conflitos'),
                      barricadas:conta('Barricadas'),
                      sitio:conta('Estado de Sítio'),
                      remissoes:[...d.querySelectorAll('.fluxo-node-ref')].map(e=>e.textContent.trim())};
            }""",CONVERGE)
            print('1) três causas convergindo num nó só:')
            print('   caixas desenhadas:',r['total'])
            print('   "Desenrolar dos Conflitos" aparece', r['desenrolar'],'vez(es)  [antes: 3]')
            print('   "Barricadas" aparece', r['barricadas'],'vez(es)  [antes: 3]')
            print('   "Estado de Sítio" aparece', r['sitio'],'vez(es)  [antes: 3]')
            print('   remissões:',r['remissoes'])
            assert r['desenrolar']==1, 'o nó compartilhado foi desenhado mais de uma vez'
            assert r['barricadas']==1 and r['sitio']==1, 'a subárvore ainda é replicada'
            assert len(r['remissoes'])==2, f'esperava 2 remissões, veio {len(r["remissoes"])}'
            assert all('segue em' in x for x in r['remissoes'])

            # --- 2) ciclo nao pode travar a aba ---
            r2=await page.evaluate("""(f) => {
              const t0=Date.now();
              const html=fluxoRenderNode(f.nos,f.raizId);
              const d=document.createElement('div'); d.innerHTML=html;
              return {ms:Date.now()-t0, caixas:d.querySelectorAll('.fluxo-node').length,
                      ref:d.querySelectorAll('.fluxo-node-ref').length};
            }""",CICLO)
            print('\n2) grafo com ciclo A->B->A:',r2,'(antes: recursão infinita)')
            assert r2['caixas']==3 and r2['ref']==1, r2
            assert r2['ms']<500

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — nó compartilhado desenhado uma vez só, e ciclo não trava mais')
        finally:
            await browser.close()
asyncio.run(main())
