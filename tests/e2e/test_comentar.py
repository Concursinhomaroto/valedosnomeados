# -*- coding: utf-8 -*-
# O caderno da banca entra sem comentario nenhum: o gabarito oficial e uma letra, nao
# uma explicacao. Aqui a explicacao e escrita depois, com pesquisa por tras — e o
# gabarito e inegociavel, a explicacao justifica a letra, nunca discute com ela.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'chave-de-teste','tavilyApiKey':'tvly-teste',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

# dubles: o Gemini devolve comentario, o Tavily devolve material
MOCK = """()=>{
  window.__chamadas=[];
  window.callGeminiJSON=async(key,prompt,useSearch,maxOut)=>{
    window.__chamadas.push({prompt,useSearch});
    const n=(prompt.match(/^\\[\\d+\\] gabarito:/gm)||[]).length;
    const arr=[];
    for(let i=0;i<n;i++)arr.push({i,explicacao:'Porque a reposicao inicial e de 30 mL/kg.',
                                  fonte:'Surviving Sepsis Campaign, 2021'});
    return {json:arr};
  };
  window.buscarMaterial=async()=>({material:'MATERIAL DO TAVILY',fontes:[],consultas:[],diag:[],via:'tavily'});
  window.confirm=()=>true;
  return true;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")
        await page.evaluate(MOCK)

        print('=== A) prova de 10 sem comentario nenhum ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(10);
          simColarLote.forEach(q=>{q.explicacao='';});   // como vem do caderno da banca
          simColarIniciar(false);
          simGeralActive.questoes.forEach((q,i)=>{
            q.explicacao='';
            q.userAnswer=(i<4)?(q.correta==='C'?'E':'C'):q.correta;});
          simGeralActive.tempoGastoSec=300;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const pr=db.provas[0];
          return {sem:comentarPendentes(pr,'sem').length,
                  erradas:comentarPendentes(pr,'erradas').length,
                  botao:/Comentar \\(10\\)/.test(provasGuardadasHTML())};}"""%LOTE,0)
        print('   sem comentário: %s · erradas: %s · botão na lista: %s'
              %(r['sem'],r['erradas'],r['botao']))
        assert r['sem']==10 and r['erradas']==4 and r['botao']
        print('   OK\n')

        print('=== B) comentar a prova inteira, em lotes ===')
        r=await page.evaluate("""async()=>{
          await comentarProva(db.provas[0].id,'sem');
          const pr=db.provas[0];
          return {chamadas:window.__chamadas.length,
                  comentadas:provaQuestoes(pr).filter(q=>q.explicacao).length,
                  comFonte:provaQuestoes(pr).filter(q=>q.fonte).length,
                  pendentes:comentarPendentes(pr,'sem').length,
                  lote:COMENTAR_LOTE};}""")
        print('   %s chamadas ao modelo pra 10 questões (lote de %s)'%(r['chamadas'],r['lote']))
        print('   comentadas: %s · com fonte: %s · pendentes: %s'
              %(r['comentadas'],r['comFonte'],r['pendentes']))
        assert r['chamadas']==2 and r['comentadas']==10 and r['comFonte']==10
        assert r['pendentes']==0
        print('   OK\n')

        print('=== C) o prompt leva o gabarito e proibe discutir com ele ===')
        r=await page.evaluate("""()=>{
          const p=window.__chamadas[0].prompt;
          return {temGabarito:/\\[0\\] gabarito: [CE]/.test(p),
                  inegociavel:p.includes('INEGOCIÁVEL'),
                  qualParte:p.includes('QUAL parte da afirmação está incorreta'),
                  algarismo:p.includes('ALGARISMO'),
                  fonteAno:p.includes('COM O ANO'),
                  naoInventa:p.includes('Comentário inventado é pior do que campo vazio'),
                  semRepetir:p.includes('Se a sua explicação puder ser lida sem saber o gabarito'),
                  material:p.includes('MATERIAL DO TAVILY'),
                  buscaPropria:window.__chamadas[0].useSearch};}""")
        for k in ['temGabarito','inegociavel','qualParte','algarismo','fonteAno','naoInventa','semRepetir']:
            assert r[k], k
        print('   gabarito no prompt, marcado como inegociável: ok')
        print('   exige apontar a parte errada, algarismo, fonte com ano: ok')
        print('   proíbe comentário inventado e explicação que só repete o item: ok')
        print('   material do Tavily entrou: %s · busca própria do modelo desligada: %s'
              %(r['material'],not r['buscaPropria']))
        assert r['material'] and not r['buscaPropria']
        print('   OK\n')

        print('=== D) sem Tavily, ele liga a busca do proprio modelo ===')
        r=await page.evaluate("""async()=>{
          const key=db.tavilyApiKey; db.tavilyApiKey='';
          provaEscreverCampo(db.provas[0],0,'explicacao','');
          window.__chamadas=[];
          await comentarProva(db.provas[0].id,'sem');
          db.tavilyApiKey=key;
          return {useSearch:window.__chamadas[0].useSearch,
                  material:window.__chamadas[0].prompt.includes('MATERIAL DO TAVILY')};}""")
        print('   busca própria do modelo: %s · material do Tavily: %s'
              %(r['useSearch'],r['material']))
        assert r['useSearch'] and not r['material']
        print('   OK\n')

        print('=== E) item fora da conta nao e comentado ===')
        r=await page.evaluate("""()=>{
          const pr=db.provas[0];
          provaQuestoes(pr).forEach((q,i)=>provaEscreverCampo(pr,i,'explicacao',''));
          const antes=comentarPendentes(pr,'sem').length;
          provaMarcar(pr,0,{...provaQuestoes(pr)[0],motivo:'datado'});
          const depois=comentarPendentes(pr,'sem').length;
          provaMarcar(pr,0,{...provaQuestoes(pr)[0],motivo:''});
          return {antes,depois};}""")
        print('   pendentes: %s -> %s ao marcar um como desatualizado'%(r['antes'],r['depois']))
        assert r['depois']==r['antes']-1
        print('   não gasta cota explicando questão que já saiu da conta')
        print('   OK\n')

        print('=== F) sem chave do Gemini ele nem tenta ===')
        r=await page.evaluate("""async()=>{
          const k=db.geminiApiKey; db.geminiApiKey='';
          window.__chamadas=[];
          await comentarProva(db.provas[0].id,'sem');
          db.geminiApiKey=k;
          return {chamadas:window.__chamadas.length};}""")
        print('   chamadas: %s'%r['chamadas'])
        assert r['chamadas']==0
        print('   OK\n')

        print('=== G) lote que falha nao derruba os outros ===')
        r=await page.evaluate("""async()=>{
          provaQuestoes(db.provas[0]).forEach((q,i)=>provaEscreverCampo(db.provas[0],i,'explicacao',''));
          let n=0;
          window.callGeminiJSON=async(key,prompt)=>{
            n++;
            if(n===1)throw new Error('503 sobrecarregado');
            const c=(prompt.match(/^\\[\\d+\\] gabarito:/gm)||[]).length;
            return {json:Array.from({length:c},(_,i)=>({i,explicacao:'ok '+i,fonte:'Lei X, 2020'}))};
          };
          await comentarProva(db.provas[0].id,'sem');
          const pr=db.provas[0];
          return {comentadas:provaQuestoes(pr).filter(q=>q.explicacao).length,
                  pendentes:comentarPendentes(pr,'sem').length};}""")
        print('   1º lote falhou · comentadas: %s · ainda pendentes: %s'
              %(r['comentadas'],r['pendentes']))
        assert r['comentadas']==2 and r['pendentes']==8
        print('   o que deu certo fica guardado; o resto continua marcado pra tentar de novo')
        print('   OK\n')

        print('=== H) o comentario e so em lote — nao ha botao por questao ===')
        # Dois botoes em CADA questao poluiam a tela de resultado de uma prova de 120
        # itens. O comentario ficou onde ele e util: em lote, na lista de provas.
        r=await page.evaluate("""()=>{
          provaRevisar(db.provas[0].id);
          const h=document.getElementById('simgeral-content').innerHTML;
          return {porQuestao:(h.match(/comentarUma\\(/g)||[]).length,
                  lote:/Comentar \\(\\d+\\)/.test(provasGuardadasHTML()),
                  aindaExiste:typeof comentarUma==='function'};}""")
        print('   botões por questão: %s · botão em lote na lista de provas: %s'
              %(r['porQuestao'],r['lote']))
        assert r['porQuestao']==0 and r['lote'] and r['aindaExiste']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
