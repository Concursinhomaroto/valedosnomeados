# -*- coding: utf-8 -*-
# Ler a explicacao e concordar nao fixa nada. Escrever com as proprias palavras por que
# o item esta certo ou errado e o passo que fixa — e o grifo marca de onde a resposta
# saiu. Os dois moram na QUESTAO dentro da prova, entao voltam quando ela e refeita.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

MONTA = """(n)=>{
  const qs=[];
  for(let i=0;i<n;i++){
    const sub=i%2?{id:'s2',nome:'PCR'}:{id:'s1',nome:'Choque septico'};
    qs.push({questao:'A reposicao inicial no choque septico e de 30 mL/kg de cristaloide.',
      alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
      correta:i%3===0?'E':'C',explicacao:'Explicacao oficial da questao '+(i+1),
      formato:'certoerrado',textoApoio:'',
      subId:sub.id,subName:sub.nome,topicName:'Urgencia',
      kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'});
  }
  simGeralActive={questoes:qs,startedAt:Date.now()-600000,limiteSec:0,corrected:false,
                  formato:'certoerrado',nivel:'dificil',importado:true,tempoGastoSec:600};
  return qs.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) terminar a prova deixa o id dela no ativo ===')
        r=await page.evaluate("""async(n)=>{
          (%s)(n);
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<4?q.correta:(q.correta==='C'?'E':'C');});
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          return {provaId:!!simGeralActive.provaId,
                  bate:simGeralActive.provaId===db.provas[0].id};}"""%MONTA,6)
        print('   provaId no simGeralActive: %s · é a prova guardada: %s'%(r['provaId'],r['bate']))
        assert r['provaId'] and r['bate']
        print('   OK\n')

        print('=== B) a caixa de escrever aparece em cada questao ===')
        r=await page.evaluate("""()=>{
          const caixas=document.querySelectorAll('.sim-nota-txt');
          const cab=[...document.querySelectorAll('.sim-nota-cab')].map(e=>e.innerText.trim());
          return {n:caixas.length,cab:cab.slice(0,3),
                  paleta:!!document.querySelector('.sim-ferramentas .marca-pen'),
                  zonas:document.querySelectorAll('.marca-zona[data-sub]').length};}""")
        print('   caixas: %s · zonas marcáveis: %s · paleta de cores: %s'
              %(r['n'],r['zonas'],r['paleta']))
        for c in r['cab']: print('   cabeçalho: %r'%c)
        assert r['n']==6 and r['zonas']==6 and r['paleta']
        assert any('CERTO' in c for c in r['cab']) and any('ERRADO' in c for c in r['cab'])
        print('   OK\n')

        print('=== C) escrever e guardar: vai pra prova e pro historico do assunto ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sim-nota-0').value='30 mL/kg na primeira hora. Errei porque troquei com os 20 do pediatrico.';
          simNotaSalvar(0);
          const prova=db.provas[0];
          const hist=simFindSub(simGeralActive.questoes[0].subId).simHistorico[0];
          return {naProva:provaQuestoes(prova)[0].minhaNota,
                  naViva:simGeralActive.questoes[0].minhaNota,
                  noHistorico:(hist.questoes[0]||{}).minhaNota,
                  selo:document.getElementById('sim-nota-selo-0').textContent.trim()};}""")
        print('   na prova guardada: %r'%(r['naProva'] or '')[:52])
        print('   no histórico do miniboss: %s · selo: %r'%(bool(r['noHistorico']),r['selo']))
        assert r['naProva'].startswith('30 mL/kg') and r['naViva']==r['naProva']
        assert r['noHistorico']==r['naProva']
        assert 'guardada' in r['selo']
        print('   OK\n')

        print('=== D) grifar dentro da questao: a marca mora na questao da prova ===')
        r=await page.evaluate("""()=>{
          const zona=document.querySelector('.marca-zona[data-sub]');
          const chave=zona.getAttribute('data-sub');
          const alvo=marcaAlvo(chave);
          alvo.set([{t:'30 mL/kg',n:0,c:'v'}]);
          marcaInvalidar(chave);
          marcaAplicarTodas(true);
          const mk=zona.querySelector('mark.resumo-marca');
          return {chave,texto:mk?mk.textContent:null,cor:mk?mk.getAttribute('data-cor'):null,
                  naProva:(provaQuestoes(db.provas[0])[0].marcas||[]).length};}""")
        print('   chave da zona: %r'%r['chave'])
        print('   grifado: %r (cor %s) · marcas na prova guardada: %s'
              %(r['texto'],r['cor'],r['naProva']))
        assert r['chave'].startswith('q:')
        assert r['texto']=='30 mL/kg' and r['cor']=='v' and r['naProva']==1
        print('   OK\n')

        print('=== E) clicar no grifo tira ele, e so dele ===')
        r=await page.evaluate("""()=>{
          const zona=document.querySelector('.marca-zona[data-sub]');
          const chave=zona.getAttribute('data-sub');
          marcaRemover(chave,0);
          marcaAplicarTodas(true);
          return {marcas:(provaQuestoes(db.provas[0])[0].marcas||[]).length,
                  nota:provaQuestoes(db.provas[0])[0].minhaNota.slice(0,8),
                  mk:!!zona.querySelector('mark.resumo-marca')};}""")
        print('   marcas: %s · o grifo sumiu da tela: %s · a nota continua: %r'
              %(r['marcas'],not r['mk'],r['nota']))
        assert r['marcas']==0 and not r['mk'] and r['nota']=='30 mL/kg'
        print('   OK\n')

        print('=== F) refazer a prova traz de volta a nota e o grifo ===')
        r=await page.evaluate("""async()=>{
          const chave='q:'+db.provas[0].id+':0';
          marcaAlvo(chave).set([{t:'cristaloide',n:0,c:'r'}]);
          window.confirm=()=>true;
          provaRefazer(db.provas[0].id);
          // a NOTA e da tela de resultado (escrever por que errou so faz sentido depois
          // do gabarito). O GRIFO, desde a v203, existe durante a prova tambem — grifar
          // e o que se faz enquanto se le o item.
          const durante={caixa:!!document.getElementById('sim-nota-0'),
                         zona:!!document.querySelector('.marca-zona[data-sub]')};
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=300;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          marcaAplicarTodas(true);
          const zona=document.querySelector('.marca-zona[data-sub]');
          const mk=zona&&zona.querySelector('mark.resumo-marca');
          return {durante,
                  naCaixa:(document.getElementById('sim-nota-0')||{}).value||'',
                  grifo:mk?mk.textContent:null,
                  chave:zona?zona.getAttribute('data-sub'):null,
                  mesmaProva:db.provas.length};}""")
        print('   respondendo a prova: caixa de nota %s · zona de grifo %s'
              %(r['durante']['caixa'],r['durante']['zona']))
        print('   no resultado da refação — caixa: %r'%r['naCaixa'][:40])
        print('   grifo redesenhado: %r · zona: %r'%(r['grifo'],r['chave']))
        assert not r['durante']['caixa'], 'nota e da tela de resultado'
        assert r['durante']['zona'], 'grifo tem que existir durante a prova'
        assert r['naCaixa'].startswith('30 mL/kg'), r['naCaixa']
        assert r['grifo']=='cristaloide'
        assert r['mesmaProva']==1, 'refacao nao pode criar outra prova'
        print('   OK\n')

        print('=== G) resumo continua funcionando com o mesmo mecanismo ===')
        r=await page.evaluate("""()=>{
          const sub=simFindSub('s1');
          sub.resumo={texto:'A reposicao inicial e de 30 mL/kg.',marcas:[]};
          const d=document.createElement('div');
          d.className='resumo-body'; d.setAttribute('data-sub','s1');
          d.textContent='A reposicao inicial e de 30 mL/kg.';
          document.body.appendChild(d);
          marcaAlvo('s1').set([{t:'30 mL/kg',n:0,c:'a'}]);
          marcaInvalidar('s1'); marcaAplicarTodas(true);
          const mk=d.querySelector('mark.resumo-marca');
          const ok=!!mk&&mk.textContent==='30 mL/kg';
          d.remove();
          return {ok,guardado:(sub.resumo.marcas||[]).length};}""")
        print('   grifo no resumo: %s · guardado em sub.resumo.marcas: %s'%(r['ok'],r['guardado']))
        assert r['ok'] and r['guardado']==1
        print('   OK\n')

        print('=== H) a nota tem teto e nao quebra o HTML ===')
        r=await page.evaluate("""()=>{
          document.getElementById('sim-nota-1').value='<img src=x onerror=alert(1)>'+'a'.repeat(900);
          simNotaSalvar(1);
          const g=provaQuestoes(db.provas[0])[1].minhaNota;
          const html=simGeralResultsHTML();
          return {len:g.length,teto:NOTA_MAX,cru:html.includes('<img src=x'),
                  escapado:html.includes('&lt;img src=x')};}""")
        print('   guardou %s de %s permitidos · HTML cru: %s · escapado: %s'
              %(r['len'],r['teto'],r['cru'],r['escapado']))
        assert r['len']==r['teto'] and not r['cru'] and r['escapado']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
