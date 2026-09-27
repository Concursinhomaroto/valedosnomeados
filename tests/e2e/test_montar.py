# -*- coding: utf-8 -*-
# O painel de erros diagnosticava e parava ali. Agora o diagnostico vira caderno:
# saca das provas guardadas e monta um sob medida, sem guardar questao nova.
import asyncio, sys
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

        print('=== A) sem prova guardada, a secao nem aparece ===')
        r=await page.evaluate("()=>({html:montarHTML(),acervo:montarAcervo().length})")
        print('   acervo: %s · secao renderizada: %s'%(r['acervo'],bool(r['html'])))
        assert r['acervo']==0 and r['html']==''
        print('   OK\n')

        print('=== B) uma prova de 12: acervo enche, sem repetida ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(12);
          simColarIniciar(false);
          // erra os 6 primeiros: no lote os assuntos alternam, entao os erros caem
          // metade em cada um — e e disso que o teste do gargalo precisa
          simGeralActive.questoes.forEach((q,i)=>{
            q.userAnswer=(i<6)?(q.correta==='C'?'E':'C'):q.correta;});
          simGeralActive.tempoGastoSec=600;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const a=montarAcervo();
          return {acervo:a.length,errou:a.filter(x=>x.errou).length,
                  temSecao:!!montarHTML()};}"""%LOTE,0)
        print('   acervo: %s questões · erradas: %s · seção aparece: %s'
              %(r['acervo'],r['errou'],r['temSecao']))
        assert r['acervo']==12 and r['errou']==6 and r['temSecao']
        print('   OK\n')

        print('=== C) "so o que eu errei" monta so com as erradas ===')
        r=await page.evaluate("""()=>{
          document.getElementById('montar-modo').value='errei';
          document.getElementById('montar-qtd').value='20';
          montarAgora();
          const nova=db.provas[0];
          const orig=db.provas[1];
          const origQs=provaQuestoes(orig);
          const errRespostas=(orig.tentativas[0].respostas||[])
            .map((r,i)=>r&&r!==origQs[i].correta?origQs[i].questao:null).filter(Boolean);
          return {provas:db.provas.length,n:nova.questoes.length,
                  treino:!!nova.treino,origem:nova.origem,tentativas:nova.tentativas.length,
                  todasErradas:nova.questoes.every(q=>errRespostas.includes(q.questao)),
                  semResposta:nova.questoes.every(q=>q.userAnswer===undefined),
                  semNota:nova.questoes.every(q=>q.minhaNota===undefined)};}""")
        print('   montou %s itens (pediu 20, o pool tinha 6) · treino: %s · origem: %r'
              %(r['n'],r['treino'],r['origem']))
        print('   todas eram erradas: %s · caderno limpo (sem resposta/nota): %s'
              %(r['todasErradas'],r['semResposta'] and r['semNota']))
        assert r['provas']==2 and r['n']==6 and r['treino'] and r['origem']=='montada'
        assert r['tentativas']==0 and r['todasErradas'] and r['semResposta'] and r['semNota']
        print('   OK\n')

        print('=== D) prova montada NAO conta, nem na primeira vez ===')
        r=await page.evaluate("""async()=>{
          const antes=JSON.stringify([simFindSub('s1').simStats,simFindSub('s2').simStats]);
          window.confirm=()=>true;
          provaRefazer(db.provas[0].id);
          const meta={refazendo:!!simGeralActive.refazendo,num:simGeralActive.tentativaNum};
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=200;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const depois=JSON.stringify([simFindSub('s1').simStats,simFindSub('s2').simStats]);
          return {...meta,intacto:antes===depois,
                  tentativas:db.provas.find(p=>p.treino).tentativas.length};}""")
        print('   1ª vez já entra como refação: %s (tentativa nº %s)'%(r['refazendo'],r['num']))
        print('   estatísticas intactas: %s · tentativa registrada: %s'
              %(r['intacto'],r['tentativas']))
        assert r['refazendo'] and r['num']==1 and r['intacto'] and r['tentativas']==1
        print('   questão que você já viu não pode contar de novo')
        print('   OK\n')

        print('=== E) "pelo gargalo" usa a classificacao dos erros ===')
        r=await page.evaluate("""()=>{
          // classifica: PCR vira gargalo de conteudo, Choque septico de atencao
          const orig=db.provas.find(p=>!p.treino);
          provaQuestoes(orig).forEach((q,i)=>{
            const resp=orig.tentativas[0].respostas[i];
            if(!resp||resp===q.correta)return;
            provaMarcar(orig,i,{...q,motivo:(q.subName==='PCR')?'conteudo':'atencao'});});
          const porConteudo=[...montarAssuntosDoGargalo('conteudo')];
          const porAtencao=[...montarAssuntosDoGargalo('atencao')];
          return {porConteudo,porAtencao,
                  poolConteudo:montarPool('gargalo','conteudo').length,
                  poolAtencao:montarPool('gargalo','atencao').length};}""")
        print('   gargalo "Não sabia": %s (%s questões)'%(r['porConteudo'],r['poolConteudo']))
        print('   gargalo "Li errado": %s (%s questões)'%(r['porAtencao'],r['poolAtencao']))
        assert r['porConteudo']==['PCR'] and r['porAtencao']==['Choque septico']
        assert r['poolConteudo']>0 and r['poolAtencao']>0
        print('   OK\n')

        print('=== F) montar pelo gargalo so traz o assunto certo ===')
        r=await page.evaluate("""()=>{
          renderSimGeralScreen();
          document.getElementById('montar-modo').value='gargalo';
          renderSimGeralScreen();
          document.getElementById('montar-modo').value='gargalo';
          document.getElementById('montar-motivo').value='conteudo';
          document.getElementById('montar-qtd').value='20';
          montarAgora();
          const nova=db.provas[0];
          return {n:nova.questoes.length,
                  assuntos:[...new Set(nova.questoes.map(q=>q.subName))]};}""")
        print('   montou %s itens · assuntos: %s'%(r['n'],r['assuntos']))
        assert r['assuntos']==['PCR'] and r['n']>0
        print('   OK\n')

        print('=== G) item fora da conta nao volta pro caderno ===')
        r=await page.evaluate("""()=>{
          const orig=db.provas.find(p=>!p.treino);
          const antes=montarAcervo().length;
          provaMarcar(orig,0,{...provaQuestoes(orig)[0],motivo:'datado'});
          const depois=montarAcervo().length;
          provaMarcar(orig,0,{...provaQuestoes(orig)[0],motivo:''});
          return {antes,depois};}""")
        print('   acervo: %s -> %s ao marcar um item como desatualizado'%(r['antes'],r['depois']))
        assert r['depois']==r['antes']-1
        print('   questão quebrada não merece ser reservida')
        print('   OK\n')

        print('=== H) a mesma questao em duas provas entra uma vez so ===')
        r=await page.evaluate("""async(x)=>{
          const antes=montarAcervo().length;
          (%s)(12);                       // mesmo lote, de novo
          simColarIniciar(false);
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=100;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          return {antes,depois:montarAcervo().length,provas:db.provas.length};}"""%LOTE,0)
        print('   %s provas no banco · acervo: %s -> %s'
              %(r['provas'],r['antes'],r['depois']))
        assert r['depois']==r['antes'], 'nao podia ter duplicado'
        print('   OK\n')

        print('=== I) filtro vazio avisa em vez de montar prova vazia ===')
        r=await page.evaluate("""()=>{
          montarSel=new Set();
          document.getElementById('montar-modo').value='assunto';
          renderSimGeralScreen();
          document.getElementById('montar-modo').value='assunto';
          const antes=db.provas.length;
          montarAgora();
          return {antes,depois:db.provas.length,pool:montarPool('assunto').length};}""")
        print('   pool vazio: %s · provas: %s (era %s)'%(r['pool'],r['depois'],r['antes']))
        assert r['pool']==0 and r['depois']==r['antes']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
