# -*- coding: utf-8 -*-
# Grade por hora do cronograma: a semana em horas (como uma grade de horarios), cada dia de estudo em
# blocos em sequencia a partir da hora que a pessoa comeca, que somam as horas do dia, com pausa; domingo,
# feriado e semana final com blocos proprios; um painel com o tempo de cada materia na semana; e o rodizio,
# que faz Especificos, Politicas Publicas, Portugues e Legislacao avancarem juntos.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, graves
from _cron_fixture import seed_cron

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed_cron(),viewport={'width':1300,'height':900})
        # seu caso: comecou ontem (03/11), hoje e quarta 04/11, 4h por dia, sem a complementar
        await page.evaluate("""()=>{window.todayStr=()=>'2026-11-04';
          db.cronograma={ativo:true,inicio:'2026-11-03',complementar:false,feitos:{},lidos:{}};
          crGradeAberta=false;crGradeOff=0;showScreen('dashboard');renderWeeklyPlan();}""")

        print('=== A) a grade abre pelo botao, com 7 dias e o de hoje marcado ===')
        r=await page.evaluate("""()=>{const antes=!!document.querySelector('.cron-grade');
          const btn=[...document.querySelectorAll('#cron-head button')].find(b=>/Grade por hora/.test(b.textContent));
          btn.click();
          const cab=[...document.querySelectorAll('.cg-cab')];
          return {antes,depois:!!document.querySelector('.cron-grade'),cab:cab.map(c=>c.querySelector('b').textContent),
                  hoje:cab.filter(c=>c.classList.contains('cg-hoje')).map(c=>c.querySelector('span').textContent),
                  titulo:document.querySelector('.cg-topo b').textContent};}""")
        print('   %s'%r)
        assert not r['antes'] and r['depois'] and r['cab']==['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
        assert r['hoje']==['04/11'] and '02/11 a 08/11' in r['titulo']
        print('   OK\n')

        print('=== B) os blocos de um dia somam as horas, comecam na hora escolhida, sem sobrepor ===')
        r=await page.evaluate("""()=>{const out={};
          for(const h of [4,5]){crEstado().fases=[{desde:'2026-11-03',horas:h}];
            const {p,cols}=crSemanaDados(0);const c=cols.find(x=>x.ds==='2026-11-05');
            const est=c.seq.blocos.filter(b=>b.tipo!=='pausa');
            const soma=est.reduce((n,b)=>n+b.dur,0);
            let sobrepoe=false;c.seq.blocos.forEach((b,i,a)=>{if(i&&a[i-1].ini+a[i-1].dur>b.ini)sobrepoe=true;});
            out[h]={soma,n:est.length,pausas:c.seq.blocos.filter(b=>b.tipo==='pausa').length,sobrepoe,
                    primeiro:est[0].tipo,ultimos:est.slice(-2).map(b=>b.tipo),fim:c.seq.fim};}
          crEstado().fases=[{desde:'2026-11-03',horas:4}];
          renderCronCabecalho();const h1=document.querySelector('.cg-hora').textContent;
          const labs=[...document.querySelectorAll('.cg-hora')].map(x=>x.textContent);
          const b1=document.querySelector('.cg-bloco');const r1=+b1.style.gridRowStart;
          crSetHoraInicio('06:30');const h2=document.querySelector('.cg-hora').textContent;
          crSetHoraInicio('xx');const ficou=crEstado().horaInicio;
          crSetHoraInicio('08:00');
          return {out,h1,h2,ficou,labs,r1,rolar:document.getElementById('cron-grade').dataset.rolar};}""")
        print('   %s'%r)
        for h,o in r['out'].items():
            assert abs(o['soma']-int(h)*60)<=15, (h,o)           # arredondamento em 5 min por bloco
            assert not o['sobrepoe'] and o['pausas']>=1 and o['primeiro']=='revisao' and o['ultimos']==['questoes','erros']
        assert r['h1']=='06:00' and r['h2']=='06:00' and r['ficou']=='06:30'
        assert r['labs'][0]=='06:00' and r['labs'][-1]>='22:00' and len(r['labs'])>=17 and int(r['rolar'])>0
        print('   OK\n')

        print('=== C) domingo, feriado e semana final tem blocos proprios ===')
        r=await page.evaluate("""()=>{const get=(off,ds)=>{const {cols}=crSemanaDados(off);const c=cols.find(x=>x.ds===ds);return c.seq.blocos.filter(b=>b.tipo!=='pausa').map(b=>[b.tipo,b.titulo,b.dur]);};
          const dom=get(0,'2026-11-08'),fer=get(2,'2026-11-20');
          const p=crPlano();const fin=p.calendario.filter(d=>d.t==='fin');
          const off=Math.floor(daysDiff('2026-11-02',fin[4].ds)/7);
          const sab=get(off,fin[4].ds);const desc=p.calendario.find(d=>d.descanso);
          const offD=Math.floor(daysDiff('2026-11-02',desc.ds)/7);
          return {dom,fer,sab,desc:get(offD,desc.ds)};}""")
        print('   dom %s\\n   fer %s\\n   sab final %s\\n   descanso %s'%(r['dom'],r['fer'],r['sab'],r['desc']))
        assert [b[1] for b in r['dom']]==['Revisão da semana','Refazer os erros','Simulado de 30','Flashcards']
        assert abs(sum(b[2] for b in r['dom'])-240)<=10
        assert r['fer']==[['leve','Revisão leve',60]]
        assert r['sab'][0][1]=='Simulado completo' and r['desc'][0][1]=='Erros do simulado'
        print('   OK\n')

        print('=== D) rodizio: todas as materias avancam juntas, a ordem dentro de cada uma nao muda ===')
        r=await page.evaluate("""()=>{
          const semana=(p)=>{const sem={};p.dias.filter(d=>d.t==='est').forEach(d=>{const k=addDays(d.ds,-((crDow(d.ds)+6)%7));
            sem[k]=sem[k]||{esp:0,pol:0,por:0,leg:0};d.orig.forEach(id=>{sem[k][p.meta.get(id).bloco]+=p.meta.get(id).min;});});return Object.values(sem);};
          const ult=(p)=>{const u={};p.dias.filter(d=>d.t==='est').forEach((d,i)=>d.orig.forEach(id=>{u[p.meta.get(id).bloco]=i;}));return u;};
          const ordemBloco=(p,b)=>p.dias.flatMap(d=>d.orig).filter(id=>p.meta.get(id).bloco===b).join();
          crEstado().rodizio=false;const off=crPlano();const so=semana(off),uo=ult(off);
          crEstado().rodizio=true;const on=crPlano();const sn=semana(on),un=ult(on);
          const conj=(p)=>p.dias.flatMap(d=>d.orig).sort().join();
          return {porPrimeiras:so.slice(0,6).map(w=>w.por),polSomeEm:so.findIndex((w,i)=>i>3&&w.pol===0),
                  rodPor:sn.slice(1,9).map(w=>w.por),rodPol:sn.slice(1,9).map(w=>w.pol),rodEsp:sn.slice(1,9).map(w=>w.esp),
                  terminamOff:uo,terminamOn:un,
                  mesmaOrdem:['esp','pol','por','leg'].every(b=>ordemBloco(off,b)===ordemBloco(on,b)),
                  mesmoConjunto:conj(off)===conj(on),totOn:on.total,totOff:off.total};}""")
        print('   sem rodizio, Portugues nas 6 primeiras semanas: %s | termina (dia de estudo) %s'%(r['porPrimeiras'],r['terminamOff']))
        print('   com rodizio, semanas 2-9  esp %s  pol %s  por %s | termina %s'%(r['rodEsp'],r['rodPol'],r['rodPor'],r['terminamOn']))
        assert all(m==0 for m in r['porPrimeiras'])                   # na ordem do prompt, so em dezembro
        assert all(m>0 for m in r['rodPor']) and all(m>0 for m in r['rodPol']) and all(m>0 for m in r['rodEsp'])
        u=r['terminamOn']      # as tres grandes terminam juntas; a Legislacao (7 assuntos) termina antes e sobra tempo pra revisar
        assert max(u['esp'],u['pol'],u['por'])-min(u['esp'],u['pol'],u['por'])<=4 and u['leg']<=min(u['esp'],u['pol'],u['por']), u
        assert r['mesmaOrdem'] and r['mesmoConjunto'] and r['totOn']==r['totOff']==534
        print('   OK\n')

        print('=== E) o painel mostra o tempo de cada materia na semana e avisa a que nao tem assunto novo ===')
        r=await page.evaluate("""()=>{crGradeOff=0;renderCronCabecalho();
          const t=document.querySelector('.cg-resumo').innerText.replace(/\\s+/g,' ');
          const nomes=[...document.querySelectorAll('.cg-orc-n')].map(x=>x.textContent.trim());
          return {t,nomes};}""")
        print('   %s'%r['nomes'])
        assert r['nomes']==['Específicos','Políticas Públicas','Português','Legislação Ebserh','Revisões e flashcards','Questões','Erros e simulado']
        assert 'de estudo na semana (4h por dia)' in r['t']
        r=await page.evaluate("""()=>{crEstado().rodizio=false;crGradeOff=0;renderCronCabecalho();
          const a=document.querySelector('.cg-resumo .cron-aviso');const txt=a?a.innerText:'';crEstado().rodizio=true;renderCronCabecalho();return txt;}""")
        print('   sem rodizio: %s'%r[:140])
        assert 'Sem assunto novo nesta semana' in r and 'Português' in r and 'Ligue o rodízio' in r
        print('   OK\n')

        print('=== F) ligar o rodizio (ou mexer na complementar) no meio do caminho nao inventa nem apaga atraso ===')
        r=await page.evaluate("""()=>{window.todayStr=()=>'2026-11-10';const st=crEstado();st.feitos={};st.rodizio=false;st.zero=null;
          const p0=crPlano();
          // em dia: concluiu exatamente o previsto ate ontem, na ordem antiga
          p0.dias.filter(d=>d.ds<'2026-11-10').flatMap(d=>d.orig).forEach(id=>{st.feitos[id]={em:'2026-11-05',via:'estudado'};});
          const a=crPlano().atrasados.length;
          crAlternarRodizio();const b=crPlano().atrasados.length,rod=st.rodizio;
          // o dia seguinte passa sem estudar: o atraso volta a crescer pelo que o dia previa
          window.todayStr=()=>'2026-11-11';const dia=crPlano();const c=dia.atrasados.length;
          const previsto=dia.dias.find(d=>d.ds==='2026-11-10').orig.length;
          // atrasado de verdade (nada feito) continua atrasado depois de ligar/desligar
          window.todayStr=()=>'2026-11-10';st.feitos={};st.zero=null;st.rodizio=false;const d0=crPlano().atrasados.length;
          crAlternarRodizio();const d1=crPlano().atrasados.length;
          crAlternarComplementar();const d2=crPlano().atrasados.length;crAlternarComplementar();
          return {a,b,rod,c,previsto,d0,d1,d2};}""")
        print('   %s'%r)
        assert r['a']==0 and r['b']==0 and r['rod'] is True
        assert r['c']==r['previsto'] and r['previsto']>0       # no dia seguinte, so o que aquele dia previa
        assert r['d0']>0 and r['d1']==r['d0'] and r['d2']==r['d0'], r   # quem estava atrasado continua com o mesmo atraso
        print('   OK\n')

        print('=== G) clicar num bloco abre o dia; o do simulado chama o simulado; config tem hora e rodizio ===')
        r=await page.evaluate("""()=>{window.todayStr=()=>'2026-11-04';crGradeOff=0;renderCronCabecalho();
          const blocos=[...document.querySelectorAll('.cg-bloco')];
          const conteudo=blocos.find(b=>/assuntos/.test(b.innerText)&&/Legisla|Enfermagem|Urg/.test(b.innerText));
          const sim=blocos.find(b=>/Simulado de 30/.test(b.innerText));
          conteudo.click();const modal=document.getElementById('modal').classList.contains('open')&&document.getElementById('modal-title').innerText;
          closeModal();crAbrirConfig();const cfg=document.getElementById('modal-body').innerText;
          return {modal,sim:sim.getAttribute('onclick'),cfg,hora:!!document.getElementById('cron-hora'),rod:!!document.querySelector('input[onchange="crAlternarRodizio()"]')};}""")
        print('   %s'%{k:(v if k!='cfg' else v[:50]) for k,v in r.items()})
        assert r['modal'] and r['modal'].startswith('📅') and '/11' in r['modal']      # abre o dia do bloco clicado
        assert r['sim'].startswith('crSimuladoSemana(') and r['hora'] and r['rod'] and 'Rodízio' in r['cfg'] and 'Começo a estudar às' in r['cfg']
        print('   OK\n')

        print('=== H) celular: a pagina nao rola de lado com a grade aberta ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>{closeModal();showScreen('agenda');crAba='grade';renderCronCabecalho();const g=document.querySelector('.cron-grade');return {w:document.documentElement.scrollWidth,iw:innerWidth,rolaPorDentro:g.scrollWidth>g.clientWidth};}")
        print('   %s'%r)
        assert r['w']<=r['iw']+1 and r['rolaPorDentro']
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
