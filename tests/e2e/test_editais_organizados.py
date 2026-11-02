# -*- coding: utf-8 -*-
# Tela de Editais organizada: "feito" = status realizado OU data ja passou. Por padrao so o que
# ainda vai acontecer (proxima prova primeiro), os ja feitos saem da frente numa vista propria
# (uma linha cada, "Marcar realizado" quando o status ficou desatualizado), formulario recolhido
# (aberto so quando nao ha edital), filtros com a contagem e marcar realizado tira o foco.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, seed, graves

SEED_JS="""()=>{const t=todayStr();
  const dia=n=>{const x=new Date(t+'T12:00:00');x.setDate(x.getDate()+n);return x.getFullYear()+'-'+String(x.getMonth()+1).padStart(2,'0')+'-'+String(x.getDate()).padStart(2,'0');};
  const mk=(i,nome,st,n)=>({id:'e'+i,nome,cargo:'Enf',banca:'FGV',data:dia(n),status:st,icon:'📋',color:'#6c47ff',disciplinas:[]});
  db.editais=[mk(1,'Feito A','realizado',-90),mk(2,'Feito B','realizado',-45),mk(3,'Vencido','inscrito',-10),
    mk(4,'Longe','inscricoes',75),mk(5,'Perto','inscrito',12),mk(6,'Meio','aguardando',40),mk(7,'Hoje','inscrito',0)];
  edFilter='ativos';showScreen('editais');renderEditais();}"""

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed(),viewport={'width':1100,'height':800})

        print('=== A) sem edital: formulario aberto e mensagem de vazio ===')
        r=await page.evaluate("()=>{db.editais=[];edFilter='ativos';showScreen('editais');renderEditais();return {aberto:document.getElementById('ed-novo').open,txt:document.getElementById('editais-list').innerText}}")
        print('   %s'%r)
        assert r['aberto'] and 'Nenhum edital cadastrado' in r['txt']
        print('   OK\n')

        print('=== B) padrao: so em andamento, o mais proximo primeiro; formulario recolhido ===')
        r=await page.evaluate(SEED_JS+"""
          ;return 0""") if False else None
        await page.evaluate(SEED_JS)
        r=await page.evaluate("""()=>({nomes:[...document.querySelectorAll('#editais-list .edital-nome')].map(x=>x.textContent),
          form:document.getElementById('ed-novo').open,
          chips:[...document.querySelectorAll('#edital-filter-row .chip')].map(c=>c.textContent.trim()),
          ativo:(document.querySelector('#edital-filter-row .chip.active')||{}).textContent,
          prox:document.getElementById('edital-counters').innerText.replace(/\\s+/g,' '),
          dica:(document.querySelector('.ed-feitos-dica')||{}).innerText})""")
        print('   %s'%r)
        assert r['nomes']==['Hoje','Perto','Meio','Longe'], r['nomes']       # hoje ainda e ativo; vencido/realizados fora
        assert not r['form'] and 'Em andamento · 4' in r['ativo']
        assert 'Já feitos · 3' in ' '.join(r['chips']) and 'Todos' in r['chips'][-1]
        assert 'Próxima prova' in r['prox'] and 'Hoje' in r['prox'] and 'hoje' in r['prox']
        assert '3 já feitos' in r['dica']
        print('   OK\n')

        print('=== C) filtro de status vale so entre os que ainda vao acontecer ===')
        r=await page.evaluate("""()=>{filterEditais('inscrito');
          return {nomes:[...document.querySelectorAll('#editais-list .edital-nome')].map(x=>x.textContent)};}""")
        print('   %s'%r)
        assert r['nomes']==['Hoje','Perto']          # o 'Vencido' (inscrito, prova passou) nao entra
        print('   OK\n')

        print('=== D) ja feitos: uma linha cada, mais recente primeiro, aviso no desatualizado ===')
        r=await page.evaluate("""()=>{filterEditais('feitos');
          const l=[...document.querySelectorAll('.ed-feito')];
          return {n:l.length,nomes:l.map(x=>x.querySelector('.ed-feito-nome').textContent),
                  avisos:l.map(x=>!!x.querySelector('.ed-feito-aviso')),btn:l.map(x=>!!x.querySelector('summary button')),
                  cartaoDentro:!!l[0].querySelector('.edital-card'),aberto:l.some(x=>x.open)};}""")
        print('   %s'%r)
        assert r['nomes']==['Vencido','Feito B','Feito A'] and r['avisos']==[True,False,False] and r['btn']==[True,False,False]
        assert r['cartaoDentro'] and not r['aberto']
        print('   OK\n')

        print('=== E) "Marcar realizado" muda o status sem abrir a linha e tira o foco ===')
        r=await page.evaluate("""()=>{db.editalFoco='e3';
          const b=document.querySelector('.ed-feito > summary .btn-primary');b.click();
          const e=db.editais.find(x=>x.id==='e3');
          return {st:e.status,foco:db.editalFoco,aviso:document.querySelectorAll('.ed-feito-aviso').length,aberto:[...document.querySelectorAll('.ed-feito')].some(x=>x.open),
                  toast:window.__toasts[window.__toasts.length-1]};}""")
        print('   %s'%r)
        assert r['st']=='realizado' and r['foco'] is None and r['aviso']==0 and not r['aberto'] and 'foco' in r['toast']
        print('   OK\n')

        print('=== F) Todos: ativos e depois os ja feitos ===')
        r=await page.evaluate("""()=>{filterEditais('all');
          return {cartoes:document.querySelectorAll('#editais-list > .edital-card').length,linhas:document.querySelectorAll('#editais-list .ed-feito').length,
                  tit:(document.querySelector('.ed-feitos-tit')||{}).textContent};}""")
        print('   %s'%r)
        assert r['cartoes']==4 and r['linhas']==3 and 'Já feitos · 3' in r['tit']
        print('   OK\n')

        print('=== G) chip de status some quando a contagem zera ===')
        r=await page.evaluate("""()=>{edFilter='ativos';db.editais=db.editais.filter(e=>e.status!=='aguardando');renderEditais();
          const a=[...document.querySelectorAll('#edital-filter-row .chip')].map(c=>c.textContent.trim());
          return a;}""")
        print('   %s'%r)
        assert not any('Aguardando' in c for c in r)
        print('   OK\n')

        print('=== H) adicionar fecha o formulario; rodar a tela nao quebra o badge ===')
        r=await page.evaluate("""()=>{document.getElementById('ed-novo').open=true;
          document.getElementById('ed-nome').value='Novo';document.getElementById('ed-data').value='2099-01-01';addEdital();
          return {form:document.getElementById('ed-novo').open,tem:!!db.editais.find(e=>e.nome==='Novo'),
                  badge:document.getElementById('editais-badge').style.display};}""")
        print('   %s'%r)
        assert not r['form'] and r['tem']
        print('   OK\n')

        print('=== I) celular: sem rolagem lateral ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>{filterEditais('all');return {w:document.documentElement.scrollWidth,iw:innerWidth};}")
        print('   %s'%r)
        assert r['w']<=r['iw']+1
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
