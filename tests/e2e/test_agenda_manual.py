# -*- coding: utf-8 -*-
# Agenda manual: apagar as agendas geradas (Ebserh e planos por edital) e montar a semana na mao, por hora.
import asyncio,sys
sys.path.insert(0,'tests/e2e'); sys.path.insert(0,'.')
from playwright.async_api import async_playwright
from test_aba_dicas import abrir, graves
from _agenda_fix import seed_agenda, ATIVAR_JS

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(b,seed_agenda(),viewport={'width':1300,'height':900})
        print('=== A) apagar as geradas: sai Ebserh e planos; fica progresso, blocos e o que voce digitou ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);window.confirm=()=>true;A({eds:['e1','e2'],hoje:'2026-11-04',inicio:'2026-11-05'});
          const st=crEstado();const p=crPlano();const id=p.agenda.fila[0];
          st.feitos[id]={em:'2026-11-04',via:'estudado'};st.pins={[p.agenda.fila[1]]:{ds:'2026-11-09'}};
          st.bloqueios=[{id:'b1',data:'2026-11-06',inicio:'14:00',min:90,titulo:'Plantao'}];
          db.weeklyPlan={'2026-11-06':[{name:'Academia',livre:true,criadoEm:'2026-11-04'}]};
          db.agendaPlanos.versoes=[{em:'x'}];
          showScreen('agenda');renderWeeklyPlan();
          const antes={ativo:st.ativo,planos:Object.keys(db.agendaPlanos.planos).length};
          agApagarGeradas();
          const s2=crEstado();
          return {antes,ativo:s2.ativo,ap:db.agendaPlanos,pins:s2.pins,fases:s2.fases,feitos:Object.keys(s2.feitos).length,bq:s2.bloqueios.length,wp:db.weeklyPlan['2026-11-06'].length,
            card:document.getElementById('cron-head').innerText.includes('Agenda manual'),gradeEbserh:document.querySelectorAll('#cron-head .cg-bloco:not(.cg-manual)').length,
            manuais:document.querySelectorAll('#cron-head .cg-manual').length,lista:getComputedStyle(document.getElementById('weekly-plan')).display,
            abas:document.querySelectorAll('#cron-head .cron-aba').length,blocos:Object.keys(CRON_BLOCOS)};}""",ATIVAR_JS)
        print('  ',r)
        assert r['antes']['ativo'] and r['antes']['planos']==1
        assert r['ativo'] is False and r['ap']=={'ativoId':None,'planos':{},'versoes':[]} and r['pins'] is None and r['fases'] is None
        assert r['feitos']==1 and r['bq']==1 and r['wp']==1,'progresso, blocos e itens digitados ficam'
        assert r['card'] and r['gradeEbserh']==0 and r['manuais']==1 and r['lista']=='none' and r['abas']==0
        print('   OK\n')

        print('=== B) criar bloco na mao: validacao, repeticao semanal, editar, excluir serie ===')
        r=await page.evaluate("""()=>{const set=(k,v)=>{document.getElementById(k).value=v;};
          agAbrirBloco('2026-11-09');
          set('agb-t','');set('agb-m','3');agSalvarBloco('');const invalido=crEstado().bloqueios.length;
          set('agb-t','Estudar Português');set('agb-i','05:30');set('agb-m','90');set('agb-r','semana');set('agb-ate','2026-11-30');agSalvarBloco('');
          const lista=crEstado().bloqueios.filter(b=>b.titulo==='Estudar Português');
          crGradeSemana(1);
          const labs=[...document.querySelectorAll('.cg-hora')].map(x=>x.textContent);
          const seg=document.querySelectorAll('#cron-head .cg-manual').length;crGradeSemana(0);
          const um=lista[0];
          agAbrirBloco(um.data,um.id);set('agb-t','Português forte');set('agb-m','45');agSalvarBloco(um.id);
          const ed=crEstado().bloqueios.find(b=>b.id===um.id);
          agAbrirBloco(um.data,um.id);agExcluirBloco(um.id,true);
          return {invalido,n:lista.length,datas:lista.map(b=>b.data),serie:new Set(lista.map(b=>b.serie)).size,labs0:labs[0],seg,ed:[ed.titulo,ed.min],depois:crEstado().bloqueios.filter(b=>b.titulo.includes('Portugu')).length,restam:crEstado().bloqueios.length};}""")
        print('  ',r)
        assert r['invalido']==1 and r['n']==4 and r['datas']==['2026-11-09','2026-11-16','2026-11-23','2026-11-30'] and r['serie']==1
        assert r['labs0']=='05:00','o eixo tem que abrir antes das 06h quando ha bloco mais cedo'
        assert r['ed']==['Português forte',45] and r['depois']==0 and r['restam']==1
        print('   OK\n')

        print('=== C) com plano ativo o bloco aparece e o estudo se reorganiza em volta ===')
        r=await page.evaluate("""(js)=>{const A=eval(js);A({eds:['e1','e2'],hoje:'2026-11-04',inicio:'2026-11-05'});
          crEstado().bloqueios=[];crAba='grade';renderWeeklyPlan();const h0=crPlano().horasEm('2026-11-05');
          agAbrirBloco('2026-11-05');const set=(k,v)=>{document.getElementById(k).value=v;};set('agb-t','Plantao');set('agb-i','06:00');set('agb-m','60');agSalvarBloco('');
          const h1=crPlano().horasEm('2026-11-05');
          const man=document.querySelectorAll('#cron-head .cg-manual').length,est=document.querySelectorAll('#cron-head .cg-bloco:not(.cg-manual)').length;
          return {h0,h1,man,est};}""",ATIVAR_JS)
        print('  ',r)
        assert r['h1']==r['h0']-1 and r['man']==1 and r['est']>0
        print('   OK\n')

        print('=== D) celular: sem rolar de lado, modal do bloco ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{agAbrirBloco('2026-11-05');const w=document.documentElement.scrollWidth;closeModal();return {w,iw:innerWidth};}""")
        print('  ',r); assert r['w']<=r['iw']+1
        print('erros de JS:',graves(errs) or 'nenhum'); assert not graves(errs)
        print('OK')
asyncio.run(main())
