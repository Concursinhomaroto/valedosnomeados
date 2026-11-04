# -*- coding: utf-8 -*-
# Agenda organizada: a mesma semana aparecia tres vezes (lista de hoje, grade e os 7 dias) e os itens
# antigos da agenda se misturavam com o cronograma. Agora: uma aba por vez (Hoje / Grade por hora /
# Proximos 7 dias), itens antigos escondidos (com aviso, mostrar e apagar — nada some sozinho), e o
# "Fim" absorvido pela pilula do prazo.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, graves
from _cron_fixture import seed_cron

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed_cron(),viewport={'width':1300,'height':900})
        await page.evaluate("""()=>{window.todayStr=()=>'2026-11-04';window.confirm=()=>true;
          db.cronograma={ativo:true,inicio:'2026-11-03',complementar:false,rodizio:false,v:2,feitos:{},lidos:{}};
          db.weeklyPlan={'2026-11-02':[{name:'item de ontem',livre:true}],
                         '2026-11-04':[{name:'FASE 1 · aprender o basico',livre:true},{name:'45min · Principios',livre:true}],
                         '2026-11-06':[{name:'Sabado de Especifico',livre:true}]};
          crAba='hoje';crMostrarManuais=false;showScreen('dashboard');renderWeeklyPlan();}""")

        print('=== A) uma visao por vez: Hoje, Grade e 7 dias ===')
        r=await page.evaluate("""()=>{const vis=()=>({hoje:!!document.querySelector('#cron-head .cron-hoje'),grade:!!document.querySelector('#cron-head .cron-grade'),
            dias:getComputedStyle(document.getElementById('weekly-plan')).display!=='none',aba:crAba});
          const out={padrao:vis()};
          const clica=t=>[...document.querySelectorAll('#cron-head .cron-aba')].find(b=>b.textContent.includes(t)).click();
          clica('Grade por hora');out.grade=vis();clica('Próximos 7 dias');out.dias=vis();clica('Hoje');out.volta=vis();
          out.abas=[...document.querySelectorAll('#cron-head .cron-aba')].map(b=>b.textContent.trim());return out;}""")
        print('   %s'%r)
        assert r['abas']==['📌 Hoje','🕐 Grade por hora','📅 Próximos 7 dias']
        assert r['padrao']=={'hoje':True,'grade':False,'dias':False,'aba':'hoje'}
        assert r['grade']=={'hoje':False,'grade':True,'dias':False,'aba':'grade'}
        assert r['dias']=={'hoje':False,'grade':False,'dias':True,'aba':'dias'}
        assert r['volta']==r['padrao']
        print('   OK\n')

        print('=== B) o "Fim" saiu da faixa e entrou na pilula do prazo ===')
        r=await page.evaluate("""()=>{const t=document.querySelector('#cron-head .cron-linha').innerText.replace(/\\\\s+/g,' ');
          const pills=[...document.querySelectorAll('#cron-head .cron-linha .cron-pill')].map(x=>x.textContent.trim());
          return {t,n:pills.length,fim:pills.some(x=>/^Fim /.test(x)),prazo:pills.find(x=>/prazo/.test(x))};}""")
        print('   %s'%r['prazo'])
        assert not r['fim'] and 'fim ' in r['prazo'] and 'prazo' in r['prazo']
        print('   OK\n')

        print('=== C) itens antigos da agenda: escondidos de hoje em diante, com aviso; os de dias passados nao contam ===')
        r=await page.evaluate("""()=>{crIrAba('dias');
          const itens=()=>document.querySelectorAll('#weekly-plan .plan-item').length;
          const cartoes=document.querySelectorAll('#weekly-plan .cron-dia').length;
          const nota=(document.querySelector('#cron-head .cron-manuais')||{}).innerText||'';
          return {itens:itens(),cartoes,nota:nota.replace(/\\\\s+/g,' '),n:crManuaisFuturos().length};}""")
        print('   %s'%r)
        assert r['itens']==0 and r['cartoes']>=7 and r['n']==3 and '3 itens' in r['nota'] and 'escondidos' in r['nota']
        r=await page.evaluate("""()=>{crManuaisAlternar();const mostra=document.querySelectorAll('#weekly-plan .plan-item').length;
          const nota=document.querySelector('#cron-head .cron-manuais').innerText.replace(/\\\\s+/g,' ');
          crManuaisAlternar();return {mostra,nota,esconde:document.querySelectorAll('#weekly-plan .plan-item').length};}""")
        print('   mostrar: %s'%r)
        assert r['mostra']==3 and 'aparecem' in r['nota'] and r['esconde']==0
        print('   OK\n')

        print('=== D) apagar tira so de hoje em diante e o aviso some ===')
        r=await page.evaluate("""()=>{crApagarManuais();
          return {ontem:(db.weeklyPlan['2026-11-02']||[]).length,hoje:(db.weeklyPlan['2026-11-04']||[]).length,sab:(db.weeklyPlan['2026-11-06']||[]).length,
                  nota:!!document.querySelector('#cron-head .cron-manuais'),toast:document.getElementById('toast').textContent};}""")
        print('   %s'%r)
        assert r['ontem']==1 and r['hoje']==0 and r['sab']==0 and not r['nota'] and '3 itens apagados' in r['toast']
        print('   OK\n')

        print('=== E) sem cronograma, a agenda segue como era: lista visivel e itens do usuario aparecendo ===')
        r=await page.evaluate("""()=>{db.cronograma.ativo=false;db.weeklyPlan={'2026-11-05':[{name:'Academia 18h',livre:true}]};crAba='grade';renderWeeklyPlan();
          return {lista:getComputedStyle(document.getElementById('weekly-plan')).display!=='none',itens:document.querySelectorAll('#weekly-plan .plan-item').length,
                  abas:document.querySelectorAll('#cron-head .cron-aba').length};}""")
        print('   %s'%r)
        assert r['lista'] and r['itens']==1 and r['abas']==0
        print('   OK\n')

        print('=== F) celular: nenhuma aba faz a pagina rolar de lado ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{db.cronograma.ativo=true;const out={};
          for(const a of ['hoje','grade','dias']){crIrAba(a);out[a]=document.documentElement.scrollWidth<=innerWidth+1;}return out;}""")
        print('   %s'%r)
        assert all(r.values())
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
