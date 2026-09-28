# -*- coding: utf-8 -*-
# Tres listas do registro eram cortadas pra ele nao crescer: historico de simulados
# gerais (20), log de sessoes (50) e historico por miniboss (5 por assunto). Isso e o
# registro da vida de estudo, e sumia pela porta dos fundos. O corte continua — e ele
# que mantem as telas rapidas — mas o excedente vai pro no de historico, nao pro lixo.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed(extra=None):
    d={'studyNickname':'Leo',
       'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
       'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
           {'id':'s1','name':'Choque septico','priority':70,'studied':True}]}]}}
    d.update(extra or {})
    return make_seed(d)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) historico de simulados gerais: corta, mas nao joga fora ===')
        r=await page.evaluate("""()=>{
          db.simGeral={historico:[]}; db.hist={geral:[],sessoes:[],subs:[]};
          for(let i=0;i<75;i++)db.simGeral.historico.unshift(
            {id:'g'+i,data:new Date(2026,0,1+i).toISOString(),quantidade:120,
             acertos:60+i%40,tempoGastoSec:3600,assuntos:[]});
          histApararGeral();
          const tudo=histGeralTudo();
          return {noRegistro:db.simGeral.historico.length, teto:HIST_GERAL_VIVO,
                  noNo:db.hist.geral.length, tudo:tudo.length,
                  semPerda:new Set(tudo.map(h=>h.id)).size,
                  maisNovaPrimeiro:tudo[0].id, maisAntiga:tudo[tudo.length-1].id};}""")
        print('   75 simulados → %s ficam no registro (teto %s), %s vão pro nó'
              %(r['noRegistro'],r['teto'],r['noNo']))
        print('   histórico completo: %s, sem nenhum id repetido: %s'%(r['tudo'],r['semPerda']))
        assert r['noRegistro']==20 and r['noNo']==55 and r['tudo']==75 and r['semPerda']==75
        assert r['maisNovaPrimeiro']=='g74' and r['maisAntiga']=='g0'
        print('   os 55 que antes eram apagados estão guardados, na ordem certa')
        print('   OK\n')

        print('=== B) log de sessoes de estudo ===')
        r=await page.evaluate("""()=>{
          db.freeSessions=[]; db.hist={geral:[],sessoes:[],subs:[]};
          for(let i=0;i<130;i++)db.freeSessions.push(
            {tipo:'simulado',reinoName:'X',segundos:600+i,
             data:'2026-0'+(1+i%9)+'-1'+(i%9),hora:'0'+(i%9)+':30'});
          const somaAntes=db.freeSessions.reduce((a,x)=>a+x.segundos,0);
          histApararSessoes();
          const somaDepois=db.freeSessions.reduce((a,x)=>a+x.segundos,0)
                          +db.hist.sessoes.reduce((a,x)=>a+x.segundos,0);
          return {vivas:db.freeSessions.length, teto:HIST_SESSOES_VIVAS,
                  noNo:db.hist.sessoes.length, somaAntes, somaDepois};}""")
        print('   130 sessões → %s vivas (teto %s) + %s no nó'
              %(r['vivas'],r['teto'],r['noNo']))
        print('   tempo total antes: %ss · depois: %ss'%(r['somaAntes'],r['somaDepois']))
        assert r['vivas']==50 and r['noNo']==80
        assert r['somaAntes']==r['somaDepois'], 'perdeu tempo de estudo no caminho'
        print('   nem um segundo de estudo sumiu')
        print('   OK\n')

        print('=== C) historico por miniboss vai SEM as questoes ===')
        r=await page.evaluate("""()=>{
          db.hist={geral:[],sessoes:[],subs:[]};
          const sub=simFindSub('s1');
          sub.simHistorico=[];
          for(let i=0;i<14;i++)sub.simHistorico.unshift({
            id:'h'+i,data:new Date(2026,0,1+i).toISOString(),quantidade:10,
            acertos:5+i%5,erros:5-i%5,
            questoes:Array.from({length:10},(_,k)=>({questao:'q'+i+'-'+k,correta:'C',
              explicacao:'texto longo '.repeat(20)}))});
          const pesoAntes=JSON.stringify(sub.simHistorico).length;
          histApararSub(sub);
          const guardados=db.hist.subs;
          return {vivos:sub.simHistorico.length, teto:HIST_SUB_VIVO,
                  noNo:guardados.length,
                  vivosTemQuestoes:sub.simHistorico.every(h=>(h.questoes||[]).length===10),
                  noNoSemQuestoes:guardados.every(h=>h.questoes===undefined),
                  temAgregado:guardados.every(h=>h.quantidade===10&&typeof h.acertos==='number'),
                  sabeDeQuem:guardados.every(h=>h.subId==='s1'&&h.subName==='Choque septico'),
                  pesoAntes, pesoNo:JSON.stringify(guardados).length};}""")
        print('   14 no assunto → %s vivos (teto %s) + %s no nó'
              %(r['vivos'],r['teto'],r['noNo']))
        print('   os vivos mantêm as questões: %s · os do nó vão sem elas: %s'
              %(r['vivosTemQuestoes'],r['noNoSemQuestoes']))
        print('   9 registros pesariam %s bytes com questões; sem elas: %s'
              %(r['pesoAntes'],r['pesoNo']))
        assert r['vivos']==5 and r['noNo']==9
        assert r['vivosTemQuestoes'] and r['noNoSemQuestoes']
        assert r['temAgregado'] and r['sabeDeQuem']
        assert r['pesoNo']<r['pesoAntes']/10
        print('   a curva do assunto fica; as questões já estão no Banco de Questões')
        print('   OK\n')

        print('=== D) nada disso entra no registro que sobe a cada saveDB ===')
        r=await page.evaluate("""()=>{
          const pay=payloadParaFirebase();
          return {hist:pay.hist, acervo:pay.acervo, arq:pay.provasArquivo,
                  temOResto:!!pay.kingdoms&&!!pay.simGeral,
                  historicoVivo:(pay.simGeral.historico||[]).length,
                  sessoesVivas:(pay.freeSessions||[]).length};}""")
        print('   hist no payload: %s · banco: %s · arquivo: %s'
              %(r['hist'],r['acervo'],r['arq']))
        print('   o payload leva as %s recentes e as %s sessões vivas, como sempre'
              %(r['historicoVivo'],r['sessoesVivas']))
        assert r['hist'] is None and r['acervo'] is None and r['arq'] is None
        assert r['temOResto'] and r['historicoVivo']==20 and r['sessoesVivas']==50
        print('   OK\n')

        print('=== E) grava no no proprio e nao duplica ao recarregar ===')
        r=await page.evaluate("""async()=>{
          window.__updateCalls=[];
          histSalvar(true);
          await new Promise(r=>setTimeout(r,300));
          const c=window.__updateCalls.filter(x=>/vdn_historico/.test(x.path));
          const antes={g:db.hist.geral.length,s:db.hist.sessoes.length,u:db.hist.subs.length};
          await histCarregar();               // como se o app reabrisse
          const depois={g:db.hist.geral.length,s:db.hist.sessoes.length,u:db.hist.subs.length};
          await histCarregar();               // e de novo
          const denovo={g:db.hist.geral.length,s:db.hist.sessoes.length,u:db.hist.subs.length};
          return {gravou:c.length,caminho:c[0]&&c[0].path,antes,depois,denovo};}""")
        print('   gravou em "%s"'%r['caminho'])
        print('   antes: %s · recarregou: %s · recarregou de novo: %s'
              %(r['antes'],r['depois'],r['denovo']))
        assert r['gravou']==1 and r['caminho']=='users/TEST_UID_LEO/vdn_historico'
        assert r['antes']==r['depois']==r['denovo'], 'duplicou ao recarregar'
        print('   união por id: recarregar duas vezes não duplica nada')
        print('   OK\n')

        print('=== F) os tetos que sobraram, e o aviso antes de doer ===')
        r=await page.evaluate("""()=>{
          let aviso='';
          const t=window.toast; window.toast=(m)=>{aviso=m;};
          acervoAvisou=false;
          db.acervo=Array.from({length:Math.round(ACERVO_MAX*0.85)},(_,i)=>
            ({questao:'q'+i,correta:'C',subId:'s1',kingdomId:'k1'}));
          const cortou=acervoAparar();
          window.toast=t;
          return {teto:ACERVO_MAX, arq:PROVARQ_MAX, cortou, aviso,
                  tamanho:db.acervo.length};}""")
        print('   banco: teto %s · arquivo de provas: teto %s'%(r['teto'],r['arq']))
        print('   a %s questões (85%% do teto) → cortou %s e avisou:'%(r['tamanho'],r['cortou']))
        print('   "%s"'%r['aviso'][:110])
        assert r['teto']==50000 and r['arq']==5000
        assert r['cortou']==0 and 'limite' in r['aviso']
        print('   avisa ANTES: descobrir depois não adianta, porque aí já sumiu')
        print('   OK\n')

        print('=== G) o caminho real: corrigir um simulado nao perde nada ===')
        r=await page.evaluate("""async()=>{
          db.hist={geral:[],sessoes:[],subs:[]};
          db.simGeral={historico:Array.from({length:20},(_,i)=>
            ({id:'v'+i,data:new Date(2026,0,1+i).toISOString(),quantidade:5,acertos:3,
              tempoGastoSec:60,assuntos:[]}))};
          db.freeSessions=Array.from({length:50},(_,i)=>
            ({tipo:'x',segundos:60,data:'2026-01-01',hora:'0'+(i%9)+':00'}));
          const sub=simFindSub('s1');
          sub.simHistorico=Array.from({length:5},(_,i)=>
            ({id:'w'+i,data:new Date().toISOString(),quantidade:2,acertos:1,erros:1,questoes:[]}));
          simGeralActive={questoes:[
            {questao:'nova 1',correta:'C',userAnswer:'C',subId:'s1',subName:'Choque septico',
             kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'},
            {questao:'nova 2',correta:'E',userAnswer:'C',subId:'s1',subName:'Choque septico',
             kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'}],
            startedAt:Date.now()-120000,corrected:false,formato:'certoerrado',
            nivel:'dificil',limiteSec:0,tempoGastoSec:0};
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,200));
          return {geralVivo:db.simGeral.historico.length, geralNo:db.hist.geral.length,
                  sessoesVivas:db.freeSessions.length, sessoesNo:db.hist.sessoes.length,
                  subVivo:simFindSub('s1').simHistorico.length, subNo:db.hist.subs.length,
                  totalGeral:histGeralTudo().length};}""")
        print('   geral: %s vivos + %s no nó (total %s)'
              %(r['geralVivo'],r['geralNo'],r['totalGeral']))
        print('   sessões: %s vivas + %s no nó'%(r['sessoesVivas'],r['sessoesNo']))
        print('   assunto: %s vivos + %s no nó'%(r['subVivo'],r['subNo']))
        assert r['geralVivo']==20 and r['geralNo']==1 and r['totalGeral']==21
        assert r['sessoesVivas']==50 and r['sessoesNo']==1
        assert r['subVivo']==5 and r['subNo']==1
        print('   cada uma das três listas empurrou 1 pro nó, nenhuma jogou fora')
        print('   OK\n')

        print('=== H) a tela mostra o historico inteiro, nao so o registro ===')
        # Guardar sem mostrar e meia solucao: o que foi pro no tem que aparecer.
        # O historico de Simulado Geral mora em Minhas Provas (Modo Treino completo tirou
        # ele da tela Treinar — la agora e so treino, sem prova nenhuma).
        r=await page.evaluate("""()=>{
          db.simGeral={historico:[]}; db.hist={geral:[],sessoes:[],subs:[]};
          for(let i=0;i<40;i++)db.simGeral.historico.unshift(
            {id:'t'+i,data:new Date(2026,0,1+i).toISOString(),quantidade:120,acertos:80,
             tempoGastoSec:3600,formato:'certoerrado',assuntos:[{subId:'s1'}]});
          histApararGeral();
          sgHistTudo=false;
          simGeralActive=null;      // o histórico mora na tela de configuração
          showScreen('provas');
          const el=document.getElementById('provas-content');
          const fechado=el.innerText;
          const linhasFechado=(el.innerHTML.match(/sg-hist-row/g)||[]).length;
          el.querySelector('.sg-mais').click();
          const aberto=document.getElementById('provas-content');
          const linhasAberto=(aberto.innerHTML.match(/sg-hist-row/g)||[]).length;
          return {noRegistro:db.simGeral.historico.length, noNo:db.hist.geral.length,
                  cabecalho:/40 desde/i.test(fechado),   // .sec-title é uppercase via CSS
                  linhasFechado, linhasAberto,
                  botao:/ver os 40/.test(fechado)};}""")
        print('   40 simulados: %s no registro + %s no nó'%(r['noRegistro'],r['noNo']))
        print('   cabeçalho diz "40 desde ...": %s · botão "ver os 40": %s'
              %(r['cabecalho'],r['botao']))
        print('   linhas na tela: %s fechado → %s aberto'%(r['linhasFechado'],r['linhasAberto']))
        assert r['noRegistro']==20 and r['noNo']==20
        assert r['cabecalho'] and r['botao']
        assert r['linhasFechado']==10 and r['linhasAberto']==40
        print('   os 20 que estavam fora do registro aparecem junto com os vivos')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
