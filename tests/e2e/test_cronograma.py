# -*- coding: utf-8 -*-
# Cronograma ativo (Ebserh/HU Brasil, 09/11/2026 a 31/01/2027): a Agenda deixa de ser so
# digitada e passa a ser um plano que se recalcula. Cobre os criterios de aceitacao do prompt
# (docs/cronograma/ebserh-2026-prompt.md, secao 8): cada assunto uma vez e na ordem, revisoes
# D+1/D+7/D+30, remarcar sozinho (atraso desliza, domingo intocado), adiantar ("ja sei" puxa o
# proximo), aviso [CONFERIR] antes de concluir, folga e "encurtar a data final", simulados
# nas proporcoes da prova, percentual por bloco e a Agenda mostrando tudo isso.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, graves
from _cron_fixture import seed_cron, DADOS

HOJE="()=>{window.todayStr=()=>window.__hoje;}"

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed_cron(),viewport={'width':1200,'height':900})
        await page.evaluate(HOJE)
        # Estes cenarios reproduzem o ritmo do prompt (5h por dia, comecando em 09/11, com a trilha
        # complementar, na ordem dele — sem o rodizio) pra os dias 1-3 serem os da tabela dele. O padrao real (4h, amanha, sem a
        # complementar) e conferido nos cenarios O a R.
        await page.evaluate("()=>{const st=crEstado();st.inicio='2026-11-09';st.fases=[{desde:'2026-11-09',horas:5}];st.complementar=true;st.rodizio=false;}")
        async def dia(ds):
            await page.evaluate("(d)=>{window.__hoje=d;}",ds)

        print('=== A) estrutura: 598 assuntos, cada um uma vez, na ordem; domingo e feriado sem assunto ===')
        await dia('2026-11-02')
        r=await page.evaluate("""()=>{const p=crPlano();
          const vistos=new Set();let dup=0;p.dias.forEach(d=>d.orig.forEach(id=>{if(vistos.has(id))dup++;vistos.add(id);}));
          const ordem={};let fora=0;
          p.dias.forEach(d=>d.orig.forEach(id=>{const m=p.meta.get(id);if((ordem[m.capId]||0)>m.idx)fora++;ordem[m.capId]=m.idx;}));
          const sund=p.dias.filter(d=>crDow(d.ds)===0);
          return {total:p.total,unicos:vistos.size,dup,fora,dias:p.totalDias,estfin:p.dias.filter(d=>d.t==='est'||d.t==='fin').length,antes:p.antes,diaN:p.diaN,
                  domTodosRev:sund.every(d=>d.t==='rev'),fer:p.dias.filter(d=>d.t==='fer').length,fin:p.dias.filter(d=>d.t==='fin').length,falt:p.falt.length,
                  domSemAssunto:p.dias.filter(d=>d.t==='rev'||d.t==='fer').every(d=>d.orig.length===0)};}""")
        print('   %s'%r)
        assert r['total']==598 and r['unicos']==598 and r['dup']==0 and r['fora']==0
        assert r['dias']==r['estfin'] and r['antes'] and r['diaN']==0 and r['domTodosRev'] and r['fer']==3 and r['fin']==5
        assert r['falt']==0 and r['domSemAssunto']
        print('   OK\n')

        print('=== B) desligado: a agenda convida a ativar; ligar mostra Dia X de N e a meta ===')
        r=await page.evaluate("()=>{showScreen('dashboard');renderWeeklyPlan();return document.getElementById('cron-head').innerText}")
        assert 'Ativar cronograma' in r and '598 assuntos' in r
        await dia('2026-11-09')
        r=await page.evaluate("""()=>{crAtivar();const h=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          const p=crPlano();return {h,ativo:crAtivo(),meta:p.hojeAtual.length,min:p.hojeMin,faixas:crFaixas(p.hojeAtual,p).map(g=>g.cap.nome+' '+g.faixa)};}""")
        print('   %s'%r)
        import re
        assert r['ativo'] and re.search(r'Dia 1 de \d+',r['h']) and 'Hoje: 9 assuntos' in r['h'] and 'Em dia' in r['h'] and '5h/dia' in r['h']
        assert r['meta']==9 and r['min']==198
        assert r['faixas']==['Legislação de Enfermagem 1–6','Ebserh: Mapa do edital HU Brasil 1','Ebserh: Legislação da Ebserh (HU Brasil) 1–2']
        print('   OK\n')

        print('=== C) concluir gera D+1, D+7 e D+30 e vira estudado ===')
        r=await page.evaluate("""()=>{const p=crPlano();const id=p.hojeAtual[0];const xp0=db.xp;
          crConcluir(id,'estudado');const s=crAcharSub(id).s;const rv=db.revisions[id];
          return {studied:s.studied,em:s.studiedAt,datas:rv.map(x=>x.date),pend:rv.every(x=>!x.completed),
                  feito:db.cronograma.feitos[id],xp:db.xp-xp0};}""")
        print('   %s'%r)
        assert r['studied'] and r['em']=='2026-11-09' and r['datas']==['2026-11-10','2026-11-16','2026-12-09'] and r['pend']
        assert r['feito']['via']=='estudado' and r['xp']>0
        print('   OK\n')

        print('=== D) "ja sei" nao rende XP, conclui, gera as revisoes e PUXA os proximos pro mesmo dia ===')
        r=await page.evaluate("""()=>{const p=crPlano();const xp0=db.xp;
          const ids=p.hojeAtual.filter(id=>!p.st.feitos[id]);   // os 8 que faltam do dia
          ids.forEach(id=>crConcluir(id,'ja-sei'));
          const q=crPlano();const dia2=q.dias[1].orig;
          // 1 concluido de verdade (22 min) + 8 "ja sei" (2 min cada) = 38 min gastos dos 198:
          // sobram 160 min, e a fila puxa 7 assuntos do dia seguinte (154 min; o 8o so entra se pelo
          // menos metade dele couber, e 154 + 11 passa de 160).
          const puxados=q.hojeAtual.filter(id=>!q.st.feitos[id]);
          return {xp:db.xp-xp0,hoje:q.hojeAtual.length,feitos:q.hojeAtual.filter(id=>q.st.feitos[id]).length,
                  puxouDia2:JSON.stringify(puxados)===JSON.stringify(dia2.slice(0,7)),
                  revs:ids.every(id=>(db.revisions[id]||[]).length===3),pend:q.pendentes,folga:q.folgaDias};}""")
        print('   %s'%r)
        assert r['xp']==0                                  # ja sei nao e atalho pra farmar XP
        assert r['feitos']==9 and r['hoje']==16 and r['puxouDia2'], r   # 9 feitos + 7 puxados de amanha
        assert r['revs'] and r['pend']==598-9 and r['folga']>=0
        print('   OK\n')

        print('=== E) atraso: o que ficou pra tras desliza pro proximo dia de estudo; domingo e feriado intocados ===')
        await page.evaluate("()=>{db.cronograma.feitos={};db.cronograma.lidos={};}")
        await dia('2026-11-10')
        r=await page.evaluate("""()=>{const p=crPlano();const orig=n=>p.dias[n].orig;
          const hoje=p.hojeAtual,qua=p.calendario.find(d=>d.ds==='2026-11-11').atual,dom=p.calendario.find(d=>d.ds==='2026-11-15'),
                sex20=p.calendario.find(d=>d.ds==='2026-11-20');
          return {atraso:p.atrasados.length,diaN:p.diaN,
                  hojeEhSegunda:JSON.stringify(hoje)===JSON.stringify(orig(0)),
                  quaEhTerca:JSON.stringify(qua)===JSON.stringify(orig(1)),
                  domTipo:dom.t,domItens:dom.atual.length,ferTipo:sex20.t,ferItens:sex20.atual.length,
                  head:document.getElementById('cron-head')?1:0};}""")
        print('   %s'%r)
        assert r['atraso']==9 and r['diaN']==2 and r['hojeEhSegunda'] and r['quaEhTerca']
        assert r['domTipo']=='rev' and r['domItens']==0 and r['ferTipo']=='fer' and r['ferItens']==0
        h=await page.evaluate("()=>{renderWeeklyPlan();return document.getElementById('cron-head').innerText.replace(/\\s+/g,' ')}")
        assert 'Atraso: 9 assuntos' in h and 'remarcado' in h, h
        print('   OK\n')

        print('=== F) [CONFERIR]: pede leitura antes de concluir e mostra o aviso ===')
        await dia('2026-11-09')
        r=await page.evaluate("""()=>{const p=crPlano();const id=p.hojeAtual[2];const s=crAcharSub(id).s;
          s.studied=false;delete db.revisions[id];
          s.resumo={texto:'Intro.\\nDose maxima 4 g [CONFERIR] na fonte oficial.\\nOutro paragrafo.'};
          renderWeeklyPlan();
          const marca=document.getElementById('cron-head').innerText.includes('conferir valores');
          crConcluir(id,'estudado');
          const modal=document.getElementById('modal').classList.contains('open')&&document.getElementById('modal-body').innerText;
          return {id,naoConcluiu:!db.cronograma.feitos[id],estudado:!!s.studied,modal,marca};}""")
        print('   %s'%{k:(v if k!='modal' else v[:70]) for k,v in r.items()})
        assert r['naoConcluiu'] and not r['estudado'] and r['marca']
        assert 'Dose maxima 4 g [CONFERIR]' in r['modal'] and 'Li o aviso' in r['modal']
        r2=await page.evaluate("""(id)=>{crConcluir(id,'ja-sei',true);return {feito:!!db.cronograma.feitos[id],lido:!!db.cronograma.lidos[id],
          modal:document.getElementById('modal').classList.contains('open')};}""",r['id'])
        assert r2['feito'] and r2['lido']
        print('   OK\n')

        print('=== G) desfazer volta ao estado anterior; com revisao cumprida, recusa ===')
        r=await page.evaluate("""()=>{const p=crPlano();const id=p.hojeAtual.find(x=>!p.st.feitos[x]);
          crAcharSub(id).s.studied=false;delete db.revisions[id];   // assunto limpo: o desfazer so reverte o que o cronograma criou
          crConcluir(id,'estudado');const a=!!db.revisions[id];
          crDesfazer(id);
          const s=crAcharSub(id).s;
          const volta={feito:!!db.cronograma.feitos[id],studied:s.studied,revs:!!db.revisions[id],a};
          crConcluir(id,'estudado');db.revisions[id][0].completed=true;crDesfazer(id);
          return {volta,recusou:!!db.cronograma.feitos[id]};}""")
        print('   %s'%r)
        assert r['volta']=={'feito':False,'studied':False,'revs':False,'a':True} and r['recusou']
        print('   OK\n')

        print('=== H) folga e encurtar a data final ===')
        r=await page.evaluate("""()=>{db.cronograma.feitos={};db.cronograma.lidos={};
          const p0=crPlano();const todos=p0.dias.flatMap(d=>d.orig);
          todos.slice(0,todos.length-40).forEach(id=>{db.cronograma.feitos[id]={em:'2026-11-08',via:'ja-sei'};});
          const p=crPlano();return {pend:p.pendentes,folga:p.folgaDias,para:p.encurtarPara,fim:p.fimAtual,fimBase:p.fimBase,fimEstudo:p.fimEstudo};}""")
        print('   %s'%r)
        FIMBASE=r['fimBase']
        assert r['pend']==40 and r['folga']>20 and r['para'] and r['para']<FIMBASE and r['fim']==FIMBASE
        r=await page.evaluate("""()=>{crAlternarEncurtar();const p=crPlano();
          const fin=p.calendario.filter(d=>d.t==='fin').length,ult=p.calendario[p.calendario.length-1];
          const apos=p.calendario.filter(d=>d.ds>p.fimEstudo&&d.t==='est').length;
          const h=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          return {enc:p.encurtado,fim:p.fimAtual,fin,ultT:ult.t,ultDs:ult.ds,apos,h:h.includes('Voltar fim para'),total:p.calendario.length};}""")
        print('   %s'%r)
        assert r['enc'] and r['fim']<FIMBASE and r['fin']==5 and r['ultT']=='rev' and r['ultDs']==r['fim'] and r['apos']==0 and r['h']
        r=await page.evaluate("()=>{crAlternarEncurtar();return crPlano().fimAtual}")
        assert r==FIMBASE
        print('   OK\n')

        print('=== I) trilha complementar fora: so o resto entra ===')
        comp=sum(c['n'] for c in DADOS['cap'] if c['cat']=='comp')
        r=await page.evaluate("()=>{db.cronograma.feitos={};crAlternarComplementar();const p=crPlano();const t=p.total;crAlternarComplementar();return t}")
        print('   total sem complementar: %s (598 - %s)'%(r,comp))
        assert r==598-comp
        print('   OK\n')

        print('=== J) simulados: proporcao da prova, FGV primeiro, so os assuntos da semana ===')
        r=await page.evaluate("""()=>{
          const p=crPlano();const qs=[];let n=0;
          p.meta.forEach((m,id)=>{for(let i=0;i<3;i++){qs.push({id:'q'+(n++),subId:id,banca:(n%4===0&&m.bloco==='esp')?'FGV':'Outra',ultimoResultado:n%10===0?'X':'C'});}});
          window.treinoPoolCompleto=()=>qs;
          window.__sel=null;window.treinoIniciar=(sel,meta)=>{window.__sel=sel;window.__meta=meta;return true;};
          window.renderSimGeralScreen=()=>{};
          crSimuladoCompleto();
          const comp=window.__sel.slice();
          const cont=a=>{const c={};a.forEach(q=>{const b=p.meta.get(q.subId).bloco;c[b]=(c[b]||0)+1;});return c;};
          const fgvTodas=qs.filter(q=>p.meta.get(q.subId).bloco==='esp'&&q.banca==='FGV').length;
          const fgvNaProva=comp.filter(q=>q.banca==='FGV').length;
          crSimuladoSemana('2026-11-15');
          const sem=window.__sel.slice();const subsSem=crSubsDaSemana('2026-11-15',p);
          crErrosSemana('2026-11-15');const erros=window.__sel.slice();
          crSimuladoDiagnostico();const diag=window.__sel.slice();
          return {completo:comp.length,contComp:cont(comp),titulo:window.__meta.titulo,fgvTodas,fgvNaProva,
                  sem:sem.length,semTudoDaSemana:sem.every(q=>subsSem.has(q.subId)),
                  erros:erros.length,errosSo:erros.every(q=>q.ultimoResultado==='X'&&subsSem.has(q.subId)),
                  diag:diag.length,contDiag:cont(diag)};}""")
        print('   %s'%r)
        assert r['completo']==60 and r['contComp']=={'esp':30,'pol':15,'por':10,'leg':5}, r['contComp']
        assert r['fgvNaProva']==min(r['fgvTodas'],30)            # FGV entra primeiro no bloco que tem
        assert r['sem']==30 and r['semTudoDaSemana'] and r['erros']>0 and r['errosSo']
        c=r['contDiag']        # minimos do prompt (10 esp, 8 SUS+Saude Publica, 6 Leg+Port) + 6 mistas por cima
        assert r['diag']==30 and c['esp']>=10 and c['pol']>=8 and c['leg']+c['por']>=6 and 'comp' not in c, c
        print('   OK\n')

        print('=== K) a Agenda mostra o cronograma: cartao por dia, domingo com simulado, modal e plano ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-09';db.cronograma.feitos={};showScreen('dashboard');renderWeeklyPlan();
          const cols=[...document.querySelectorAll('#weekly-plan .day-col')];
          const cartoes=cols.map(c=>({n:c.querySelectorAll('.cron-dia').length,txt:c.querySelector('.cron-dia')?c.querySelector('.cron-dia').innerText.replace(/\\s+/g,' '):''}));
          crAbrirDia('2026-11-15');const dom=document.getElementById('modal-body').innerText;
          crAbrirDia('2026-11-09');const seg=document.getElementById('modal-body').innerText;
          crAbrirPlano();const sem=document.querySelectorAll('.cron-plano-sem').length;
          crAbrirDia('2026-11-20');const fer=document.getElementById('modal-body').innerText;
          return {cartoes,dom,segLinhas:(seg.match(/assunto/g)||[]).length,seg:seg.slice(0,60),sem,fer};}""")
        print('   %s'%[c['txt'][:44] for c in r['cartoes']])
        assert all(c['n']==1 for c in r['cartoes'])
        assert '9 assuntos' in r['cartoes'][0]['txt'] and 'Legislação de Enfermagem' in r['cartoes'][0]['txt']
        assert 'Revisão semanal' in r['cartoes'][6]['txt']
        assert 'Simulado de 30' in r['dom'] and 'Erros da semana' in r['dom']
        assert r['sem']>=10
        assert 'Feriado' in r['fer']
        print('   OK\n')

        print('=== L) percentual por bloco e prova no painel; toggleTimer usa D+1/D+7/D+30 so com o cronograma ligado ===')
        r=await page.evaluate("""()=>{const p=crPlano();p.hojeAtual.slice(0,3).forEach(id=>{db.cronograma.feitos[id]={em:'2026-11-09',via:'estudado'};});
          const ed={id:'ed1',nome:'Ebserh HU Brasil',cargo:'Enf',banca:'FGV',data:'2027-03-01',status:'previsto',icon:'🏥',color:'#6c47ff',disciplinas:[]};
          db.editais=[ed];renderWeeklyPlan();
          const h=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          const on=crRevisoesIniciais('2026-11-09').length;db.cronograma.ativo=false;const off=crRevisoesIniciais('2026-11-09');db.cronograma.ativo=true;
          return {h,on,off:off.map(x=>x.date)};}""")
        print('   %s'%r)
        assert 'Específicos' in r['h'] and 'Políticas Públicas' in r['h'] and 'Português' in r['h'] and 'Legislação Ebserh' in r['h']
        assert 'Prova 01/03' in r['h'] and r['on']==3 and r['off']==['2026-11-16']
        print('   OK\n')

        print('=== N) diagnostico: sem registro pede; com historico antigo mostra o resultado; ao encerrar grava por bloco ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-02';closeModal();db.cronograma.diagnostico=null;db.treinoHistorico=[];
          renderWeeklyPlan();const sem=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          // feito antes do registro existir: so o historico do treino sabe
          db.treinoHistorico=[{id:'h1',data:'2026-11-02T13:00:00.000Z',titulo:'Simulado diagnóstico',respondidas:30,certas:18,liquida:6}];
          renderWeeklyPlan();const hist=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          return {sem,hist};}""")
        print('   %s'%{k:v[v.find('Antes') if 'Antes' in v else v.find('Diagn'):][:150] for k,v in r.items()})
        assert 'Abrir diagnóstico' in r['sem'] and 'Diagnóstico feito' not in r['sem']
        assert 'Diagnóstico feito em 02/11: 18/30 (60%)' in r['hist'] and 'Abrir diagnóstico' not in r['hist'] and 'Refazer diagnóstico' in r['hist']
        r=await page.evaluate("""()=>{
          const p=crPlano();const ids=[...p.meta.keys()];
          const porBloco=b=>ids.filter(id=>p.meta.get(id).bloco===b);
          const esp=porBloco('esp'),pol=porBloco('pol'),leg=porBloco('leg');
          const itens=[];const add=(id,ok)=>itens.push({subId:id,userAnswer:ok?'A':'B',correta:'A'});
          for(let i=0;i<10;i++)add(esp[i],i<6);      // 6/10 em Especificos
          for(let i=0;i<8;i++)add(pol[i],i<2);       // 2/8 em Politicas  (o ponto mais fraco)
          for(let i=0;i<3;i++)add(leg[i],true);      // 3/3 em Legislacao
          treinoSessao={itens,idx:0,titulo:'Simulado diagnóstico',seg:0,segPend:0,segLancado:0,ultimoTick:Date.now(),
            iniciadoEm:Date.now(),respondidas:21,certas:11,erradas:10,puladas:new Set(),respondidasSet:new Set(itens.map((_,i)=>i)),revisao:null};
          window.renderSimGeralScreen=()=>{};
          treinoEncerrar();
          const d=db.cronograma.diagnostico;renderWeeklyPlan();
          return {d,h:document.getElementById('cron-head').innerText.replace(/\\s+/g,' '),tr:(db.treinoHistorico[0]||{}).titulo};}""")
        print('   %s'%{'d':r['d']['blocos'],'certas':r['d']['certas']})
        d=r['d']
        assert d['respondidas']==21 and d['certas']==11 and d['em']=='2026-11-02'
        assert d['blocos']['esp']=={'tot':10,'certas':6} and d['blocos']['pol']=={'tot':8,'certas':2} and d['blocos']['leg']=={'tot':3,'certas':3}
        assert 'Específicos 6/10' in r['h'] and 'ponto mais fraco: Políticas Públicas (25%)' in r['h'], r['h']
        print('   OK\n')

        print('=== O) seu caso: comeca amanha, 4h por dia, sem a trilha complementar (estado antigo migra) ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-02';closeModal();
          db.cronograma={ativo:true,complementar:true,feitos:{},lidos:{}};   // como ficou salvo na versao anterior
          const st=crEstado();const p=crPlano();renderWeeklyPlan();
          const est=p.dias.filter(d=>d.t==='est');
          return {inicio:p.inicio,horas:p.horas,comp:st.complementar,rod:st.rodizio,v:st.v,total:p.total,antes:p.antes,dia1:est[0].orig.length,dia2:est[1].orig.length,
                  min1:est[0].orig.reduce((n,id)=>n+p.meta.get(id).min,0),
                  h:document.getElementById('cron-head').innerText.replace(/\\s+/g,' ')};}""")
        print('   %s'%{k:v for k,v in r.items() if k!='h'})
        assert r['inicio']=='2026-11-03' and r['horas']==4 and r['comp'] is False and r['v']==2 and r['antes']
        assert r['rod'] is True                      # estado antigo ganha o rodizio
        assert r['total']==534 and 6<=r['dia1']<=9 and 6<=r['dia2']<=9 and r['min1']<=158+11
        assert 'Começa em 1 dia' in r['h'] and '4h/dia' in r['h']
        print('   OK\n')

        print('=== P) prazo de 3 meses: 4h nao fecha tudo, e o app diz quanto fecha; 4h30 fecha ===')
        r=await page.evaluate("""()=>{crEstado().rodizio=false;const a=crPlano();const ha=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          crSetHoras(4.5);const b=crPlano();const hb=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          crSetHoras(4);
          return {prazo:a.prazo,noA:a.noPrazo,nec:a.horasNec,fimA:a.fimAtual,ha,noB:b.noPrazo,fimB:b.fimAtual,hb,dia1B:b.dias.filter(d=>d.t==='est')[0].orig.length};}""")
        print('   4h: no prazo=%s fim %s (prazo %s) precisa ~%sh · 4,5h: no prazo=%s fim %s'%(r['noA'],r['fimA'],r['prazo'],r['nec'],r['noB'],r['fimB']))
        assert r['prazo']=='2027-02-03' and not r['noA'] and r['nec']==4.5 and r['fimA']>r['prazo']
        assert 'além do prazo' in r['ha'] and 'fecha com ~4,5h/dia' in r['ha']
        assert r['noB'] and r['fimB']<=r['prazo'] and 'No prazo' in r['hb'] and r['dia1B']==8
        print('   OK\n')

        print('=== Q) mudar as horas no meio do caminho nao cria atraso falso ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-10';db.cronograma.feitos={};
          const a=crPlano().atrasados.length;crSetHoras(6);const p=crPlano();
          return {a,b:p.atrasados.length,fases:db.cronograma.fases,hoje6:p.horas};}""")
        print('   %s'%r)
        assert r['a']>0 and r['a']==r['b'] and r['hoje6']==6 and len(r['fases'])==2 and r['fases'][1]['desde']=='2026-11-10'
        await page.evaluate("()=>{crSetHoras(4);}")
        print('   OK\n')

        print('=== R) mudar o inicio antes de comecar; configuracao mostra horas e prazo ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-02';db.cronograma.fases=[{desde:db.cronograma.inicio,horas:4}];
          crSetInicio('2026-11-01');const rejeitou=crEstado().inicio==='2026-11-03';
          crSetInicio('2026-11-05');const p=crPlano();
          crAbrirConfig();const m=document.getElementById('modal-body').innerText;const val=document.getElementById('cron-horas').value;
          return {rejeitou,inicio:p.inicio,primeiroDia:p.dias[0].ds,m,val};}""")
        print('   %s'%{k:(v if k!='m' else v[:60]) for k,v in r.items()})
        assert r['rejeitou'] and r['inicio']=='2026-11-05' and r['primeiroDia']=='2026-11-05' and r['val']=='4'
        assert 'Horas de estudo por dia' in r['m'] and 'Prazo de 3 meses' in r['m'] and 'não estava no último edital' in r['m']
        print('   OK\n')

        print('=== S) edital da Ebserh ainda nao saiu: o plano avisa, e o aviso some ao confirmar ===')
        r=await page.evaluate("""()=>{window.__hoje='2026-11-02';closeModal();db.editais=[];db.editalFoco=null;
          const st=crEstado();delete st.editalSaiu;renderWeeklyPlan();
          const antes=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          crAbrirConfig();const cfg=document.getElementById('modal-body').innerText;closeModal();
          crEditalSaiu();
          const depois=document.getElementById('cron-head').innerText.replace(/\\s+/g,' ');
          return {antes,cfg,depois,flag:crEstado().editalSaiu};}""")
        a,d=r['antes'],r['depois']
        print('   antes: %s | depois tem aviso: %s'%('Prova sem data' in a,'ainda não foi publicado' in d))
        assert 'O edital da Ebserh ainda não foi publicado' in a and 'último (Ebserh/FGV 03/2024' in a and 'Prova sem data (edital não publicado)' in a
        assert 'não estava no último edital (03/2024)' in r['cfg'] and 'não cai no edital' not in r['cfg']
        assert r['flag'] is True and 'ainda não foi publicado' not in d and 'Cadastre a data da prova em Editais' in d
        print('   OK\n')

        print('=== M) celular: sem rolagem lateral com o cronograma na tela ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>{closeModal();showScreen('dashboard');renderWeeklyPlan();return {w:document.documentElement.scrollWidth,iw:innerWidth};}")
        print('   %s'%r)
        assert r['w']<=r['iw']+1
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
