# Varredura que tenta amarrar flashcard ao miniboss pelo nome, com previa antes de gravar.
# A regra de ouro e PRECISAO: um card amarrado no assunto errado envenena a medicao dos
# dois assuntos. Entao so olha os minibosses do proprio chefao, exige o nome INTEIRO e
# exige folga sobre o segundo colocado. Na duvida, nao amarra.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def c(i,mb,perg,resp='Resposta.',tags='',sub=None):
    d={'id':'c%d'%i,'mbId':mb,'pergunta':perg,'resposta':resp,'tags':tags,
       'acertos':0,'erros':0}
    if sub:d['subId']=sub
    return d

CARDS={}
def add(*cs):
    for x in cs: CARDS[x['id']]=x
add(
 # --- casam com ALTA: nome do miniboss na TAG
 c(1,'t1','Qual a conduta inicial?','...','reposicao volemica,choque hipovolemico'),
 c(2,'t1','O que avaliar primeiro?','...','choque hipovolemico,trauma'),
 # --- casam com ALTA: nome de 2+ palavras no corpo
 c(3,'t1','Como se define o choque hipovolemico na pratica clinica?','Perda de volume.'),
 # --- casa com MEDIA: nome de UMA palavra, so no corpo
 c(4,'t2','O paciente em PCR deve receber compressoes.','...'),
 # --- NAO pode casar: dois minibosses do mesmo chefao disputam
 c(5,'t1','Diferencie choque hipovolemico de choque cardiogenico.','...'),
 # --- NAO pode casar: nome so PARCIAL (tem "choque", falta "hipovolemico")
 c(6,'t1','O que e choque?','Sindrome de hipoperfusao.'),
 # --- NAO pode casar: nenhum nome aparece
 c(7,'t1','Qual o valor normal da glicemia?','70 a 99.'),
 # --- ja tem vinculo: nao pode ser tocado
 c(8,'t1','Card ja amarrado sobre choque hipovolemico','...','',sub='s1'),
 # --- chefao que nao existe mais
 c(9,'tX','Card orfao sobre choque hipovolemico','...'),
)
SUBS1=[{'id':'s1','name':'Choque Hipovolemico','priority':70,'studied':True,'studiedAt':'2026-01-01'},
       {'id':'s2','name':'Choque Cardiogenico','priority':70,'studied':True,'studiedAt':'2026-01-01'},
       {'id':'s3','name':'Glicemia capilar','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
SUBS2=[{'id':'s4','name':'PCR','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':SUBS1},
                  {'id':'t2','name':'Suporte de vida','subtopics':SUBS2}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)

        print('=== A) a passada a seco nao grava nada ===')
        r=await page.evaluate("""()=>{
          const antes=Object.values(db.flashcards).filter(c=>c.subId).map(c=>c.id);
          const v=revVarrerVinculos();
          const depois=Object.values(db.flashcards).filter(c=>c.subId).map(c=>c.id);
          return {antes,depois,semVinculo:v.semVinculo,semChefe:v.semChefe,res:v.res,
                  casados:v.casados.map(x=>[x.cardId,x.subNome,x.conf])};
        }""")
        print('   sem vinculo: %d (orfaos de chefao: %d)'%(r['semVinculo'],r['semChefe']))
        print('   casaram: alta=%d media=%d'%(r['res']['alta'],r['res']['media']))
        for cid,nome,cf in r['casados']: print('      %-4s -> %-22s (%s)'%(cid,nome,cf))
        assert r['antes']==r['depois']==['c8'], r
        print('   OK — nada gravado\n')

        print('=== B) quem casou e quem NAO casou ===')
        casou={x[0]:x[1] for x in r['casados']}
        esperado={'c1':'Choque Hipovolemico','c2':'Choque Hipovolemico',
                  'c3':'Choque Hipovolemico','c4':'PCR'}
        for cid,nome in esperado.items():
            print('   %-4s casou com %-22s %s'%(cid,casou.get(cid,'—'),'OK' if casou.get(cid)==nome else 'FALHOU'))
        assert {k:v for k,v in casou.items()}==esperado, (casou,esperado)
        print('   c5 (dois assuntos disputam) ficou de fora: %s'%('c5' not in casou))
        print('   c6 (nome so parcial) ficou de fora:        %s'%('c6' not in casou))
        print('   c7 (nenhum nome) ficou de fora:            %s'%('c7' not in casou))
        print('   c9 (chefao inexistente) ficou de fora:     %s'%('c9' not in casou))
        assert not any(x in casou for x in ['c5','c6','c7','c9'])
        print('   OK\n')

        print('=== C) confianca: tag = alta; uma palavra so no corpo = media ===')
        conf={x[0]:x[2] for x in r['casados']}
        print('   c1/c2 (nome na tag): %s/%s · c3 (2 palavras no corpo): %s · c4 (1 palavra no corpo): %s'
              %(conf['c1'],conf['c2'],conf['c3'],conf['c4']))
        assert conf['c1']=='alta' and conf['c3']=='alta' and conf['c4']=='media'
        print('   OK\n')

        print('=== D) aplicar so os de alta ===')
        r2=await page.evaluate("""async()=>{
          window.confirm=()=>true;
          revAbrirVarredura();
          revAplicarVarredura('alta');
          await new Promise(r=>setTimeout(r,150));
          const f=db.flashcards;
          return {c1:f.c1.subId,c3:f.c3.subId,c4:f.c4.subId||null,
                  auto:Object.values(f).filter(x=>x.vinculoAuto).length,
                  c8auto:!!f.c8.vinculoAuto,c8sub:f.c8.subId};
        }""")
        print('   c1=%s c3=%s · c4 (media) ficou: %s'%(r2['c1'],r2['c3'],r2['c4']))
        print('   marcados como automatico: %d · o card que ja tinha vinculo foi tocado? %s'
              %(r2['auto'],r2['c8auto']))
        assert r2['c1']=='s1' and r2['c3']=='s1' and r2['c4'] is None
        assert r2['auto']==3 and not r2['c8auto'] and r2['c8sub']=='s1'
        print('   OK\n')

        print('=== E) desfazer nao toca em quem ja tinha vinculo ===')
        r3=await page.evaluate("""async()=>{
          revAbrirVarredura(); revDesfazerVarredura();
          await new Promise(r=>setTimeout(r,150));
          const f=db.flashcards;
          return {c1:f.c1.subId||null,c3:f.c3.subId||null,c8:f.c8.subId,
                  auto:Object.values(f).filter(x=>x.vinculoAuto).length};
        }""")
        print('   c1=%s c3=%s · c8 (manual) segue %s · automaticos restantes: %d'
              %(r3['c1'],r3['c3'],r3['c8'],r3['auto']))
        assert r3['c1'] is None and r3['c3'] is None and r3['c8']=='s1' and r3['auto']==0
        print('   OK\n')

        print('=== F) aplicar alta+media, e a retencao passa a ser do assunto ===')
        r4=await page.evaluate("""async()=>{
          Object.values(db.flashcards).forEach(c=>{
            c.fsrs={S:10,D:5}; const d=new Date(); d.setDate(d.getDate()-30);
            c.ultimaRevisao=d.toISOString().slice(0,10);
          });
          revAbrirVarredura(); revAplicarVarredura('tudo');
          await new Promise(r=>setTimeout(r,200));
          const s1=simFindSub('s1');
          return {c4:db.flashcards.c4.subId,
                  ret:revRetencao(s1,'t1'),
                  sem:Object.values(db.flashcards).filter(c=>!c.subId).length};
        }""")
        print('   c4 (media) amarrado: %s · sobraram sem assunto: %d'%(r4['c4'],r4['sem']))
        print('   retencao de "Choque Hipovolemico": %s'%r4['ret'])
        assert r4['c4']=='s4' and r4['ret'] and r4['ret']['fonte']=='assunto'
        print('   OK — deixou de ser aproximacao do chefao\n')

        print('=== G) o atalho aparece na barra da fila ===')
        r5=await page.evaluate("""()=>{filterRevs('fila',document.querySelector('#screen-revisions .filter-row .chip'));
          const t=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          return {tem:t.indexOf('tentar amarrar')>=0, txt:t.slice(t.indexOf('flashcard'),t.indexOf('flashcard')+90)};}""")
        print('   %s'%r5['txt'])
        assert r5['tem']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
