# "O marca-texto nao aparece quando eu abro o resumo, so aparece quando marco de novo."
# renderTopics monta o painel JA FECHADO e toggleResumo so tira a classe que esconde —
# nao redesenha nada. As marcas existiam no banco e ficavam invisiveis ate a proxima vez.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

TEXTO=("SONDAGEM VESICAL:\nA sondagem vesical de demora e privativa do Enfermeiro.\n\n"
       "Na pratica: o tecnico nao passa sonda em nenhuma situacao.")
SUB='s1'

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'d','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Procedimentos','icon':'x','subtopics':[
          {'id':SUB,'name':'Sondagem','priority':100,'studied':True,'studiedAt':'2026-01-01',
           'resumo':{'texto':TEXTO,'geradoEm':'2026-09-01T10:00:00.000Z','origem':'web',
                     'marcas':[{'t':'privativa do Enfermeiro','n':0,'c':'a'},
                               {'t':'nao passa sonda','n':0,'c':'r'}]}}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) abrir o reino: as marcas ja vem desenhadas ===')
        r=await page.evaluate("""async()=>{
          openKingdom(db.kingdoms[0]);
          await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
          const mks=[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')];
          return {n:mks.length,textos:mks.map(m=>m.textContent),
                  cores:mks.map(m=>m.getAttribute('data-cor'))};}""")
        print('   marcas na tela: %s → %s (cores %s)'%(r['n'],r['textos'],r['cores']))
        assert r['n']==2 and 'privativa do Enfermeiro' in r['textos']
        assert sorted(r['cores'])==['a','r']
        print('   OK\n')

        print('=== B) abrir o painel do resumo nao apaga nem duplica ===')
        r=await page.evaluate("""async()=>{
          toggleResumo('s1');
          await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
          const mks=[...document.querySelectorAll('#resumo-s1 mark.resumo-marca')];
          return {n:mks.length,aberto:document.getElementById('resumo-s1').classList.contains('resumo-open')};}""")
        print('   painel aberto: %s · marcas: %s'%(r['aberto'],r['n']))
        assert r['aberto'] and r['n']==2
        print('   OK\n')

        print('=== C) redesenhar a lista inteira mantem as marcas ===')
        r=await page.evaluate("""async()=>{
          renderTopics();
          await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
          return document.querySelectorAll('#resumo-s1 mark.resumo-marca').length;}""")
        print('   depois de renderTopics: %s marcas'%r); assert r==2
        print('   OK\n')

        print('=== D) o observador nao entra em laco ===')
        r=await page.evaluate("""async()=>{
          let passadas=0;
          const orig=window.marcaAplicarTodas;
          window.marcaAplicarTodas=function(f){passadas++;return orig.apply(this,arguments);};
          renderTopics();
          await new Promise(r=>setTimeout(r,600));
          window.marcaAplicarTodas=orig;
          return {passadas,marcas:document.querySelectorAll('#resumo-s1 mark.resumo-marca').length};}""")
        print('   passadas do redesenho em 600ms: %s · marcas: %s'%(r['passadas'],r['marcas']))
        assert r['passadas']<=3 and r['marcas']==2
        print('   OK\n')

        print('=== E) na tela de revisao tambem, sem chamada explicita ===')
        r=await page.evaluate("""async()=>{
          revAbrirTela('s1');
          await new Promise(r=>setTimeout(r,300));
          const mks=[...document.querySelectorAll('#modal-body mark.resumo-marca')].map(m=>m.textContent);
          revFecharTela();
          return mks;}""")
        print('   %s'%r); assert len(r)==2
        print('   OK\n')

        print('=== F) marcar de novo continua funcionando (redesenho forcado) ===')
        r=await page.evaluate("""()=>{
          const root=document.querySelector('#resumo-s1 .resumo-body[data-sub]');
          const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null);
          let n;
          while((n=w.nextNode())){
            const i=n.nodeValue.indexOf('SONDAGEM');
            if(i>=0){const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+8);
              const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);break;}
          }
          marcaSalvarSelecao('s1'); marcaAplicarTodas(true);
          return [...document.querySelectorAll('#resumo-s1 mark.resumo-marca')].map(m=>m.textContent);}""")
        print('   %s'%r); assert len(r)==3 and 'SONDAGEM' in r
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
