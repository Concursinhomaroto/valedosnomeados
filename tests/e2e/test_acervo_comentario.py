# -*- coding: utf-8 -*-
# O que viaja com a questao quando a prova sai da lista. Regra: sai o que pertence
# AQUELA TENTATIVA (o que voce marcou, por que errou, o grifo), fica o que pertence a
# QUESTAO — inclusive o que e seu: comentario, fonte, o trecho da norma que voce mandou
# buscar, e a nota que voce escreveu com as suas palavras.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_acervo import seed, QS

CHEIA = """(tag)=>({
  questao:tag+' o servidor deve utilizar os avancos tecnicos ao seu alcance',
  correta:'C',formato:'certoerrado',
  textoApoio:'Texto de apoio do caderno.',
  explicacao:'Certo. A vedacao e por omissao. GUARDE: nao se atualizar e falta etica.',
  fonte:'Lei Estadual 6.754/2006, art. 12',
  apoioWeb:[{titulo:'Lei 6.754/2006',url:'https://gcs2.sefaz.al.gov.br/lei6754',
             trecho:'Art. 12. Sao deveres do servidor...'}],
  minhaNota:'Errei porque li "pode" onde estava "deve". Ler o verbo duas vezes.',
  marcas:[{ini:0,fim:8,cor:'amarelo'}],
  motivo:'atencao', userAnswer:'E', _histId:'h1', _qIdxInHist:3, problematico:false,
  subId:'sE1',subName:'Choque septico',kingdomId:'kEnf',kingdomName:'Enfermagem',kingdomIcon:'💉'})"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');window.confirm=()=>true;return true;}")
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');return true;}",QS)
        await page.evaluate("(f)=>{window.CHEIA=eval('('+f+')');return true;}",CHEIA)

        print('=== A) o comentario, a fonte, o trecho e a sua nota vao pro banco ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const q=CHEIA('A');
          const id=provaGuardarLote([q],{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.tentativas=[{data:new Date().toISOString(),respostas:['E'],acertos:0,tempoGastoSec:9}];
          acervoGuardarProva(pr);
          const g=db.acervo[0];
          return {ficou:{explicacao:!!g.explicacao,fonte:!!g.fonte,
                         apoioWeb:(g.apoioWeb||[]).length,minhaNota:!!g.minhaNota,
                         textoApoio:!!g.textoApoio,alternativasOuGabarito:!!g.correta},
                  saiu:{userAnswer:g.userAnswer,motivo:g.motivo,marcas:g.marcas,
                        histId:g._histId,problematico:g.problematico},
                  carimbo:g.ultimoResultado,
                  comentario:g.explicacao, nota:g.minhaNota};}""")
        print('   ficou: %s'%r['ficou'])
        print('   saiu:  %s'%r['saiu'])
        print('   comentário: "%s"'%r['comentario'][:60])
        print('   sua nota:   "%s"'%r['nota'][:60])
        assert all(r['ficou'].values()), r['ficou']
        assert all(v is None for v in r['saiu'].values()), r['saiu']
        assert r['carimbo']=='X'
        print('   OK\n')

        print('=== B) a mesma questao, comentada depois, melhora a que ja estava la ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const crua=CHEIA('B');
          delete crua.explicacao; delete crua.fonte; delete crua.apoioWeb; delete crua.minhaNota;
          acervoGuardarProva({questoes:[crua],tentativas:[]});
          const antes={...db.acervo[0]};
          // semanas depois, a mesma questao volta num caderno ja comentado
          const novas=acervoGuardarProva({questoes:[CHEIA('B')],
            tentativas:[{respostas:['E'],acertos:0}]});
          const g=db.acervo[0];
          return {antesTinha:{expl:!!antes.explicacao,nota:!!antes.minhaNota,resp:antes.ultimoResultado},
                  novasGuardadas:novas, total:db.acervo.length,
                  agora:{expl:!!g.explicacao,fonte:!!g.fonte,
                         apoio:(g.apoioWeb||[]).length,nota:!!g.minhaNota,resp:g.ultimoResultado}};}""")
        print('   1ª vez (sem comentário): %s'%r['antesTinha'])
        print('   2ª vez (comentada): guardou %s nova, banco com %s'
              %(r['novasGuardadas'],r['total']))
        print('   agora: %s'%r['agora'])
        assert r['novasGuardadas']==0 and r['total']==1
        assert all([r['agora']['expl'],r['agora']['fonte'],r['agora']['nota']])
        assert r['agora']['apoio']==1 and r['agora']['resp']=='X'
        print('   não duplicou, e o comentário que teria se perdido entrou na que já estava lá')
        print('   OK\n')

        print('=== C) nada e sobrescrito: so preenche o que falta ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const boa=CHEIA('C');
          boa.explicacao='COMENTÁRIO BOM que já estava no banco.';
          boa.minhaNota='MINHA NOTA original.';
          acervoGuardarProva({questoes:[boa],tentativas:[]});
          const ruim=CHEIA('C');
          ruim.explicacao='comentário pior que chegou depois';
          ruim.minhaNota='nota pior';
          acervoGuardarProva({questoes:[ruim],tentativas:[]});
          const g=db.acervo[0];
          return {expl:g.explicacao,nota:g.minhaNota,total:db.acervo.length};}""")
        print('   comentário: "%s"'%r['expl'])
        print('   nota:       "%s"'%r['nota'])
        assert r['expl'].startswith('COMENTÁRIO BOM') and r['nota'].startswith('MINHA NOTA')
        assert r['total']==1
        print('   o que já estava lá manda — enriquecer não é sobrescrever')
        print('   OK\n')

        print('=== D) prova montada leva comentario, fonte e a sua nota ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[];
          const qs=[];
          for(let i=0;i<6;i++){const q=CHEIA('D'+i); qs.push(q);}
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.tentativas=[{respostas:qs.map(()=>'E'),acertos:0,tempoGastoSec:60}];
          montarSelMat=new Set(['kEnf']);
          document.getElementById('provas-content').innerHTML=montarHTML();
          document.getElementById('montar-modo').value='materia';
          document.getElementById('montar-qtd').value='4';
          montarAgora();
          const nova=db.provas[0];
          const q0=nova.questoes[0];
          return {itens:nova.questoes.length,
                  comComentario:nova.questoes.filter(x=>x.explicacao).length,
                  comFonte:nova.questoes.filter(x=>x.fonte).length,
                  comApoio:nova.questoes.filter(x=>(x.apoioWeb||[]).length).length,
                  comNota:nova.questoes.filter(x=>x.minhaNota).length,
                  semResposta:nova.questoes.every(x=>!x.userAnswer),
                  semMotivo:nova.questoes.every(x=>!x.motivo),
                  semGrifo:nova.questoes.every(x=>!x.marcas),
                  semCarimbo:nova.questoes.every(x=>x.ultimoResultado===undefined)};}""")
        print('   caderno de %s itens · com comentário: %s · fonte: %s · trecho: %s · sua nota: %s'
              %(r['itens'],r['comComentario'],r['comFonte'],r['comApoio'],r['comNota']))
        print('   sem a resposta da vez passada: %s · sem motivo: %s · sem grifo: %s'
              %(r['semResposta'],r['semMotivo'],r['semGrifo']))
        assert r['itens']==4 and r['comComentario']==4 and r['comFonte']==4
        assert r['comApoio']==4 and r['comNota']==4
        assert r['semResposta'] and r['semMotivo'] and r['semGrifo'] and r['semCarimbo']
        print('   OK\n')

        print('=== E) a nota e o trecho nao aparecem ANTES de corrigir ===')
        r=await page.evaluate("""()=>{
          provaRefazer(db.provas[0].id);
          const durante=document.getElementById('simgeral-content').innerHTML;
          simGeralActive.questoes.forEach(q=>{q.userAnswer='C';});
          simGeralActive.tempoGastoSec=30;
          simGeralCorrigir();
          const depois=document.getElementById('simgeral-content').innerHTML;
          return {durante:{nota:/MINHA NOTA|minhaNota|sim-nota-txt/.test(durante),
                           fonte:/fonte-web/.test(durante),
                           comentario:/sim-explain/.test(durante)},
                  depois:{nota:/Ler o verbo duas vezes/.test(depois),
                          fonte:/fonte-web/.test(depois),
                          comentario:/sim-explain/.test(depois)}};}""")
        print('   durante a prova: %s'%r['durante'])
        print('   depois de corrigir: %s'%r['depois'])
        assert not any(r['durante'].values()), 'vazou resposta durante a prova'
        assert all(r['depois'].values())
        print('   durante a prova não vaza nada; depois, tudo volta — inclusive o que você escreveu')
        print('   OK\n')

        print('=== F) item quebrado continua fora, com comentario e tudo ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];
          const q=CHEIA('F'); q.motivo='datado';
          const novas=acervoGuardarProva({questoes:[q],tentativas:[]});
          return {novas,banco:db.acervo.length};}""")
        print('   questão marcada como desatualizada: %s foi pro banco'%r['novas'])
        assert r['novas']==0 and r['banco']==0
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
