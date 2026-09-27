# -*- coding: utf-8 -*-
# O painel Controle de Erros lia SO a lista viva de provas. Entao ele encolhia sozinho:
# cada prova que envelhecia e saia da lista levava junto as classificacoes que voce
# clicou uma a uma, ate o painel amanhecer dizendo "nenhum erro classificado ainda".
# O banco nao salvava isso de proposito (motivo e da TENTATIVA, nao da questao) e o
# arquivo nao guardava. Agora o esqueleto guarda, esparso.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) o painel some quando a prova sai? (era esse o defeito) ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',10,'A');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.tentativas=[{data:new Date().toISOString(),
            respostas:pr.questoes.map((q,i)=>i<4?(q.correta==='C'?'E':'C'):q.correta),
            acertos:6,tempoGastoSec:600}];
          // voce classifica os 4 erros, um clique cada
          pr.questoes[0].motivo='conteudo';
          pr.questoes[1].motivo='atencao';
          pr.questoes[2].motivo='atencao';
          pr.questoes[3].motivo='chute';
          const antes=motivosAgregado();
          // a prova envelhece e sai da lista
          acervoGuardarProva(pr); provaArquivar(pr);
          db.provas=[];
          const depois=motivosAgregado();
          return {antes:{cls:antes.classificadas,err:antes.erradas,tot:antes.tot},
                  depois:{cls:depois.classificadas,err:depois.erradas,tot:depois.tot},
                  assuntos:Object.keys(depois.porAssunto)};}""")
        print('   com a prova na lista:  %s classificadas · %s erradas · %s'
              %(r['antes']['cls'],r['antes']['err'],r['antes']['tot']))
        print('   depois que ela saiu:   %s classificadas · %s erradas · %s'
              %(r['depois']['cls'],r['depois']['err'],r['depois']['tot']))
        assert r['antes']['cls']==4 and r['antes']['err']==4
        assert r['depois']['cls']==4, 'as classificações sumiram com a prova'
        assert r['depois']['err']==4
        assert r['depois']['tot']==r['antes']['tot']
        assert r['assuntos']==['Choque septico'], r['assuntos']
        print('   o painel continua inteiro, com o assunto de cada uma')
        print('   OK\n')

        print('=== B) o esqueleto so guarda o que voce marcou ===')
        r=await page.evaluate("""()=>{
          const a=db.provasArquivo[0];
          return {itens:(a.chaves||[]).length,
                  marcacoes:Object.keys(a.marcacoes||{}).length,
                  exemplo:a.marcacoes['1'],
                  bytes:JSON.stringify(a.marcacoes).length};}""")
        print('   prova de %s itens, %s marcações guardadas (%s bytes)'
              %(r['itens'],r['marcacoes'],r['bytes']))
        print('   exemplo: %s'%r['exemplo'])
        assert r['marcacoes']==4 and r['exemplo']['m']=='atencao'
        assert r['exemplo']['s']=='Choque septico'
        print('   esparso: 4 entradas numa prova de 10, não 10')
        print('   OK\n')

        print('=== C) ao reabrir a arquivada, a classificacao esta na tela ===')
        r=await page.evaluate("""()=>{
          provaRevisarArquivada(db.provasArquivo[0].id);
          const qs=simGeralActive.questoes;
          const h=document.getElementById('simgeral-content').innerHTML;
          return {motivos:qs.map(q=>q.motivo||''),
                  aceso:(h.match(/sim-motivo-btn sim-motivo-on|motivo-on/g)||[]).length>0,
                  arquivadaId:simGeralActive.arquivadaId===db.provasArquivo[0].id};}""")
        print('   motivos remontados: %s'%[m for m in r['motivos'] if m])
        assert r['motivos'][:4]==['conteudo','atencao','atencao','chute']
        assert r['arquivadaId']
        print('   OK\n')

        print('=== D) classificar OLHANDO a arquivada tambem grava ===')
        r=await page.evaluate("""()=>{
          const id=db.provasArquivo[0].id;
          simMotivoSalvar(5,'chute');            // item que estava sem classificação
          const a=()=>(db.provasArquivo||[]).find(x=>x.id===id);
          const dep1=Object.keys(a().marcacoes).length;
          const cls1=motivosAgregado().classificadas;
          simMotivoSalvar(5,'chute');            // clica de novo: desmarca
          const dep2=Object.keys(a().marcacoes).length;
          const cls2=motivosAgregado().classificadas;
          return {dep1,cls1,dep2,cls2,
                  gravado:a().marcacoes['5']===undefined};}""")
        print('   classifiquei o item 6: %s marcações, painel com %s'%(r['dep1'],r['cls1']))
        print('   cliquei de novo (desmarca): %s marcações, painel com %s'%(r['dep2'],r['cls2']))
        assert r['dep1']==5 and r['cls1']==5
        assert r['dep2']==4 and r['cls2']==4 and r['gravado']
        print('   o clique numa prova antiga não cai mais no vazio')
        print('   OK\n')

        print('=== E) item quebrado desloca a tela, mas nao a gravacao ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',6,'E');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.questoes[1].motivo='datado';        // quebrado: nunca entra no banco
          pr.tentativas=[{data:new Date().toISOString(),
            respostas:pr.questoes.map(q=>q.correta),acertos:6,tempoGastoSec:60}];
          acervoGuardarProva(pr); provaArquivar(pr);
          db.provas=[];
          provaRevisarArquivada(db.provasArquivo[0].id);
          const naTela=simGeralActive.questoes.length;
          simMotivoSalvar(3,'atencao');          // 4º da TELA = 5º do esqueleto
          const m=db.provasArquivo[0].marcacoes;
          return {naTela, chaves:db.provasArquivo[0].chaves.length,
                  chaves_marcadas:Object.keys(m).sort(),
                  oQuarto:m['4'], mapa:db.provasArquivo[0]._mapa};}""")
        print('   esqueleto: %s itens · na tela: %s (1 quebrado ficou fora)'
              %(r['chaves'],r['naTela']))
        print('   mapa tela→original: %s'%r['mapa'])
        print('   marcações gravadas nos índices: %s'%r['chaves_marcadas'])
        assert r['naTela']==5 and r['chaves']==6
        assert r['oQuarto'] and r['oQuarto']['m']=='atencao'
        print('   gravou no índice 4 (o original), não no 3 (o da tela)')
        print('   OK\n')

        print('=== F) o mapa de sessao nao sobe pro servidor ===')
        r=await page.evaluate("""async()=>{
          window.__updateCalls=[];
          provarqSalvar(true);
          await new Promise(r=>setTimeout(r,200));
          const c=window.__updateCalls.filter(x=>/vdn_provas_arq/.test(x.path));
          const noServidor=window.__root.users.TEST_UID_LEO.vdn_provas_arq||[];
          return {gravou:c.length,
                  temMapa:JSON.stringify(noServidor).includes('_mapa'),
                  temMarcacoes:!!(noServidor[0]||{}).marcacoes};}""")
        print('   gravou no nó: %s · levou marcações: %s · levou o _mapa de sessão: %s'
              %(r['gravou'],r['temMarcacoes'],r['temMapa']))
        assert r['gravou']==1 and r['temMarcacoes'] and not r['temMapa']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
