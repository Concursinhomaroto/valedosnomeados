# A capa do caderno Cebraspe diz que a ausencia de marcacao NAO e apenada. O app
# contava todo nao-acerto como -1 no "saldo Cebraspe" — punia deixar em branco do
# mesmo jeito que punia errar, que e o contrario do que a prova cobra.
import asyncio, re, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

# 12 itens certo/errado: 6 de s1, 6 de s2. A resposta certa e sempre 'C' pra
# facilitar a montagem do gabarito no teste.
MONTA = """(padrao)=>{
  const qs=[];
  for(let i=0;i<12;i++){
    const s=i<6?{id:'s1',nome:'Choque septico'}:{id:'s2',nome:'PCR'};
    qs.push({questao:'Item '+(i+1),alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
      correta:'C',explicacao:'x',formato:'certoerrado',
      subId:s.id,subName:s.nome,topicName:'Urgencia',
      kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'});
  }
  // padrao: 'a'=acerta, 'e'=erra, 'b'=branco
  qs.forEach((q,i)=>{const p=padrao[i];
    if(p==='a')q.userAnswer='C'; else if(p==='e')q.userAnswer='E';});
  simGeralActive={questoes:qs,startedAt:Date.now()-600000,limiteSec:0,corrected:false,
                  formato:'certoerrado',nivel:'dificil',importado:true,tempoGastoSec:600};
  return qs.length;
}"""

def num(html,rx):
    m=re.search(rx,html)
    return m.group(1) if m else None

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        # s1: 1 acerto, 4 erros, 1 branco  -> saldo -3 (marcar custou ponto)
        # s2: 5 acertos, 0 erros, 1 branco -> saldo +5
        # total: 6 acertos, 4 erros, 2 brancos -> liquido +2 (conta antiga: 0)
        PADRAO='aeeeeb'+'aaaaab'

        print('=== A) em branco nao conta como erro ===')
        html=await page.evaluate("""(padrao)=>{(%s)(padrao);return simGeralResultsHTML();}"""%MONTA,PADRAO)
        saldo=num(html,r'saldo Cebraspe: ([+-]?\d+)')
        liq=num(html,r'([+-]?\d+) líquidos')
        brancos=num(html,r'(\d+) em branco \(não pesam\)')
        antigo=num(html,r'em branco valiam <b>(-?\d+)</b>')
        print('   6 acertos · 4 erros · 2 em branco')
        print('   saldo Cebraspe: %s · liquido no bloco: %s · brancos: %s'%(saldo,liq,brancos))
        print('   conta antiga valia: %s'%antigo)
        assert saldo=='+2', saldo
        assert liq=='+2', liq
        assert brancos=='2', brancos
        assert antigo=='0', antigo
        assert '6 acertos' in html and '4 erros' in html
        print('   OK\n')

        print('=== B) o assunto em que marcar custou ponto aparece ===')
        perdidos=num(html,r'Marcar custou (\d+) ponto')
        print('   perdidos: %s'%perdidos)
        assert perdidos=='3', perdidos
        assert 'Choque septico' in html.split('Marcar custou')[1][:400]
        # s2 tem saldo positivo: nao pode entrar na lista de caros
        trecho=html.split('Marcar custou')[1].split('</div>\n      </div>')[0]
        assert 'PCR' not in trecho, 'assunto com saldo positivo entrou na lista'
        assert '1/5 marcadas' in html
        print('   so o assunto de saldo negativo entrou (1/5 marcadas), PCR ficou de fora')
        print('   OK\n')

        print('=== C) prova toda marcada: nada de "em branco", nota diferente ===')
        html2=await page.evaluate("""(padrao)=>{(%s)(padrao);return simGeralResultsHTML();}"""%MONTA,'aaaaae'+'aaaaee')
        saldo2=num(html2,r'saldo Cebraspe: ([+-]?\d+)')
        print('   9 acertos · 3 erros · 0 brancos -> saldo %s'%saldo2)
        assert saldo2=='+6', saldo2
        assert 'Marcar custou' not in html2   # nenhum assunto com saldo negativo
        # "em branco" tambem aparece no title explicativo; o que nao pode e o contador
        assert not re.search(r'\d+ em branco \(não pesam\)',html2)
        assert not re.search(r'· \d+ em branco',html2)
        assert 'Você marcou todos os itens' in html2
        print('   OK\n')

        print('=== D) sem nenhum acerto e tudo em branco o liquido e zero, nao -12 ===')
        html3=await page.evaluate("""(padrao)=>{(%s)(padrao);return simGeralResultsHTML();}"""%MONTA,'b'*12)
        saldo3=num(html3,r'saldo Cebraspe: ([+-]?\d+)')
        antigo3=num(html3,r'em branco valiam <b>(-?\d+)</b>')
        print('   12 em branco -> saldo %s (conta antiga: %s)'%(saldo3,antigo3))
        assert saldo3=='0', saldo3   # zero nao leva sinal
        assert antigo3=='-12', antigo3
        assert 'Marcar custou' not in html3
        print('   OK\n')

        print('=== E) multipla escolha nao mostra o bloco (o desconto e so do C/E) ===')
        html4=await page.evaluate("""(padrao)=>{(%s)(padrao);simGeralActive.formato='multipla';
          return simGeralResultsHTML();}"""%MONTA,PADRAO)
        assert 'sg-liquido' not in html4 and 'saldo Cebraspe' not in html4
        print('   OK\n')

        print('=== F) provaLiquido: com e sem o campo respostas ===')
        r=await page.evaluate("""()=>({
          comBranco:provaLiquido({acertos:6,respostas:['C','E','E','E','E','','C','C','C','C','C','']},12),
          semCampo:provaLiquido({acertos:6},12),
          vazio:provaLiquido({acertos:0,respostas:new Array(12).fill('')},12)})""")
        print('   com respostas (2 brancos): %s · sem o campo (prova antiga): %s · tudo em branco: %s'
              %(r['comBranco'],r['semCampo'],r['vazio']))
        assert r['comBranco']==2
        assert r['semCampo']==0      # prova antiga sem respostas: assume tudo marcado
        assert r['vazio']==0         # e nao -12
        print('   OK\n')

        print('=== G) refacao compara liquido contra liquido ===')
        r=await page.evaluate("""async(padrao)=>{
          (%s)(padrao);
          simGeralCorrigir();                      // guarda a prova (1a tentativa)
          await new Promise(r=>setTimeout(r,400));
          const id=db.provas[0].id;
          const t1=db.provas[0].tentativas[0];
          window.confirm=()=>true;
          provaRefazer(id);
          // 2a tentativa: acerta 8, erra 2, deixa 2 em branco -> liquido +6
          simGeralActive.questoes.forEach((q,i)=>{
            if(i<8)q.userAnswer='C'; else if(i<10)q.userAnswer='E';});
          simGeralActive.tempoGastoSec=300;
          const html=simGeralResultsHTML();
          return {brancosT1:t1.respostas.filter(x=>!x).length,
                  acertosT1:t1.acertos,html};}"""%MONTA,PADRAO)
        print('   tentativa 1 guardada: %s acertos, %s respostas em branco'
              %(r['acertosT1'],r['brancosT1']))
        assert r['brancosT1']==2 and r['acertosT1']==6
        h=r['html']
        ant=num(h,r'líq\. ([+-]?\d+)')
        delta=num(h,r'([+-]?\d+) no líquido')
        print('   antes: líq. %s · agora: %s · delta %s'%(ant,num(h,r'([+-]?\d+) líquidos'),delta))
        assert ant=='+2', ant          # e nao 0, que era a conta com branco punido
        assert num(h,r'([+-]?\d+) líquidos')=='+6'
        assert delta=='+4', delta
        print('   OK\n')

        print('=== H) o historico do assunto tambem parou de punir branco ===')
        r=await page.evaluate("""()=>{
          const pf=simFindSub('s1').simStats.porFormato.certoerrado;
          const f=simResumoFormato('certoerrado',pf);
          // historico antigo, gravado antes deste campo: assume tudo marcado
          const velho=simResumoFormato('certoerrado',{tentativas:1,questoes:6,acertos:1});
          return {questoes:pf.questoes,acertos:pf.acertos,marcadas:pf.marcadas,
                  erros:f.erros,saldo:f.saldo,brancos:f.brancos,
                  velhoErros:velho.erros,velhoSaldo:velho.saldo,velhoBrancos:velho.brancos};}""")
        print('   s1: %s itens · %s marcados · %s acertos -> %s erros · saldo %s · %s em branco'
              %(r['questoes'],r['marcadas'],r['acertos'],r['erros'],r['saldo'],r['brancos']))
        assert r['marcadas']==5 and r['questoes']==6
        assert r['erros']==4 and r['saldo']==-3 and r['brancos']==1
        print('   historico sem o campo (antes desta versao): %s erros · saldo %s · %s em branco'
              %(r['velhoErros'],r['velhoSaldo'],r['velhoBrancos']))
        assert r['velhoErros']==5 and r['velhoSaldo']==-4 and r['velhoBrancos']==0
        print('   OK\n')

        print('=== I) simulado de fora conta como tudo marcado ===')
        r=await page.evaluate("""()=>{
          const sub=simFindSub('s2');
          const antes=sub.simStats.porFormato.certoerrado.marcadas;
          const pf=sub.simStats.porFormato.certoerrado;
          pf.tentativas++; pf.questoes+=20; pf.acertos+=12;
          if(pf.marcadas==null)pf.marcadas=pf.questoes; pf.marcadas+=20;
          const f=simResumoFormato('certoerrado',pf);
          return {antes,depois:pf.marcadas,questoes:pf.questoes,brancos:f.brancos,saldo:f.saldo};}""")
        print('   marcadas %s -> %s de %s itens · em branco: %s · saldo %s'
              %(r['antes'],r['depois'],r['questoes'],r['brancos'],r['saldo']))
        assert r['brancos']==1   # so o branco do simulado interno; os 20 de fora contam marcados
        assert r['saldo']==5+12-8
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
