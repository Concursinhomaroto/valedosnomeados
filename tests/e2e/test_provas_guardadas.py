# Uma prova de 120 itens era consumida uma vez e evaporava: db.simGeral.historico so
# guarda agregado, o simHistorico por miniboss guarda as 5 ultimas e emagrece as certas,
# e simGeralReset jogava a prova fora. Agora ela fica guardada e da pra refazer.
# colar prova e o banco mudaram de painel (aba Minhas Provas); o teste olha os dois
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

# monta uma prova certo/errado de 10 itens, ja no formato interno
MONTA = """(n)=>{
  const qs=[];
  for(let i=0;i<n;i++){
    const sub=i%2?{id:'s2',nome:'PCR'}:{id:'s1',nome:'Choque septico'};
    qs.push({questao:'Item '+(i+1)+' sobre '+sub.nome+'.',
      alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
      correta:i%3===0?'E':'C',explicacao:'Porque sim, item '+(i+1)+'.',
      formato:'certoerrado',textoApoio:i<2?'Texto base compartilhado.':'',
      subId:sub.id,subName:sub.nome,topicName:'Urgencia',
      kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'});
  }
  simGeralActive={questoes:qs,startedAt:Date.now()-600000,limiteSec:0,corrected:false,
                  formato:'certoerrado',nivel:'dificil',importado:true};
  return qs.length;
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) terminar a prova guarda ela inteira ===')
        r=await page.evaluate("""async(n)=>{
          (%s)(n);
          // acerta 6 de 10
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<6?q.correta:(q.correta==='C'?'E':'C');});
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const pr=(db.provas||[])[0];
          return {n:(db.provas||[]).length,
                  questoes:pr?pr.questoes.length:0,
                  origem:pr?pr.origem:null,
                  tentativas:pr?pr.tentativas.length:0,
                  acertos:pr?pr.tentativas[0].acertos:null,
                  temExplicacao:!!(pr&&pr.questoes[0].explicacao),
                  temAlternativas:!!(pr&&pr.questoes[0].alternativas),
                  temApoio:!!(pr&&pr.questoes[0].textoApoio),
                  semResposta:pr?pr.questoes.every(q=>q.userAnswer===undefined):null,
                  respostasNaTentativa:pr?pr.tentativas[0].respostas.length:0};}"""%MONTA,10)
        print('   provas guardadas: %s · questões: %s · origem: %s'%(r['n'],r['questoes'],r['origem']))
        print('   guarda alternativas: %s · explicação: %s · texto de apoio: %s'
              %(r['temAlternativas'],r['temExplicacao'],r['temApoio']))
        print('   a resposta fica na TENTATIVA, não na questão: %s (%s respostas)'
              %(r['semResposta'],r['respostasNaTentativa']))
        assert r['n']==1 and r['questoes']==10 and r['origem']=='colado'
        assert r['tentativas']==1 and r['acertos']==6
        assert r['temAlternativas'] and r['temExplicacao'] and r['temApoio']
        assert r['semResposta'] and r['respostasNaTentativa']==10
        print('   OK\n')

        print('=== B) a tela lista a prova, com o placar ===')
        r=await page.evaluate("""()=>{simGeralReset();
          const t=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText);
          return {secao:t.toLowerCase().indexOf('provas guardadas')>=0,
                  placar:(t.match(/1ª: 6\\/10[^\\n]*/)||[''])[0],
                  botao:(document.getElementById('provas-content').innerHTML+document.getElementById('simgeral-content').innerHTML).indexOf('provaRefazer')>=0};}""")
        print('   seção: %s · botão refazer: %s'%(r['secao'],r['botao']))
        print('   placar: %r'%r['placar'])
        assert r['secao'] and r['botao'] and '6/10' in r['placar'] and 'líq. +2' in r['placar']
        print('   OK\n')

        print('=== C) refazer carrega a prova zerada, sem sujar a guardada ===')
        r=await page.evaluate("""()=>{
          const id=db.provas[0].id;
          provaRefazer(id);
          const a=simGeralActive;
          return {n:a.questoes.length,semResposta:a.questoes.every(q=>!q.userAnswer),
                  refazendo:!!a.refazendo,tentativa:a.tentativaNum,
                  mesmoTexto:a.questoes[0].questao===db.provas[0].questoes[0].questao,
                  outroObjeto:a.questoes[0]!==db.provas[0].questoes[0]};}""")
        print('   %s questões, todas em branco: %s · %sª tentativa'
              %(r['n'],r['semResposta'],r['tentativa']))
        print('   mesmo enunciado: %s · é cópia (não a guardada): %s'
              %(r['mesmoTexto'],r['outroObjeto']))
        assert r['n']==10 and r['semResposta'] and r['refazendo'] and r['tentativa']==2
        assert r['mesmoTexto'] and r['outroObjeto']
        print('   OK\n')

        print('=== D) a refacao NAO mexe em simStats, Banco de Erros nem flashcards ===')
        r=await page.evaluate("""async()=>{
          const antes={s1:JSON.parse(JSON.stringify(simFindSub('s1').simStats||{})),
                       s2:JSON.parse(JSON.stringify(simFindSub('s2').simStats||{})),
                       banco:getErrorBank().length,
                       cards:Object.keys(db.flashcards||{}).length,
                       hist:(db.simGeral.historico||[]).length};
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});  // gabarita
          simGeralActive.startedAt=Date.now()-300000;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          return {antes,depois:{s1:simFindSub('s1').simStats,s2:simFindSub('s2').simStats,
                   banco:getErrorBank().length,cards:Object.keys(db.flashcards||{}).length,
                   hist:(db.simGeral.historico||[]).length},
                  tentativas:db.provas[0].tentativas.length,
                  acertos2:db.provas[0].tentativas[1].acertos};}""")
        print('   simStats s1: %s → %s'%(r['antes']['s1'],r['depois']['s1']))
        print('   Banco de Erros: %s → %s · flashcards: %s → %s · histórico geral: %s → %s'
              %(r['antes']['banco'],r['depois']['banco'],r['antes']['cards'],
                r['depois']['cards'],r['antes']['hist'],r['depois']['hist']))
        print('   tentativas na prova: %s (2ª com %s acertos)'%(r['tentativas'],r['acertos2']))
        assert r['antes']['s1']==r['depois']['s1'] and r['antes']['s2']==r['depois']['s2']
        assert r['antes']['banco']==r['depois']['banco']
        assert r['antes']['cards']==r['depois']['cards']
        assert r['antes']['hist']==r['depois']['hist']
        assert r['tentativas']==2 and r['acertos2']==10
        print('   OK\n')

        print('=== E) o resultado compara com a tentativa anterior ===')
        r=await page.evaluate("""()=>{const t=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText);
          return {titulo:t.toLowerCase().indexOf('resultado da refação')>=0,
                  linha:(t.match(/2ª tentativa[^\\n]*/)||[''])[0]};}""")
        print('   %s'%r['linha'])
        assert r['titulo'] and 'Antes: 6/10' in r['linha'] and '+4 acerto' in r['linha']
        assert 'não entra nas estatísticas' in r['linha']
        print('   OK\n')

        print('=== F) o placar da lista mostra a evolucao ===')
        r=await page.evaluate("""()=>{simGeralReset();
          const t=(document.getElementById('provas-content').innerText+document.getElementById('simgeral-content').innerText).replace(/\\s+/g,' ');
          const i=t.indexOf('1ª: 6/10');
          return i<0?t.slice(0,200):t.slice(i,i+80);}""")
        print('   %r'%r); assert '1ª: 6/10' in r and '2ª: 10/10' in r
        print('   OK\n')

        print('=== G) teto: passando dele, a mais antiga sai ===')
        # o numero sai de PROVAS_MAX, nao chumbado aqui: o teto ja mudou uma vez
        r=await page.evaluate("""async(n)=>{
          for(let k=0;k<PROVAS_MAX+2;k++){
            (%s)(4);
            simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
            simGeralCorrigir();
          }
          await new Promise(r=>setTimeout(r,300));
          return {n:db.provas.length,teto:PROVAS_MAX,
                  maisNova:db.provas[0].questoes.length,
                  aindaTem10:db.provas.some(p=>p.questoes.length===10)};}"""%MONTA,4)
        print('   provas guardadas: %s (teto %s) · a de 10 questões ainda existe: %s'
              %(r['n'],r['teto'],r['aindaTem10']))
        assert r['n']==r['teto'] and not r['aindaTem10']
        print('   OK\n')

        print('=== H) apagar uma prova nao mexe nas estatisticas ===')
        r=await page.evaluate("""()=>{window.confirm=()=>true;
          const antes={n:db.provas.length,st:JSON.stringify(simFindSub('s1').simStats)};
          provaApagar(db.provas[0].id);
          return {antes,n:db.provas.length,st:JSON.stringify(simFindSub('s1').simStats)};}""")
        print('   provas: %s → %s · simStats intacto: %s'
              %(r['antes']['n'],r['n'],r['st']==r['antes']['st']))
        assert r['n']==r['antes']['n']-1 and r['st']==r['antes']['st']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
