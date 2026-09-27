# -*- coding: utf-8 -*-
# Passo 2 do plano do Banco de Questoes: tags, favorita, status, contadores de verdade
# (vezesRespondida/acertos/erros/ultimaVezEm), dificuldadeAferida, criadaEm, origem.
#
# _resp (C/X da ultima tentativa) virou ultimoResultado — MESMA semantica, so o nome —
# porque "so o que eu errei" depende dele pra questao sem prova viva, e trocar por um
# agregado ("errou alguma vez", "erra mais do que acerta") mudaria o preset sem avisar.
# Os contadores sao ADITIVOS, do lado, pros filtros novos (faixa de acerto, nunca
# respondida, dificuldade aferida) — nao substituem o papel do ultimoResultado.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

def prova(qs,fmt='certoerrado'):
    return {'questoes':qs,'tentativas':[]}

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) "so o que eu errei" continua lendo o ULTIMO resultado, nao um agregado ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'M');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=()=>provaAchar(id);
          // 1ª vez: errou. 2ª vez: acertou. Se o preset lesse "erros>0", continuaria
          // aparecendo em "so o que eu errei" mesmo tendo acertado da última vez.
          pr().tentativas=[{respostas:[pr().questoes[0].correta==='C'?'E':'C'],acertos:0,tempoGastoSec:5}];
          acervoGuardarProva(pr()); db.provas=[];
          const depoisDoErro=montarPool('errei').length;
          const id2=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id2).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id2)); db.provas=[];
          const depoisDoAcerto=montarPool('errei').length;
          const g=db.acervo[0];
          return {depoisDoErro,depoisDoAcerto,
                  ultimoResultado:g.ultimoResultado,
                  vezesRespondida:g.vezesRespondida,acertos:g.acertos,erros:g.erros};}""")
        print('   depois de errar: %s em "só o que eu errei" · depois de acertar: %s'
              %(r['depoisDoErro'],r['depoisDoAcerto']))
        print('   ultimoResultado: %s · vezesRespondida: %s (acertos %s, erros %s)'
              %(r['ultimoResultado'],r['vezesRespondida'],r['acertos'],r['erros']))
        assert r['depoisDoErro']==1, 'errou e não apareceu no preset'
        assert r['depoisDoAcerto']==0, 'acertou da última vez e continuou marcado como erro'
        assert r['ultimoResultado']=='C'
        assert r['vezesRespondida']==2 and r['acertos']==1 and r['erros']==1
        print('   o preset segue sendo "a última vez", e os contadores somam as duas')
        print('   OK\n')

        print('=== B) resultado mais recente vence — não o primeiro que chegou ===')
        # Bug latente que o merge de _resp tinha (so preenchia se estivesse vazio, nunca
        # atualizava): duas provas com a MESMA questao, ordem de arquivamento importa.
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',1,'N');
          const id1=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id1).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}]; // acertou
          acervoGuardarProva(provaAchar(id1)); db.provas=[];
          const id2=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id2).tentativas=[{respostas:[qs[0].correta==='C'?'E':'C'],acertos:0,tempoGastoSec:5}]; // errou depois
          acervoGuardarProva(provaAchar(id2)); db.provas=[];
          return {ultimo:db.acervo[0].ultimoResultado,
                  acertos:db.acervo[0].acertos, erros:db.acervo[0].erros,
                  vezes:db.acervo[0].vezesRespondida};}""")
        print('   acertou, depois errou → ultimoResultado: %s (acertos %s, erros %s de %s)'
              %(r['ultimo'],r['acertos'],r['erros'],r['vezes']))
        assert r['ultimo']=='X', 'o resultado mais antigo venceu o mais novo'
        assert r['acertos']==1 and r['erros']==1 and r['vezes']==2
        print('   OK\n')

        print('=== C) dificuldadeAferida só existe com amostra, e reflete a taxa real ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'D');
          const resultados=['C','C','E','C','E','E','E'];   // 3 no minimo, depois 4/7
          let ultimaId=null;
          resultados.forEach((res,i)=>{
            const id=provaGuardarLote(qs,{formato:'certoerrado'});
            const marcada=(res==='C')?qs[0].correta:(qs[0].correta==='C'?'E':'C');
            provaAchar(id).tentativas=[{respostas:[marcada],acertos:res==='C'?1:0,tempoGastoSec:5}];
            acervoGuardarProva(provaAchar(id)); db.provas=[];
            ultimaId=i;
          });
          const g=db.acervo[0];
          return {vezes:g.vezesRespondida,acertos:g.acertos,erros:g.erros,
                  dificuldade:g.dificuldadeAferida};}""")
        print('   %s respostas (%s acertos, %s erros = %.0f%%) → dificuldadeAferida: %s'
              %(r['vezes'],r['acertos'],r['erros'],100*r['acertos']/r['vezes'],r['dificuldade']))
        assert r['vezes']==7 and r['acertos']==3 and r['erros']==4
        assert r['dificuldade']=='media', 'taxa de 43% cai na faixa media (>=40% e <75%)'
        print('   OK\n')

        print('=== D) menos que a amostra mínima, fica null (não chuta com 1 resposta) ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kPt','Português','📖','sP1','Crase',1,'S');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id));
          return {dificuldade:db.acervo[0].dificuldadeAferida,
                  minimo:ACERVO_DIFICULDADE_MIN_AMOSTRA};}""")
        print('   1 resposta só (mínimo é %s) → dificuldadeAferida: %s'
              %(r['minimo'],r['dificuldade']))
        assert r['dificuldade'] is None
        print('   OK\n')

        print('=== E) campos novos nascem no primeiro guardar, com os defaults certos ===')
        r=await page.evaluate("""(args)=>{
          const [tag]=args;
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,tag);
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id));   // so ao arquivar a questao entra no acervo
          const g=db.acervo[0];
          return {tags:g.tags,favorita:g.favorita,status:g.status,
                  criadaEm:!!g.criadaEm,origem:g.origem,
                  vezes:g.vezesRespondida,ultima:g.ultimaVezEm};}""",['E'])
        print('   tags=%s · favorita=%s · status=%s · origem=%s · criadaEm existe: %s'
              %(r['tags'],r['favorita'],r['status'],r['origem'],r['criadaEm']))
        assert r['tags']==[] and r['favorita']==False and r['status']=='ativa'
        assert r['criadaEm'] and r['origem']=='ia' and r['vezes']==0 and r['ultima'] is None
        print('   OK\n')

        print('=== F) tags/favorita/status são SEUS — não são tocados pela fusão de conteúdo ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',1,'F');
          const id1=provaGuardarLote(qs,{formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id1));
          const g=db.acervo[0];
          g.tags=['prova-x','revisar-depois']; g.favorita=true; g.status='revisar';
          // a mesma questão chega nova (ex.: comentada), como se fosse outra prova
          const id2=provaGuardarLote(qs.map(q=>({...q,explicacao:'Comentário novo.'})),{formato:'certoerrado'});
          provaAchar(id2).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id2));
          return {tags:g.tags,favorita:g.favorita,status:g.status,
                  ganhouComentario:!!g.explicacao,total:db.acervo.length};}""")
        print('   depois de fundir conteúdo novo: tags=%s · favorita=%s · status=%s'
              %(r['tags'],r['favorita'],r['status']))
        assert r['tags']==['prova-x','revisar-depois'] and r['favorita']==True and r['status']=='revisar'
        assert r['ganhouComentario'] and r['total']==1
        print('   sua organização sobrevive a qualquer atualização de conteúdo')
        print('   OK\n')

        print('=== G) montada carrega os contadores (útil pra ver durante o treino), mas não o resultado ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'G');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:[qs[0].correta==='C'?'E':'C'],acertos:0,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          montarSel=new Set(['sE1']);
          document.getElementById('provas-content').innerHTML='';
          showScreen('banco');
          document.getElementById('montar-modo').value='assunto';
          document.getElementById('montar-qtd').value='1';
          montarAgora();
          const nova=db.provas[0].questoes[0];
          return {vezesRespondida:nova.vezesRespondida,acertos:nova.acertos,erros:nova.erros,
                  semUltimoResultado:nova.ultimoResultado===undefined};}""")
        print('   copia na prova montada: vezesRespondida=%s (acertos %s, erros %s) · sem ultimoResultado: %s'
              %(r['vezesRespondida'],r['acertos'],r['erros'],r['semUltimoResultado']))
        assert r['vezesRespondida']==1 and r['erros']==1
        assert r['semUltimoResultado']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
