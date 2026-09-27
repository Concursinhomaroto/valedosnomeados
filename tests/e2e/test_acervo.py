# -*- coding: utf-8 -*-
# Tres coisas que andam juntas: a prova ganha nome e numero (sete linhas dizendo "120
# questoes" nao identificam nada), a prova que sai da lista nao leva as questoes junto
# (questao nao envelhece — e o material que se quer manter), e o que sobrou vira um
# banco por materia pra treinar avulso.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed(extra=None):
    d={'studyNickname':'Leo',
       'kingdoms':[{'id':'kEnf','name':'Enfermagem','icon':'💉','color':'#22d3ee'},
                   {'id':'kSus','name':'Saúde Pública','icon':'⚕️','color':'#a78bfa'},
                   {'id':'kPt','name':'Português','icon':'📖','color':'#f472b6'}],
       'topics':{'kEnf':[{'id':'tE','name':'Urgencia','icon':'⚔️','subtopics':[
                    {'id':'sE1','name':'Choque septico','priority':70,'studied':True},
                    {'id':'sE2','name':'PCR','priority':70,'studied':True}]}],
                 'kSus':[{'id':'tS','name':'Leis','icon':'⚖️','subtopics':[
                    {'id':'sS1','name':'Lei 8080','priority':70,'studied':True}]}],
                 'kPt':[{'id':'tP','name':'Gramatica','icon':'✏️','subtopics':[
                    {'id':'sP1','name':'Crase','priority':70,'studied':True}]}]}}
    d.update(extra or {})
    return make_seed(d)

# fabrica questoes de uma materia
QS = """(kId,kNome,kIcone,subId,subNome,n,tag)=>{
  const arr=[];
  for(let i=0;i<n;i++)arr.push({questao:tag+' item '+i+' sobre '+subNome,correta:i%2?'C':'E',
    formato:'certoerrado',explicacao:'x',subId,subName:subNome,topicName:'T',
    kingdomId:kId,kingdomName:kNome,kingdomIcon:kIcone});
  return arr;}"""

async def main():
    async with async_playwright() as p2:
        b,page,errs=await setup_page(p2,seed())
        await page.evaluate("()=>{showScreen('provas');window.confirm=()=>true;return true;}")
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');return true;}",QS)

        print('=== A) o nome automatico ja diz a materia ===')
        r=await page.evaluate("""()=>{
          const soEnf=provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',10,'A'),
                                       {formato:'certoerrado'});
          const misto=provaGuardarLote(
            QS('kEnf','Enfermagem','💉','sE1','Choque septico',5,'B')
              .concat(QS('kPt','Português','📖','sP1','Crase',5,'B')),{formato:'certoerrado'});
          return {enf:provaRotulo(provaAchar(soEnf)), misto:provaRotulo(provaAchar(misto)),
                  numEnf:provaAchar(soEnf).num, numMisto:provaAchar(misto).num};}""")
        print('   %s (nº %s)'%(r['enf'],r['numEnf']))
        print('   %s (nº %s)'%(r['misto'],r['numMisto']))
        assert r['enf']=='Simulado 01 — Enfermagem'
        assert r['misto']=='Simulado 02 — Geral', r['misto']
        print('   matéria dominante quando passa de 70%; misturada vira "Geral"')
        print('   OK\n')

        print('=== B) renomear, e voltar pro automatico ===')
        r=await page.evaluate("""()=>{
          const id=db.provas[0].id;
          window.prompt=()=>'Simulado 2 - Enfermagem (Gran)';
          provaRenomear(id);
          const posto=provaRotulo(provaAchar(id));
          const naLista=provasGuardadasHTML().includes('Simulado 2 - Enfermagem (Gran)');
          window.prompt=()=>'   ';
          provaRenomear(id);
          const voltou=provaRotulo(provaAchar(id));
          window.prompt=()=>null;                 // cancelou
          provaRenomear(id);
          return {posto,naLista,voltou,intacto:provaRotulo(provaAchar(id))};}""")
        print('   virou "%s" · aparece na lista: %s'%(r['posto'],r['naLista']))
        print('   apagou o nome → "%s" · cancelar não mexe: %s'%(r['voltou'],r['intacto']==r['voltou']))
        assert r['posto']=='Simulado 2 - Enfermagem (Gran)' and r['naLista']
        assert r['voltou']=='Simulado 02 — Geral' and r['intacto']==r['voltou']
        print('   OK\n')

        print('=== C) estourar o teto tira a prova FEITA da lista, nao as questoes ===')
        # So prova ja feita e despejada: prova esperando e trabalho marcado, nao
        # historico, e tem teste proprio em test_prova_esperando.
        r=await page.evaluate("""()=>{
          db.provas.forEach(p=>{if(!(p.tentativas||[]).length){
            const qs=provaQuestoes(p);
            p.tentativas=[{data:new Date().toISOString(),
              respostas:qs.map(q=>q.correta),acertos:qs.length,tempoGastoSec:60}];
          }});
          const antes=db.provas.length;
          for(let i=0;i<PROVAS_MAX;i++){
            const id=provaGuardarLote(QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',6,'C'+i),
                                      {formato:'certoerrado'});
            provaAchar(id).tentativas=[{data:new Date().toISOString(),
              respostas:['C','C','C','C','C','C'],acertos:6,tempoGastoSec:60}];
          }
          provasAparar();
          return {antes, provas:db.provas.length, teto:PROVAS_MAX,
                  banco:(db.acervo||[]).length,
                  aindaTemAsPrimeiras:db.provas.some(p=>provaQuestoes(p)[0].questao.startsWith('A ')),
                  noBancoAsPrimeiras:(db.acervo||[]).some(q=>q.questao.startsWith('A '))};}""")
        print('   %s provas feitas → guardei mais %s → ficaram %s (teto %s)'
              %(r['antes'],r['teto'],r['provas'],r['teto']))
        print('   as 10 primeiras ainda numa prova: %s · no banco: %s (banco tem %s)'
              %(r['aindaTemAsPrimeiras'],r['noBancoAsPrimeiras'],r['banco']))
        assert r['provas']==r['teto']
        assert not r['aindaTemAsPrimeiras'] and r['noBancoAsPrimeiras']
        assert r['banco']>=10
        print('   OK\n')

        print('=== D) o banco nao guarda questao repetida ===')
        r=await page.evaluate("""()=>{
          const antes=db.acervo.length;
          const prova={questoes:db.acervo.slice(0,8).map(q=>({...q})),tentativas:[]};
          const novas=acervoGuardarProva(prova);
          return {antes,novas,depois:db.acervo.length};}""")
        print('   reenviei 8 questões que já estavam lá → %s novas (banco: %s → %s)'
              %(r['novas'],r['antes'],r['depois']))
        assert r['novas']==0 and r['depois']==r['antes']
        print('   mesmo caderno importado duas vezes ocupa uma vez só')
        print('   OK\n')

        print('=== E) "so o que eu errei" acha questao de prova que ja saiu ===')
        r=await page.evaluate("""()=>{
          // uma prova respondida: metade errada. Depois ela sai da lista.
          const qs=QS('kEnf','Enfermagem','💉','sE2','PCR',10,'E');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.tentativas=[{data:new Date().toISOString(),
            respostas:pr.questoes.map((q,i)=>i<5?(q.correta==='C'?'E':'C'):q.correta),
            acertos:5,tempoGastoSec:60}];
          const erradasComProva=montarPool('errei').filter(x=>x.q.questao.startsWith('E ')).length;
          // agora ela sai: guarda no banco e tira da lista
          const guardadas=acervoGuardarProva(pr);
          db.provas=db.provas.filter(p=>p.id!==id);
          const erradasSemProva=montarPool('errei').filter(x=>x.q.questao.startsWith('E ')).length;
          const carimbos=db.acervo.filter(q=>q.questao.startsWith('E ')).map(q=>q.ultimoResultado).sort();
          return {erradasComProva,erradasSemProva,guardadas,
                  carimbos:carimbos.join(''),
                  doBanco:montarAcervo().filter(x=>x.doBanco).length};}""")
        print('   com a prova na lista: %s erradas · depois que ela saiu: %s'
              %(r['erradasComProva'],r['erradasSemProva']))
        print('   carimbo gravado em cada uma: %s'%r['carimbos'])
        assert r['erradasComProva']==5 and r['erradasSemProva']==5
        assert r['carimbos']=='CCCCCXXXXX'
        print('   o que você errou continua sendo o que você errou, sem a prova de origem')
        print('   OK\n')

        print('=== F) montar por materia ===')
        r=await page.evaluate("""()=>{
          const ac=montarAcervo();
          const porMat={};
          ac.forEach(x=>{porMat[x.q.kingdomName]=(porMat[x.q.kingdomName]||0)+1;});
          montarSelMat=new Set(['kSus']);
          const pool=montarPool('materia');
          const soSus=pool.every(x=>x.q.kingdomId==='kSus');
          montarSelMat=new Set(['kSus','kPt']);
          const duas=montarPool('materia').length;
          montarSelMat=new Set();
          return {porMat,sus:pool.length,soSus,duas,
                  vazio:montarPool('materia').length,
                  temModo:MONTAR_MODOS.some(m=>m.id==='materia')};}""")
        print('   acervo por matéria: %s'%r['porMat'])
        print('   só Saúde Pública: %s itens (todos dela: %s) · + Português: %s · nenhuma: %s'
              %(r['sus'],r['soSus'],r['duas'],r['vazio']))
        assert r['temModo'] and r['soSus'] and r['sus']>0
        assert r['duas']>r['sus'] and r['vazio']==0
        print('   OK\n')

        print('=== G) monta de verdade a partir do banco ===')
        r=await page.evaluate("""()=>{
          montarSelMat=new Set(['kSus']);
          document.getElementById('provas-content').innerHTML=montarHTML();
          const el=document.getElementById('montar-modo'); el.value='materia';
          document.getElementById('montar-qtd').value='12';
          const antes=db.provas.length;
          montarAgora();
          const nova=db.provas[0];
          return {antes,depois:db.provas.length,itens:nova.questoes.length,
                  soSus:nova.questoes.every(q=>q.kingdomId==='kSus'),
                  treino:!!nova.treino, rotulo:provaRotulo(nova),
                  semCarimbo:nova.questoes.every(q=>q.ultimoResultado===undefined)};}""")
        print('   montou "%s" com %s itens, só de Saúde Pública: %s'
              %(r['rotulo'],r['itens'],r['soSus']))
        print('   marcada como treino: %s · sem carimbo de resposta antiga: %s'
              %(r['treino'],r['semCarimbo']))
        assert r['depois']==r['antes'] or r['depois']==r['antes']+1
        assert r['itens']==12 and r['soSus'] and r['treino'] and r['semCarimbo']
        print('   OK\n')

        print('=== H) apagar a mao tambem manda pro banco ===')
        r=await page.evaluate("""()=>{
          const qs=QS('kPt','Português','📖','sP1','Crase',7,'H');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const antes=db.acervo.length;
          window.confirm=()=>true;
          provaApagar(id);
          return {antes,depois:db.acervo.length,
                  sumiu:!provaAchar(id),
                  noBanco:db.acervo.filter(q=>q.questao.startsWith('H ')).length};}""")
        print('   prova apagada: %s · banco %s → %s (as 7 entraram: %s)'
              %(r['sumiu'],r['antes'],r['depois'],r['noBanco']))
        assert r['sumiu'] and r['noBanco']==7
        print('   OK\n')

        print('=== I) item quebrado nao entra no banco ===')
        r=await page.evaluate("""()=>{
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',5,'I');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.questoes[0].motivo='datado';
          pr.questoes[1].problematico=true;
          const novas=acervoGuardarProva(pr);
          const dentro=db.acervo.filter(q=>q.questao.startsWith('I ')).length;
          return {novas,dentro,doTotal:pr.questoes.length};}""")
        print('   prova de %s · 1 desatualizado + 1 com problema → %s foram pro banco'
              %(r['doTotal'],r['novas']))
        assert r['novas']==3 and r['dentro']==3
        print('   item que você marcou como quebrado não volta pra te atrapalhar depois')
        print('   OK\n')

        print('=== J) o banco nao tem teto de tamanho — so rede de seguranca ===')
        # O teto por bytes saiu junto com a mudanca de lugar: agora o banco tem no
        # proprio no Firebase, entao o tamanho dele nao pesa mais no saveDB.
        r=await page.evaluate("""()=>{
          const antes=db.acervo.length;
          db.acervo=db.acervo.concat(Array.from({length:500},(_,i)=>
            ({questao:'enche '+'x'.repeat(2000)+i,correta:'C',subId:'sE1',kingdomId:'kEnf'})));
          const cortou=acervoAparar();
          return {antes,depois:db.acervo.length,cortou,teto:ACERVO_MAX,
                  bytes:JSON.stringify(db.acervo).length,
                  noPayload:payloadParaFirebase().acervo};}""")
        print('   %s + 500 questões de 2 KB = %s bytes → cortou %s (teto: %s questões)'
              %(r['antes'],r['bytes'],r['cortou'],r['teto']))
        assert r['cortou']==0 and r['depois']==r['antes']+500
        assert r['noPayload'] is None, 'o banco vazou pro registro principal'
        print('   1 MB no banco e o registro que sobe a cada saveDB continua sem ele')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()

        print('=== K) as provas que ja existem ganham numero na ordem certa ===')
        # Conta de verdade: sete provas guardadas antes da numeracao existir.
        antigas=[{'id':'p%d'%i,'criadaEm':'2026-09-%02dT10:00:00.000Z'%(14+i),
                  'formato':'certoerrado','nivel':'dificil','limiteSec':0,'origem':'colado',
                  'questoes':[{'questao':'velha %d-%d'%(i,k),'correta':'C','subId':'sE1',
                               'subName':'Choque septico','kingdomId':'kEnf',
                               'kingdomName':'Enfermagem','kingdomIcon':'💉'} for k in range(3)],
                  'tentativas':[]}
                 for i in range(7)]
        antigas.reverse()                     # a lista e a mais nova primeiro
        b,page,errs=await setup_page(p2,seed({'provas':antigas}))
        r=await page.evaluate("""()=>{
          const porData=db.provas.slice().sort((a,b)=>new Date(a.criadaEm)-new Date(b.criadaEm));
          return {nums:porData.map(p=>p.num),
                  rotulos:porData.map(p=>provaRotulo(p)),
                  seq:db.provaSeq, semRepetir:new Set(db.provas.map(p=>p.num)).size===db.provas.length,
                  proxima:(()=>{const id=provaGuardarLote(
                      [{questao:'nova',correta:'C',subId:'sE1',subName:'Choque septico',
                        kingdomId:'kEnf',kingdomName:'Enfermagem',kingdomIcon:'💉'}],
                      {formato:'certoerrado'});
                    return provaAchar(id).num;})()};}""")
        print('   numeração por data: %s'%r['nums'])
        print('   a mais antiga virou "%s"'%r['rotulos'][0])
        print('   a mais nova virou "%s"'%r['rotulos'][-1])
        assert r['nums']==[1,2,3,4,5,6,7] and r['semRepetir']
        print('   a próxima prova criada pega o nº %s — número não se repete'%r['proxima'])
        assert r['proxima']==8
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('   erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('   OK\n')
        print('OK')

asyncio.run(main())
