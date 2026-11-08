# -*- coding: utf-8 -*-
# Agenda desligada + "Plano de assunto": lista Mundo > Chefe > assuntos com caixinha "ja estudei" (so um registro).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':False}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Português','icon':'📖'}],
      'topics':{'k1':[{'id':'t1','name':'Saúde da Mulher','icon':'⚔️','subtopics':[sub('s1','Pré-natal'),sub('s2','Puerpério'),sub('s3','Aleitamento')]},
                      {'id':'t2','name':'Saúde da Criança','icon':'⚔️','subtopics':[sub('s4','Vacinação')]}],
                'k2':[{'id':'t3','name':'Sintaxe','icon':'⚔️','subtopics':[sub('s5','Regência'),sub('s6','Concordância')]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{window.__VDN_LIGAR=[];recursosAplicar();window.confirm=()=>true;return true;}")

        print('=== A) Agenda desligada: some do menu, a tela volta pro Painel, nao monta nada, dados guardados ===')
        r=await page.evaluate("""()=>{const vis=id=>{const e=document.getElementById(id);return !!e&&getComputedStyle(e).display!=='none';};
          db.cronograma={ativo:true,inicio:'2026-11-05',v:2,feitos:{},lidos:{}};db.weeklyPlan={'2026-11-06':[{name:'Academia',livre:true}]};
          showScreen('agenda');const tela=[...document.querySelectorAll('.screen.active')].map(s=>s.id);
          const cab=document.getElementById('cron-head');if(cab)cab.innerHTML='';renderWeeklyPlan();
          return {nav:vis('nav-agenda'),plano:vis('nav-plano'),tela,montou:!!(cab&&cab.innerHTML.trim()),cardPainel:vis('screen-dashboard')&&!!document.querySelector('.dash-agenda')&&getComputedStyle(document.querySelector('.dash-agenda')).display!=='none',
            guardado:db.cronograma.ativo===true&&db.weeklyPlan['2026-11-06'].length===1};}""")
        print('   ',r)
        assert r['nav'] is False and r['plano'] is True and r['tela']==['screen-dashboard'] and r['montou'] is False and r['cardPainel'] is False and r['guardado']
        print('   OK\n')

        print('=== B) Plano de assunto: abre, lista Mundo > Chefe > assuntos, total 0 de 6 ===')
        r=await page.evaluate("""()=>{document.getElementById('nav-plano').click();const el=document.getElementById('plano-conteudo');
          return {tela:[...document.querySelectorAll('.screen.active')].map(s=>s.id),txt:el.innerText.replace(/\\s+/g,' '),chefes:el.querySelectorAll('.pa-chefe').length,itens:el.querySelectorAll('.pa-item').length,
            nav:document.getElementById('nav-plano').classList.contains('active')};}""")
        print('   ',r['tela'],r['chefes'],r['itens'])
        assert r['tela']==['screen-plano'] and r['chefes']==3 and r['itens']==6 and r['nav'] and '0 de 6 assuntos estudados' in r['txt'] and 'Enfermagem' in r['txt'] and 'Saúde da Mulher' in r['txt']
        print('   OK\n')

        print('=== C) clicar marca (com a data), clicar de novo desmarca; so um registro (sem revisao nem XP) ===')
        r=await page.evaluate("""async()=>{const xp0=db.xp,rev0=JSON.stringify(db.revisions||null),stud0=db.topics.k1[0].subtopics[0].studied;
          const cb=()=>document.querySelector('.pa-item input');
          cb().click();const a={marcado:!!(db.planoAssunto&&db.planoAssunto.s1),data:db.planoAssunto.s1,txt:document.getElementById('plano-conteudo').innerText.replace(/\\s+/g,' ')};
          await new Promise(r=>setTimeout(r,1400));
          const salvo=JSON.stringify(window.__root.users.TEST_UID_LEO.vdn_v1.planoAssunto||null);
          cb().click();const b={marcado:!!(db.planoAssunto&&db.planoAssunto.s1)};
          cb().click();
          return {a,b,salvo,hoje:todayStr(),xp:db.xp===xp0,rev:JSON.stringify(db.revisions||null)===rev0,mapa:db.topics.k1[0].subtopics[0].studied===stud0};}""")
        print('   ',r)
        assert r['a']['marcado'] and r['a']['data']==r['hoje'] and '1 de 6 assuntos estudados' in r['a']['txt'] and r['b']['marcado'] is False
        assert 's1' in r['salvo'] and r['xp'] and r['rev'] and r['mapa']
        print('   OK\n')

        print('=== D) marcar todos / limpar do chefe, filtro por Mundo, busca e so os que faltam ===')
        r=await page.evaluate("""()=>{const out={};
          paMarcarChefe('t1',true);out.t1=['s1','s2','s3'].every(i=>db.planoAssunto[i]);
          paSetMundo('k2');out.soPort=document.querySelectorAll('#plano-conteudo .pa-chefe').length;paSetMundo('k2');out.todos=document.querySelectorAll('#plano-conteudo .pa-chefe').length;
          paBuscar('vacina');out.busca=[...document.querySelectorAll('#plano-conteudo .pa-nome')].map(x=>x.textContent);paBuscar('');
          paSoPendentes(true);out.faltam=[...document.querySelectorAll('#plano-conteudo .pa-nome')].map(x=>x.textContent);paSoPendentes(false);
          paMarcarChefe('t1',false);out.limpo=['s1','s2','s3'].every(i=>!db.planoAssunto[i]);
          return out;}""")
        print('   ',r)
        assert r['t1'] and r['soPort']==1 and r['todos']==3 and r['busca']==['Vacinação'] and r['faltam']==['Vacinação','Regência','Concordância'] and r['limpo']
        print('   OK\n')

        print('=== E) dado vindo da nuvem como objeto/nulo nao quebra; assunto apagado nao conta ===')
        r=await page.evaluate("""()=>{db.planoAssunto=null;renderPlanoAssunto();const a=document.getElementById('plano-conteudo').innerText.includes('0 de 6');
          db.planoAssunto={s1:'2026-11-07',sFantasma:'2026-11-07'};renderPlanoAssunto();const b=document.getElementById('plano-conteudo').innerText.replace(/\\s+/g,' ');
          db.planoAssunto=['x'];renderPlanoAssunto();const c=document.getElementById('plano-conteudo').innerText.includes('0 de 6');
          return {a,b:b.includes('1 de 6'),c};}""")
        print('   ',r); assert r['a'] and r['b'] and r['c']
        print('   OK\n')

        print('=== F) celular: nao rola de lado; menu Mais tem Plano de assunto e nao tem Agenda ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{document.body.classList.add('nav-mais-aberto');const v=id=>getComputedStyle(document.getElementById(id)).display!=='none';
          const out={plano:v('nav-plano'),agenda:v('nav-agenda'),w:document.documentElement.scrollWidth,iw:innerWidth};document.body.classList.remove('nav-mais-aberto');return out;}""")
        print('   ',r); assert r['plano'] and r['agenda'] is False and r['w']<=r['iw']+1
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
