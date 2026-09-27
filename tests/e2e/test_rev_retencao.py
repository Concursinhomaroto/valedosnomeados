# A fila ordenava so pelo acerto em questoes: a retencao dos flashcards estava bloqueada
# porque o card esta preso ao chefao, nao ao miniboss (so 24% dos 4870 tem subId).
# Em vez de esperar a migracao, o indice usa as duas granularidades: assunto quando ha
# vinculo, chefao quando nao ha. E dois bugs que PERDIAM o vinculo foram corrigidos.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def card(i,sub=None,mb='t1',dias=10,S=20):
    c={'id':'c%d'%i,'mbId':mb,'pergunta':'P%d'%i,'resposta':'R%d'%i,
       'acertos':3,'erros':0,'fsrs':{'S':S,'D':5},'ultimaRevisao':None,'_dias':dias}
    if sub:c['subId']=sub
    return c
SUBS=[{'id':'s1','name':'Choque','priority':70,'studied':True,'studiedAt':'2026-01-01'},
      {'id':'s2','name':'PCR','priority':70,'studied':True,'studiedAt':'2026-01-01'},
      {'id':'s3','name':'Crase','priority':70,'studied':True,'studiedAt':'2026-01-01'}]
CARDS={}
# s1: 4 cards proprios, memoria FRACA (S baixo, faz tempo)
for i in range(1,5): CARDS['c%d'%i]=card(i,'s1',dias=60,S=8)
# s2: 4 cards proprios, memoria BOA
for i in range(5,9): CARDS['c%d'%i]=card(i,'s2',dias=5,S=200)
# s3: nenhum card proprio; o chefao t2 tem 6 cards com memoria fraca
for i in range(9,15): CARDS['c%d'%i]=card(i,None,mb='t2',dias=60,S=8)
seed=make_seed({'studyNickname':'Leo','flashcards':CARDS,
  'kingdoms':[{'id':'k1','name':'Enf','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':SUBS[:2]},
                  {'id':'t2','name':'Sintaxe','subtopics':[SUBS[2]]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{
          // ultimaRevisao a partir do _dias de cada card
          Object.values(db.flashcards).forEach(c=>{
            const d=new Date(); d.setDate(d.getDate()-(c._dias||10));
            // ISO COMPLETO, que e o que o app grava de verdade (c.ultimaRevisao=new
            // Date().toISOString()). Semear 'AAAA-MM-DD' aqui foi o que escondeu o NaN.
            c.ultimaRevisao=d.toISOString(); delete c._dias;
          });
          db.revisions={}; ['s1','s2','s3'].forEach(id=>{
            const d=new Date(); d.setDate(d.getDate()-40);
            db.revisions[id]=[{date:d.toISOString().slice(0,10),completed:true,quality:4}];
          });
          db.revOrcamentoMin=240; saveDB();
        }""")
        await page.wait_for_timeout(200)

        print('=== A) retencao por ASSUNTO quando ha vinculo ===')
        r=await page.evaluate("""()=>{
          const f=id=>{let o=null;db.kingdoms.forEach(k=>(db.topics[k.id]||[]).forEach(t=>
            (t.subtopics||[]).forEach(s=>{if(s.id===id)o={s,t};})));return o;};
          const out={};
          ['s1','s2','s3'].forEach(id=>{const x=f(id);out[id]=revRetencao(x.s,x.t.id);});
          return out;
        }""")
        for k,v in r.items():
            print('   %s -> %s'%(k, ('R %.2f de %d cards (%s)'%(v['r'],v['n'],v['fonte'])) if v else 'sem medicao'))
        assert r['s1']['fonte']=='assunto' and r['s2']['fonte']=='assunto'
        assert r['s1']['r']<r['s2']['r'], r
        print('   OK\n')

        print('   nenhum NaN: %s'%all(v is None or (v['r']==v['r']) for v in r.values()))
        assert all(v is None or (v['r']==v['r']) for v in r.values()), r
        assert all(v is None or 0<=v['r']<=1 for v in r.values()), r

        print('=== B) sem vinculo, cai na media do CHEFAO ===')
        print('   s3 (nenhum card proprio) -> %s, %d cards'%(r['s3']['fonte'],r['s3']['n']))
        assert r['s3']['fonte']=='chefao' and r['s3']['n']==6
        print('   OK\n')

        print('=== C) memoria fraca sobe na fila ===')
        r2=await page.evaluate("()=>revCandidatos().map(c=>[c.sub.name,Math.round((c.retencao||{}).r*100)||null,Math.round(c.urg)])")
        for n,rt,u in r2: print('   %-8s retencao %-6s urgencia %d'%(n,(str(rt)+'%') if rt else '—',u))
        nomes=[x[0] for x in r2]
        assert nomes.index('Choque')<nomes.index('PCR'), r2
        print('   OK — Choque (R baixa) passa na frente de PCR (R alta), mesmo tempo parado\n')

        print('=== D) o item mostra de onde veio a retencao ===')
        r3=await page.evaluate("""()=>{filterRevs('fila',document.querySelector('#screen-revisions .filter-row .chip'));
          const t=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          return {t, temAssunto:t.indexOf('do assunto')>=0, temChefao:t.indexOf('do chefão')>=0};}""")
        print('   mostra "do assunto": %s · "do chefão": %s'%(r3['temAssunto'],r3['temChefao']))
        assert r3['temAssunto'] and r3['temChefao']
        print('   OK\n')

        print('=== D2) card com data estranha nao envenena a media (o NaN% da fila) ===')
        rN=await page.evaluate("""()=>{
          const f=id=>{let o=null;db.kingdoms.forEach(k=>(db.topics[k.id]||[]).forEach(t=>
            (t.subtopics||[]).forEach(s=>{if(s.id===id)o={s,t};})));return o;};
          const antes=revRetencao(f('s1').s,'t1');
          db.flashcards.cX={id:'cX',mbId:'t1',subId:'s1',pergunta:'P',resposta:'R',
            fsrs:{S:20,D:5},ultimaRevisao:'data invalida',acertos:1,erros:0};
          // (nao adianta usar fsrs.S=0 como "invalido": o FSRS deriva um estado de
          //  acertos/erros nesse caso, e aí o card conta com razao)
          db.lastModified=Date.now();
          return {antes,depois:revRetencao(f('s1').s,'t1')};
        }""")
        print('   antes: R %.2f de %d cards'%(rN['antes']['r'],rN['antes']['n']))
        print('   depois de entrar um card com ultimaRevisao invalida: R %.2f de %d cards'
              %(rN['depois']['r'],rN['depois']['n']))
        assert rN['depois']['r']==rN['depois']['r'], 'NaN voltou'
        assert rN['depois']['n']==rN['antes']['n'], 'card invalido nao pode entrar na conta'
        print('   OK — os invalidos ficam de fora em vez de virar NaN\n')

        print('=== E) o card de questao errada agora guarda o assunto (era o bug) ===')
        r4=await page.evaluate("""()=>{
          const s=simFindSub('s1');
          const q={questao:'Qual a conduta no choque?',alternativas:[{letra:'A',texto:'X'},{letra:'B',texto:'Y'}],
                   correta:'A',explicacao:'Porque sim.',formato:'multipla'};
          const antes=Object.keys(db.flashcards).length;
          criarFlashcardDeQuestaoErrada('s1',q);
          const novo=Object.values(db.flashcards).find(c=>c.tags==='banco-de-erros');
          return {criou:Object.keys(db.flashcards).length-antes,
                  subId:novo&&novo.subId,subNome:novo&&novo.subNome,mbId:novo&&novo.mbId};
        }""")
        print('   criou %d card · subId=%s · subNome=%s · mbId=%s'
              %(r4['criou'],r4['subId'],r4['subNome'],r4['mbId']))
        assert r4['subId']=='s1' and r4['subNome']=='Choque'
        print('   OK\n')

        print('=== F) exportar o modelo nao perde mais o vinculo ===')
        r5=await page.evaluate("""()=>{
          const orig=URL.createObjectURL; let capt=null;
          URL.createObjectURL=(blob)=>{capt=blob;return 'blob:x';};
          const a=document.createElement('a'); const clickOrig=a.click;
          exportarModeloEstudo();
          URL.createObjectURL=orig;
          return capt?capt.text().then(t=>{const m=JSON.parse(t);
            const com=m.flashcards.filter(c=>c.subId).length;
            return {total:m.flashcards.length,com};}):null;
        }""")
        print('   no arquivo exportado: %d de %d cards com subId'%(r5['com'],r5['total']))
        assert r5['com']>0, r5
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
