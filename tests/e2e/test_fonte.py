# -*- coding: utf-8 -*-
# Item desatualizado nao parece errado, parece certo. O de rastreamento do colo do
# utero trazia so o citopatologico, sem o DNA-HPV: coerente com a diretriz velha, e
# sem fonte datada nao havia como perceber. Agora toda explicacao diz de onde saiu.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) a regra da fonte esta nos tres geradores ===')
        r=await page.evaluate("""()=>{
          const t=simColarPromptTexto();
          return {colar:t.includes('FONTE — toda explicação traz a sua'),
                  ano:t.includes('sempre com o ANO da versão'),
                  velha:t.includes('versão antiga de um protocolo que mudou'),
                  naoInventa:t.includes('"fonte": "não confirmada"'),
                  convivem:t.includes('substituindo a antiga por etapas'),
                  exemploColo:t.includes('rastreamento do câncer do colo do útero, 2024'),
                  noExemploJSON:t.includes('"fonte":"Lei 8.080/1990, art. 7º"'),
                  miniboss:(generateQuestionsForSubject.toString().match(/promptFonteCebraspe/g)||[]).length,
                  chefao:(generateQuestionsForTopic.toString().match(/promptFonteCebraspe/g)||[]).length};}""")
        for k in ['colar','ano','velha','naoInventa','convivem','exemploColo','noExemploJSON']:
            assert r[k], k
        print('   prova colada: ok · miniboss: %s uso · chefão: %s uso'%(r['miniboss'],r['chefao']))
        print('   exige ano, proíbe referência inventada, trata diretriz em transição')
        assert r['miniboss']==1 and r['chefao']==1
        print('   OK\n')

        print('=== B) os exemplos de JSON internos tambem declaram o campo ===')
        r=await page.evaluate("""()=>({
          sub:generateQuestionsForSubject.toString().includes('"fonte":"Cofen 564/2017, art. 45"'),
          top:generateQuestionsForTopic.toString().includes('"fonte":"Lei 8.080/1990, art. 7º"')})""")
        print('   miniboss: %s · chefão: %s'%(r['sub'],r['top']))
        assert r['sub'] and r['top']
        print('   OK\n')

        print('=== C) a fonte sobrevive a importacao, nos dois formatos ===')
        r=await page.evaluate("""()=>{
          simColarPromptTexto();
          const achar=n=>simColarLista.findIndex(c=>c.sub.name===n)+1;
          simColarLote=[];
          document.getElementById('sg-colar-txt').value=JSON.stringify([
            {assunto:achar('Choque septico'),assuntoNome:'Choque septico',
             afirmacao:'A reposicao inicial e de 30 mL/kg.',gabarito:'C',
             explicacao:'Sim.',fonte:'Surviving Sepsis Campaign, 2021'},
            {assunto:achar('PCR'),assuntoNome:'PCR',questao:'Relacao no adulto?',
             alternativas:[{letra:'A',texto:'15:2'},{letra:'B',texto:'30:2'},
                           {letra:'C',texto:'5:1'},{letra:'D',texto:'10:2'},{letra:'E',texto:'20:2'}],
             correta:'B',explicacao:'30:2.',fonte:'AHA 2020 — SBV adulto'},
            {assunto:achar('PCR'),assuntoNome:'PCR',afirmacao:'Sem fonte.',gabarito:'E',
             explicacao:'x',fonte:'  n/a '}]);
          simColarAdicionar();
          return simColarLote.map(q=>({fmt:q.formato,fonte:q.fonte||null}));}""")
        for q in r: print('   %-12s fonte: %r'%(q['fmt'],q['fonte']))
        assert r[0]['fonte']=='Surviving Sepsis Campaign, 2021'
        assert r[1]['fonte']=='AHA 2020 — SBV adulto'
        assert r[2]['fonte'] is None, '"n/a" nao e fonte'
        print('   OK\n')

        print('=== D) aparece na tela de resultado, embaixo da explicacao ===')
        r=await page.evaluate("""async()=>{
          simColarIniciar(true);
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=300;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const fontes=[...document.querySelectorAll('.sim-fonte')].map(e=>e.innerText.trim());
          const cards=document.querySelectorAll('.sim-q').length;
          return {cards,fontes};}""")
        print('   %s questões na tela · %s com fonte'%(r['cards'],len(r['fontes'])))
        for f in r['fontes']: print('   %r'%f)
        assert r['cards']==3 and len(r['fontes'])==2
        assert any('Surviving Sepsis' in f for f in r['fontes'])
        print('   a que veio sem fonte não mostra linha vazia')
        print('   OK\n')

        print('=== E) a fonte fica guardada na prova e volta na revisao ===')
        r=await page.evaluate("""()=>{
          const q0=provaQuestoes(db.provas[0])[0];
          provaRevisar(db.provas[0].id);
          const naTela=[...document.querySelectorAll('.sim-fonte')].map(e=>e.innerText.trim());
          return {naProva:q0.fonte||null,naTela:naTela.length};}""")
        print('   guardada na prova: %r · na revisão: %s linhas'%(r['naProva'],r['naTela']))
        assert r['naProva']=='Surviving Sepsis Campaign, 2021' and r['naTela']==2
        print('   OK\n')

        print('=== F) fonte longa e cortada, e HTML nao passa cru ===')
        r=await page.evaluate("""()=>{
          const longa='X'.repeat(400);
          const a=simNormalizaQuestao({afirmacao:'t',gabarito:'C',fonte:longa},'certoerrado');
          const b=simNormalizaQuestao({afirmacao:'t',gabarito:'C',
                    fonte:'<img src=x onerror=alert(1)>'},'certoerrado');
          simGeralActive={questoes:[{...b,subId:'s1',subName:'PCR',topicName:'U',
            kingdomId:'k1',kingdomName:'E',kingdomIcon:'x',userAnswer:'C'}],
            corrected:true,formato:'certoerrado',startedAt:Date.now(),tempoGastoSec:1};
          const html=simGeralResultsHTML();
          return {len:a.fonte.length,teto:SIM_FONTE_MAX,
                  cru:html.includes('<img src=x'),escapado:html.includes('&lt;img src=x')};}""")
        print('   cortada em %s de %s · HTML cru: %s · escapado: %s'
              %(r['len'],r['teto'],r['cru'],r['escapado']))
        assert r['len']==r['teto'] and not r['cru'] and r['escapado']
        print('   OK\n')

        print('=== G) o conversor pede fonte sem inventar, e avisa gabarito da epoca ===')
        c=await page.evaluate("()=>simColarPromptConverter()")
        for m in ['EXPLICAÇÃO E FONTE','com o ANO da versão que você usou',
                  'nunca invente referência','gabarito da época; a diretriz vigente hoje é outra']:
            assert m in c, m
        print('   prova antiga mantém o gabarito da época, com nota embaixo do JSON')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
