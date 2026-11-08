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

        print('=== B) Plano de assunto: materias como cartoes; clicar expande os chefes e assuntos da materia ===')
        r=await page.evaluate("""()=>{document.getElementById('nav-plano').click();const el=document.getElementById('plano-conteudo');
          const ini={cards:[...el.querySelectorAll('.pa-card')].map(c=>c.innerText.replace(/\\s+/g,' ')),chefes:el.querySelectorAll('.pa-chefe').length,aviso:el.innerText.includes('Clique numa matéria')};
          el.querySelectorAll('.pa-card')[0].click();
          const e1={chefes:document.querySelectorAll('#plano-conteudo .pa-chefe').length,itens:document.querySelectorAll('#plano-conteudo .pa-item').length,aberto:document.querySelector('.pa-card-aberto').innerText.includes('Enfermagem')};
          document.querySelectorAll('#plano-conteudo .pa-card')[1].click();
          const e2={chefes:document.querySelectorAll('#plano-conteudo .pa-chefe').length,itens:document.querySelectorAll('#plano-conteudo .pa-item').length,txt:document.getElementById('plano-conteudo').innerText};
          document.querySelectorAll('#plano-conteudo .pa-card')[1].click();
          const e3={chefes:document.querySelectorAll('#plano-conteudo .pa-chefe').length};
          return {tela:[...document.querySelectorAll('.screen.active')].map(s=>s.id),ini,e1,e2,e3,nav:document.getElementById('nav-plano').classList.contains('active'),
            rotulo:document.querySelector('#nav-plano .nav-label').textContent,txt:el.innerText.replace(/\\s+/g,' ')};}""")
        print('   ',r['ini'],r['e1'],r['e3'])
        assert r['tela']==['screen-plano'] and r['nav'] and r['rotulo']=='Plano' and r['ini']['chefes']==0 and r['ini']['aviso'] and len(r['ini']['cards'])==2
        assert '1 chefe ·' in r['ini']['cards'][1] and 'Enfermagem' in r['ini']['cards'][0] and '0 de 4 assuntos' in r['ini']['cards'][0] and '2 chefes' in r['ini']['cards'][0]
        assert r['e1']['chefes']==2 and r['e1']['itens']==4 and r['e1']['aberto'] and r['e2']['chefes']==1 and r['e2']['itens']==2 and 'Sintaxe' in r['e2']['txt'] and r['e3']['chefes']==0
        assert '0 de 6 assuntos estudados' in r['txt']
        print('   OK\n')

        print('=== C) clicar marca (com a data), clicar de novo desmarca; so um registro (sem revisao nem XP) ===')
        r=await page.evaluate("""async()=>{paFiltro.mundo='';paSetMundo('k1');const xp0=db.xp,rev0=JSON.stringify(db.revisions||null),stud0=db.topics.k1[0].subtopics[0].studied;
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

        print('=== D) marcar todos / limpar do chefe, busca (abre a materia sozinha) e so os que faltam ===')
        r=await page.evaluate("""()=>{const out={};const nomes=()=>[...document.querySelectorAll('#plano-conteudo .pa-nome')].map(x=>x.textContent);
          paMarcarChefe('t1',true);out.t1=['s1','s2','s3'].every(i=>db.planoAssunto[i]);
          paFiltro.mundo='';renderPlanoAssunto();out.fechado=document.querySelectorAll('#plano-conteudo .pa-chefe').length;
          paBuscar('vacina');out.busca=nomes();paBuscar('regên');out.busca2=nomes();paBuscar('');
          paSetMundo('k1');paSoPendentes(true);out.faltam=nomes();paSoPendentes(false);
          paMarcarChefe('t1',false);out.limpo=['s1','s2','s3'].every(i=>!db.planoAssunto[i]);
          return out;}""")
        print('   ',r)
        assert r['t1'] and r['fechado']==0 and r['busca']==['Vacinação'] and r['busca2']==['Regência'] and r['faltam']==['Vacinação'] and r['limpo']
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
