# -*- coding: utf-8 -*-
# Prova de 120 itens toca umas 40 matérias, e a quebra listava as 40 numa linha gorda
# cada. O que voce precisa ver — em que BLOCO do edital perdeu e quais assuntos doeram —
# ficava enterrado entre trinta linhas de 100%. Agora abre no bloco, lista so o que
# sangrou, e guarda o assunto-a-assunto atras de um clique.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Geral','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Um','priority':70,'studied':True}]}]}})

# 4 blocos do edital, 22 assuntos, 60 itens — o formato da prova de verdade.
MONTAR = """(x)=>{
  const blocos=[
    {id:'kEnf',nome:'Enfermagem',icone:'💊',assuntos:10},
    {id:'kPt', nome:'Português', icone:'📖',assuntos:5},
    {id:'kSus',nome:'Saúde Pública',icone:'⚕️',assuntos:4},
    {id:'kAl', nome:'Alagoas',    icone:'⚖️',assuntos:3}];
  const qs=[]; let n=0;
  blocos.forEach((b,bi)=>{
    for(let a=0;a<b.assuntos;a++){
      const sid=b.id+'-'+a;
      const qtd=(a%3)+1;                       // 1 a 3 itens por assunto
      for(let k=0;k<qtd;k++){
        n++;
        // Erra de proposito: o bloco 0 erra pouco, o 3 erra muito.
        const errou=((a+k+bi*2)%4)<bi;
        qs.push({subId:sid,subName:b.nome+' — assunto '+(a+1),
                 kingdomId:b.id,kingdomName:b.nome,kingdomIcon:b.icone,
                 questao:'Item '+n,correta:'C',userAnswer:errou?'E':'C'});
      }
    }
  });
  simGeralActive={questoes:qs,startedAt:Date.now()-100000,corrected:true,
                  formato:'certoerrado',nivel:'medio',tempoGastoSec:3600,limiteSec:0};
  return qs.length;}"""

def conta(h,cls):
    return h.count('class="%s"'%cls)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) a quebra abre no bloco do edital, nao no assunto ===')
        r=await page.evaluate("""(m)=>{
          const total=(eval('('+m+')'))(0);
          sgVerTodos=false;
          const h=simGeralResultsHTML();
          const nomes=[...h.matchAll(/class="sg-bloco">\\s*<span>[^ ]+ ([^<]+)</g)].map(x=>x[1]);
          const pcts=[...h.matchAll(/class="sg-bloco-num"[^>]*>(\\d+)\\/(\\d+) \\((\\d+)%\\)/g)]
                      .map(x=>({a:+x[1],t:+x[2],p:+x[3]}));
          const assuntos=new Set(simGeralActive.questoes.map(q=>q.subId)).size;
          return {total,assuntos,nomes,pcts,
                  blocos:(h.match(/class="sg-bloco"/g)||[]).length,
                  linhasTodos:(h.match(/sg-todos-linha/g)||[]).length};}""", MONTAR)
        print('   %s itens · %s assuntos · %s blocos na tela'%(r['total'],r['assuntos'],r['blocos']))
        for nome,pc in zip(r['nomes'],r['pcts']):
            print('   %-16s %s/%s (%s%%)'%(nome,pc['a'],pc['t'],pc['p']))
        assert r['assuntos']==22 and r['blocos']==4
        somaT=sum(x['t'] for x in r['pcts']); somaA=sum(x['a'] for x in r['pcts'])
        assert somaT==r['total'], (somaT,r['total'])
        print('   os 4 blocos somam os %s itens: nenhum assunto sumiu da conta'%somaT)
        pcts=[x['p'] for x in r['pcts']]
        assert pcts==sorted(pcts), pcts
        print('   pior bloco primeiro: %s'%pcts)
        assert r['linhasTodos']==0
        print('   as %s linhas de assunto NÃO aparecem por padrão'%r['assuntos'])
        print('   OK\n')

        print('=== B) so o que sangrou vira chip ===')
        r=await page.evaluate("""()=>{
          const h=simGeralResultsHTML();
          const bySub={};
          simGeralActive.questoes.forEach(q=>{
            const b=bySub[q.subId]=bySub[q.subId]||{a:0,t:0};
            b.t++; if(q.userAnswer===q.correta)b.a++;});
          const erraram=Object.values(bySub).filter(b=>b.a<b.t).length;
          const limpos=Object.values(bySub).filter(b=>b.a===b.t).length;
          return {erraram,limpos,
                  chips:(h.match(/class="sg-chip"/g)||[]).length,
                  cab:(h.match(/Onde você perdeu ponto — (\\d+) de (\\d+) assuntos/)||[]).slice(1),
                  temExcedente:/<span>\\+\\d+<\\/span>/.test(h)};}""")
        print('   assuntos com erro: %s · assuntos 100%%: %s'%(r['erraram'],r['limpos']))
        print('   cabeçalho: "%s de %s assuntos" · chips: %s · chip de excedente: %s'
              %(r['cab'][0],r['cab'][1],r['chips'],r['temExcedente']))
        assert int(r['cab'][0])==r['erraram'] and int(r['cab'][1])==r['erraram']+r['limpos']
        assert r['chips']==min(10,r['erraram'])+(1 if r['erraram']>10 else 0)
        assert r['limpos']>0, 'fixture fraco: sem assunto limpo, nada prova que ele foi omitido'
        print('   os %s assuntos sem erro ficaram fora da lista — é o que encurtou a tela'%r['limpos'])
        print('   OK\n')

        print('=== C) o assunto-a-assunto continua la, atras de um clique ===')
        r=await page.evaluate("""()=>{
          const fechado=simGeralResultsHTML();
          sgVerTodos=true;
          const aberto=simGeralResultsHTML();
          const linhas=[...aberto.matchAll(/sg-todos-linha"><span>[^ ]+ ([^<]+)<\\/span>\\s*<b[^>]*>(\\d+)\\/(\\d+)/g)]
                        .map(x=>({nome:x[1],a:+x[2],t:+x[3]}));
          sgVerTodos=false;
          return {linhas:linhas.length,
                  assuntos:new Set(simGeralActive.questoes.map(q=>q.subId)).size,
                  ordenado:linhas.every((l,i)=>i===0||(linhas[i-1].a/linhas[i-1].t)<=(l.a/l.t)),
                  primeiro:linhas[0],
                  fechadoMenor:fechado.length<aberto.length,
                  rotuloFechado:/ver os 22 assuntos um a um/.test(fechado),
                  rotuloAberto:/esconder os assuntos/.test(aberto)};}""")
        print('   com o clique: %s linhas, uma por assunto (são %s)'%(r['linhas'],r['assuntos']))
        print('   pior primeiro: %s · %s %s/%s'
              %(r['ordenado'],r['primeiro']['nome'],r['primeiro']['a'],r['primeiro']['t']))
        assert r['linhas']==r['assuntos'] and r['ordenado']
        assert r['fechadoMenor'] and r['rotuloFechado'] and r['rotuloAberto']
        print('   o botão diz quantos são, e o rótulo troca quando abre')
        print('   OK\n')

        print('=== D) o clique de verdade, na tela ===')
        r=await page.evaluate("""()=>{
          renderSimGeralScreen();
          const botao=()=>document.querySelector('#simgeral-content .sg-mais');
          const linhas=()=>document.querySelectorAll('#simgeral-content .sg-todos-linha').length;
          const antes=linhas(); const txtAntes=botao().textContent.trim();
          botao().click();
          const depois=linhas(); const txtDepois=botao().textContent.trim();
          botao().click();
          return {antes,depois,fechouDeNovo:linhas(),txtAntes,txtDepois,
                  blocos:document.querySelectorAll('#simgeral-content .sg-bloco').length};}""")
        print('   linhas: %s → clicou → %s → clicou → %s'%(r['antes'],r['depois'],r['fechouDeNovo']))
        print('   botão: "%s" → "%s"'%(r['txtAntes'],r['txtDepois']))
        assert r['antes']==0 and r['depois']==22 and r['fechouDeNovo']==0 and r['blocos']==4
        print('   OK\n')

        print('=== E) prova sem erro nenhum nao mostra lista de sangria ===')
        r=await page.evaluate("""()=>{
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          const h=simGeralResultsHTML();
          return {chips:(h.match(/class="sg-chip"/g)||[]).length,
                  verde:h.includes('Nenhum assunto ficou com erro'),
                  blocos:(h.match(/class="sg-bloco"/g)||[]).length,
                  cem:(h.match(/class="sg-bloco-num"[^>]*>\\d+\\/\\d+ \\(100%\\)/g)||[]).length};}""")
        print('   chips: %s · aviso verde: %s · blocos: %s (blocos em 100%%: %s)'
              %(r['chips'],r['verde'],r['blocos'],r['cem']))
        assert r['chips']==0 and r['verde'] and r['blocos']==4 and r['cem']==4
        print('   OK\n')

        print('=== F) item fora da conta sai da quebra tambem ===')
        r=await page.evaluate("""()=>{
          const q=simGeralActive.questoes;
          q.forEach(x=>{x.userAnswer=x.correta;});
          const alvo=q.find(x=>x.kingdomId==='kAl');
          const antes=(simGeralResultsHTML().match(/class="sg-bloco-num"[^>]*>(\\d+)\\/(\\d+)/g)||[]);
          alvo.motivo='datado';
          const depois=(simGeralResultsHTML().match(/class="sg-bloco-num"[^>]*>(\\d+)\\/(\\d+)/g)||[]);
          const soma=t=>t.reduce((n,x)=>n+Number(x.match(/\\/(\\d+)/)[1]),0);
          alvo.motivo='';
          return {antes:soma(antes),depois:soma(depois)};}""")
        print('   itens contados na quebra: %s → %s ao marcar 1 como desatualizado'
              %(r['antes'],r['depois']))
        assert r['depois']==r['antes']-1
        print('   a quebra usa a mesma base do placar — não conta item que saiu da conta')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
