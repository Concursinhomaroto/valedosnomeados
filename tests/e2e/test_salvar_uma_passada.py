# -*- coding: utf-8 -*-
# Travamento ao clicar (medido numa conta real: registro de ~13 MB, ~900 minibosses, ~6 mil
# flashcards, ~15 mil questões). Três consertos, cada um com a sua conferência:
#  1) simFindSub usa um índice em vez de varrer a árvore a cada chamada — tem de devolver
#     EXATAMENTE o que a varredura devolvia, inclusive depois de criar/apagar/mover miniboss;
#  2) getAllFCForTopic agrupa os cards uma vez enquanto uma tela é desenhada (comIndiceFC) —
#     dentro do escopo a resposta é a mesma da varredura, e fora dele nada fica em cache;
#  3) saveDB só marca; a gravação acontece UMA vez na pausa, com o retrato tirado direto do
#     db (syncMapaDoDb) — que tem de ser igual, campo por campo, ao retrato antigo
#     (syncMapa(payloadParaFirebase())).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

UID='TEST_UID_LEO'
V1='users/%s/vdn_v1'%UID

def seed():
    def sub(i,k):
        s={'id':'s%s_%d'%(k,i),'name':'Assunto %s %d'%(k,i),'priority':70 if i%2 else 100,'studied':True,'studiedAt':'2026-01-01'}
        if i==0:
            s['simHistorico']=[{'id':'h1','data':'2026-01-05','questoes':[
                {'questao':'Q certa','correta':'A','userAnswer':'A','alternativas':[{'letra':'A','texto':'x'}],'explicacao':'peso morto','formato':'ce','revisado':True},
                {'questao':'Q errada','correta':'A','userAnswer':'B','alternativas':[{'letra':'A','texto':'x'}],'explicacao':'fica inteira'}]}]
        return s
    topics={}
    for k in ('k1','k2','k3'):
        topics[k]=[{'id':'t%s_%d'%(k,t),'name':'Chefão %s %d'%(k,t),'icon':'⚔️','subtopics':[sub(i+t*10,k) for i in range(4)]} for t in range(3)]
    fc={}
    n=0
    for k in ('k1','k2','k3'):
        for t in range(3):
            for i in range(7):
                n+=1
                fc['fc%d'%n]={'id':'fc%d'%n,'mbId':'t%s_%d'%(k,t),'subId':'s%s_%d'%(k,t*10),'pergunta':'P %d'%n,'resposta':'R %d'%n,
                              'tags':'','dificuldade':2,'acertos':n%3,'erros':n%2,'lastConf':4 if n%4 else 0,'criacao':'2026-01-01T10:00:00Z'}
    return make_seed({'studyNickname':'Leo','xp':100,
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'},{'id':'k2','name':'Português','icon':'📚'},{'id':'k3','name':'SUS','icon':'🏥'}],
      'topics':topics,'flashcards':fc,
      'revisions':{'sk1_0':[{'date':'2026-01-10','completed':False}]}})

# compara dois retratos (formato do syncMapa): devolve a lista de diferenças
CMP="""(a,b)=>{const d=[];const ks=new Set([...Object.keys(a),...Object.keys(b)]);
  ks.forEach(k=>{const x=a[k],y=b[k];if(!x||!y){d.push(k+': falta');return;}
    if(x.o!==y.o){d.push(k+': tipo');return;}
    if(!x.o){if(x.s!==y.s)d.push(k+': valor');return;}
    new Set([...Object.keys(x.ch),...Object.keys(y.ch)]).forEach(c=>{if(x.ch[c]!==y.ch[c])d.push(k+'/'+c);});});
  return d;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.wait_for_timeout(1500)

        print('=== 1) simFindSub (índice) devolve o mesmo que a varredura ===')
        r=await page.evaluate("""()=>{
          const ids=[];db.kingdoms.forEach(k=>(db.topics[k.id]||[]).forEach(t=>(t.subtopics||[]).forEach(s=>ids.push(s.id))));
          ids.push('nao-existe',undefined,null,'');
          const dif=()=>ids.filter(id=>simFindSub(id)!==simFindSubVarredura(id)).length;
          const d0=dif();
          // cria um miniboss SEM salvar: tem de aparecer na hora
          const novo={id:'novo1',name:'Recém-criado',priority:70};
          db.topics.k2[1].subtopics.push(novo);ids.push('novo1');
          const achouNovo=simFindSub('novo1')===novo;const d1=dif();
          // apaga um miniboss SEM salvar: tem de sumir na hora
          const apagado=db.topics.k1[0].subtopics.shift();
          const sumiu=simFindSub(apagado.id)===null;const d2=dif();
          // move um miniboss de chefão (sai de um, entra em outro): continua achando o MESMO objeto
          const movido=db.topics.k3[2].subtopics.pop();db.topics.k1[1].subtopics.unshift(movido);
          const achouMovido=simFindSub(movido.id)===movido;const d3=dif();
          // apaga um reino inteiro: os minibosses dele deixam de existir
          const idDoK2=db.topics.k2[0].subtopics[0].id;
          const k2=db.kingdoms.splice(1,1)[0];
          const semReino=simFindSub(idDoK2)===null;const d4=dif();
          db.kingdoms.splice(1,0,k2);
          // troca a árvore inteira por uma cópia (é o que acontece quando chega dado do servidor)
          db.topics=JSON.parse(JSON.stringify(db.topics));
          const d5=dif();const naCopia=simFindSub('novo1')===db.topics.k2[1].subtopics.find(s=>s.id==='novo1');
          return {d0,d1,d2,d3,d4,d5,achouNovo,sumiu,achouMovido,semReino,naCopia};}""")
        print('   %s'%r)
        assert r=={'d0':0,'d1':0,'d2':0,'d3':0,'d4':0,'d5':0,'achouNovo':True,'sumiu':True,'achouMovido':True,'semReino':True,'naCopia':True}
        print('   OK\n')

        print('=== 2) getAllFCForTopic: mesmo resultado dentro do escopo; fora dele nada fica guardado ===')
        r=await page.evaluate("""()=>{
          const tops=[];db.kingdoms.forEach(k=>(db.topics[k.id]||[]).forEach(t=>tops.push(t.id)));tops.push('nao-existe');
          const ids=l=>l.map(c=>c.id).join(',');
          const fora=tops.map(t=>ids(getAllFCForTopic(t)));
          const dentro=comIndiceFC(()=>tops.map(t=>ids(getAllFCForTopic(t))));
          const lista=comIndiceFC(()=>{const a=getAllFCForTopic(tops[0]);a.length=0;return getAllFCForTopic(tops[0]).length;});
          // depois do escopo: um card movido de chefão aparece no lugar novo na hora
          const c=Object.values(db.flashcards)[0];const de=c.mbId,para=tops.find(t=>t!==de&&t!=='nao-existe');
          const antes=getAllFCForTopic(para).length;c.mbId=para;const depois=getAllFCForTopic(para).length;
          const reinos=[countReinosDominados(),comIndiceFC(countReinosDominados)];
          c.mbId=de;
          return {igual:JSON.stringify(fora)===JSON.stringify(dentro),copiaIndependente:lista===7,moveu:depois===antes+1,
                  escopoFechado:fcIndiceEscopo===null&&escopoMemo===null,reinosIgual:reinos[0]===reinos[1]};}""")
        print('   %s'%r)
        assert r=={'igual':True,'copiaIndependente':True,'moveu':True,'escopoFechado':True,'reinosIgual':True}
        print('   OK\n')

        print('=== 3) retrato direto do db == retrato antigo, inclusive nos casos chatos ===')
        r=await page.evaluate("""(cmp)=>{
          const CMP=eval(cmp);
          const casos={};
          casos.normal=CMP(syncMapa(payloadParaFirebase()),syncMapaDoDb());
          // campos que o JSON descarta ou transforma
          db.campoUndefined=undefined;db.campoFuncao=function(){};db.campoData=new Date(1700000000000);
          db.campoNulo=null;db.campoNaN=NaN;db.objComBuraco={a:1,b:undefined,c:null,d:[1,undefined,3]};
          db.listaVazia=[];db.objVazio={};
          casos.estranhos=CMP(syncMapa(payloadParaFirebase()),syncMapaDoDb());
          // reino apagado com os chefões sobrando em db.topics: NÃO é enxugado (como antes)
          const k3=db.kingdoms.pop();
          casos.reinoOrfao=CMP(syncMapa(payloadParaFirebase()),syncMapaDoDb());
          db.kingdoms.push(k3);
          // muda um reino: só ele é refeito, e o resultado continua igual
          db.topics.k2[0].subtopics[0].simHistorico[0].questoes.push({questao:'nova certa',correta:'C',userAnswer:'C',alternativas:[1,2],explicacao:'sai'});
          casos.depoisDeMudar=CMP(syncMapa(payloadParaFirebase()),syncMapaDoDb());
          const enx=JSON.parse(syncMapaDoDb().topics.ch.k2)[0].subtopics[0].simHistorico[0].questoes;
          ['campoUndefined','campoFuncao','campoData','campoNulo','campoNaN','objComBuraco','listaVazia','objVazio'].forEach(k=>delete db[k]);
          return {casos,certaMagra:!('explicacao' in enx[0])&&enx[0].revisado===true,erradaInteira:enx[1].explicacao==='fica inteira',
                  novaMagra:!('alternativas' in enx[2]),memoriaIntacta:db.topics.k2[0].subtopics[0].simHistorico[0].questoes[2].explicacao==='sai'};}""",CMP)
        print('   %s'%r)
        assert all(len(v)==0 for v in r['casos'].values()), r['casos']
        assert r['certaMagra'] and r['erradaInteira'] and r['novaMagra'] and r['memoriaIntacta']
        print('   OK\n')

        print('=== 4) vários saveDB seguidos viram UMA gravação, na pausa ===')
        r=await page.evaluate("""async(p)=>{
          saveDB();saveFlush();await new Promise(r=>setTimeout(r,50));
          // (o que os itens 1-3 mexeram na memória já subiu na linha de cima)
          window.__updateCalls=[];
          let custoClique=0;
          for(let i=0;i<10;i++){db.xp=200+i;const t=performance.now();saveDB();custoClique+=performance.now()-t;await new Promise(r=>setTimeout(r,60));}
          const duranteCliques=window.__updateCalls.filter(x=>x.path===p).length;
          await new Promise(r=>setTimeout(r,1000));
          const c=window.__updateCalls.filter(x=>x.path===p);
          let n=window.__root;p.split('/').forEach(s=>{n=n&&n[s];});
          const local=await idbLer(lsKey());
          return {duranteCliques,gravacoes:c.length,op:c[0]&&c[0].op,chaves:c[0]?Object.keys(c[0].val).sort():[],xpNuvem:n.xp,xpLocal:local&&local.xp,
                  donoLocal:local&&local._uid,pendente:savePendente};}""",V1)
        print('   %s'%r)
        assert r['duranteCliques']==0 and r['gravacoes']==1 and r['op']=='update'
        assert r['chaves']==['lastModified','xp'] and r['xpNuvem']==209 and r['xpLocal']==209 and r['donoLocal']==UID and not r['pendente']
        print('   OK\n')

        print('=== 5) clicando sem parar, grava no máximo a cada 4 s (não espera a pausa pra sempre) ===')
        r=await page.evaluate("""async(p)=>{
          window.__updateCalls=[];const ini=Date.now();
          while(Date.now()-ini<4700){db.xp++;saveDB();await new Promise(r=>setTimeout(r,300));}
          return window.__updateCalls.filter(x=>x.path===p).length;}""",V1)
        print('   gravações em 4,7 s de cliques a cada 0,3 s: %s'%r)
        assert r>=1
        print('   OK\n')

        print('=== 6) esconder a aba com gravação marcada grava na hora ===')
        r=await page.evaluate("""async(p)=>{
          saveFlush();await new Promise(r=>setTimeout(r,50));window.__updateCalls=[];
          db.xp=777;saveDB();
          const antes=window.__updateCalls.filter(x=>x.path===p).length;
          Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
          document.dispatchEvent(new Event('visibilitychange'));
          delete document.hidden;
          const depois=window.__updateCalls.filter(x=>x.path===p).length;
          let n=window.__root;p.split('/').forEach(s=>{n=n&&n[s];});const xpEscondida=n.xp;
          db.xp=778;saveDB();window.dispatchEvent(new Event('pagehide'));
          let m=window.__root;p.split('/').forEach(s=>{m=m&&m[s];});
          return {antes,depois,xp:xpEscondida,xpPagehide:m.xp};}""",V1)
        print('   %s'%r)
        assert r=={'antes':0,'depois':1,'xp':777,'xpPagehide':778}
        print('   OK\n')

        print('=== 7) o Painel desenha igual com e sem os atalhos ===')
        r=await page.evaluate("""()=>{
          showScreen('dashboard');
          // só os blocos que usam os atalhos (o gráfico de tempo se mede pelo layout e muda de
          // altura entre dois desenhos seguidos — não entra na comparação)
          const ids=['dash-maquina','missao-cta','avg-time-list','dash-badges','dash-badges-summary','next-steps-list','dash-stats','sim-global-stats','controle-erros'];
          const foto=()=>ids.map(id=>{const e=document.getElementById(id);return e?e.innerHTML:'(sem '+id+')';});
          renderDashboard();const comAtalho=foto();
          renderDashboardInterno();const semEscopo=foto();
          return {diferentes:ids.filter((id,i)=>comAtalho[i]!==semEscopo[i]),tam:comAtalho.join('').length};}""")
        print('   %s'%r)
        assert r['diferentes']==[] and r['tam']>1000
        print('   OK\n')

        e=real_errors(errs)
        print('erros de JS:',e or 'nenhum')
        assert not e
        await b.close()
    print('OK')

asyncio.run(main())
