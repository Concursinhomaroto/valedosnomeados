# A Camara de Revisoes era um calendario de vencimentos: com 326 assuntos a pilha de
# atrasados e matematicamente permanente. Agora e uma fila com orcamento.
# Aqui: (1) a fila corta no tamanho do dia, (2) ordena por dias x sinal medido,
# (3) o ciclo sai de assuntos/dia e responde ao orcamento, (4) o "dominio total" nao
# tira mais o assunto da fila pra sempre, (5) concluir agenda a volta pelo ciclo.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def mb(i, dias, ac=None, n=0, pri=70, passadas=0):
    """miniboss estudado ha X dias, com taxa de acerto opcional"""
    s={'id':'s%d'%i,'name':'Assunto %d'%i,'priority':pri,'studied':True,
       'studiedAt':'2026-01-01'}
    if ac is not None:
        s['simStats']={'tentativas':1,'questoesTotal':n,'acertosTotal':round(ac*n)}
    return s

SUBS=[mb(1,90,0.40,40),   # muito tempo + errando muito -> topo
      mb(2,90,0.95,40),   # muito tempo mas acertando -> desce
      mb(3,10,0.40,40),   # errando mas visto ha pouco
      mb(4,60,None,0),    # sem medicao
      mb(5,30,0.60,3),    # amostra minuscula: quase nao pesa
      mb(6,5,0.50,40),
      mb(7,45,0.70,20),
      mb(8,20,0.80,20)]
seed=make_seed({'studyNickname':'Leo',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':SUBS}]}})

SETUP="""(dias)=>{
  // 'ha X dias sem olhar' = ultima revisao concluida nessa data
  const hoje=new Date('2026-09-13T00:00:00');
  db.revisions={};
  Object.keys(dias).forEach(id=>{
    const d=new Date(hoje); d.setDate(d.getDate()-dias[id]);
    db.revisions[id]=[{date:d.toISOString().slice(0,10),completed:true,quality:4}];
  });
}"""
DIAS={'s1':90,'s2':90,'s3':10,'s4':60,'s5':30,'s6':5,'s7':45,'s8':20}

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate(SETUP,DIAS)

        print('=== A) o ciclo sai da capacidade, nao de formula ===')
        for orc,esperado in ((60,3),(120,6),(30,1)):
            e=await page.evaluate("o=>{db.revOrcamentoMin=o;return revEstado();}",orc)
            print('   %3d min/dia -> cabem %d por dia · ciclo %d dias (8 assuntos)'
                  %(orc,e['porDia'],e['ciclo']))
            assert e['porDia']==esperado, (orc,e)
            assert e['ciclo']==round(8/e['porDia']) or abs(e['ciclo']-8/e['porDia'])<1
        print('   OK\n')

        print('=== B) a fila corta no tamanho do dia e ordena por urgencia ===')
        r=await page.evaluate("""()=>{
          db.revOrcamentoMin=60;   // 3 por dia
          renderRevisions();
          const nomes=[].map.call(document.querySelectorAll('#revisions-list .rev-name'),e=>e.textContent);
          const todos=revCandidatos().map(c=>[c.sub.name,Math.round(c.urg)]);
          return {nomes,todos,html:document.getElementById('revisions-list').innerHTML};
        }""")
        print('   ordem completa por urgencia: %s'%r['todos'])
        print('   mostrados hoje (3): %s'%r['nomes'])
        assert len(r['nomes'])==3, r['nomes']
        assert r['todos'][0][0]=='Assunto 1', r['todos'][0]
        # o que ficou de fora nao vira divida
        assert 'Sem atrasadas, sem d' in r['html']
        print('   rodape: "Por hoje e isso. Sem atrasadas, sem divida." OK\n')

        print('=== C) acertar muito desce na fila, mesmo parado ha o mesmo tempo ===')
        pos=[n for n,_ in r['todos']]
        print('   s1 (90d, 40%% de acerto) posicao %d | s2 (90d, 95%%) posicao %d'
              %(pos.index('Assunto 1')+1,pos.index('Assunto 2')+1))
        assert pos.index('Assunto 1')<pos.index('Assunto 2')
        print('   OK\n')

        print('=== D) amostra pequena nao sacode a fila ===')
        u=await page.evaluate("""()=>{
          const c={}; revCandidatos().forEach(x=>c[x.sub.name]={peso:+x.peso.toFixed(2),dias:x.dias});
          return c;
        }""")
        print('   s5 (60%% em SO 3 questoes) peso %.2f  vs  s7 (70%% em 20) peso %.2f'
              %(u['Assunto 5']['peso'],u['Assunto 7']['peso']))
        assert abs(u['Assunto 5']['peso']-1.0)<abs(u['Assunto 7']['peso']-1.0)+0.15
        print('   OK\n')

        print('=== E) "dominio total" nao exclui mais o assunto ===')
        r2=await page.evaluate("""()=>{
          const s=simFindSub('s1'); s.revMastered=true;
          const naFila=revCandidatos().some(c=>c.sub.id==='s1');
          return {naFila, piso:REV_PISO};
        }""")
        print('   assunto com revMastered=true continua na fila: %s (piso de peso %s)'
              %(r2['naFila'],r2['piso']))
        assert r2['naFila']
        print('   OK\n')

        print('=== F) concluir agenda a volta pelo ciclo, e sempre agenda ===')
        r3=await page.evaluate("""async()=>{
          db.revOrcamentoMin=60;
          const antes=(db.revisions['s1']||[]).length;
          revConcluirDaFila('s1');
          await new Promise(r=>setTimeout(r,120));
          const revs=db.revisions['s1']||[];
          const pend=revs.filter(r=>!r.completed);
          const s=simFindSub('s1');
          return {antes,depois:revs.length,pendentes:pend.length,
                  prox:pend.length?pend[pend.length-1].date:null,
                  mastered:s.revMastered,
                  foraDaFilaHoje:!revCandidatos().some(c=>c.sub.id==='s1')};
        }""")
        print('   revisoes %d -> %d · pendente agendada para %s'
              %(r3['antes'],r3['depois'],r3['prox']))
        print('   revMastered ficou: %s · saiu da fila de HOJE: %s'
              %(r3['mastered'],r3['foraDaFilaHoje']))
        assert r3['pendentes']==1 and r3['prox'] and not r3['mastered']
        assert r3['foraDaFilaHoje'], 'concluido hoje nao pode voltar no topo agora'
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())

# ---- G/H acrescentados depois do bug do BCG: responder "Esqueci tudo" nao mudava
# nada, porque revProxIntervalo ignorava a nota. Caso real do usuario: revisao
# concluida com "Esqueceu tudo" reagendada para 27 dias depois.
async def notas():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate(SETUP,DIAS)
        print('=== G) a nota muda a volta (o bug do BCG) ===')
        r=await page.evaluate("""async()=>{
          db.revOrcamentoMin=60;
          const out={};
          for(const q of [1,3,4,5]){
            // estado limpo a cada nota
            db.revisions['s7']=[{date:'2026-07-14',completed:true,quality:4}];
            const s=simFindSub('s7'); s.revMastered=false;
            revConcluirDaFila('s7',q);
            await new Promise(r=>setTimeout(r,60));
            const pend=(db.revisions['s7']||[]).filter(r=>!r.completed);
            out[q]=pend.length?daysDiff(todayStr(),pend[pend.length-1].date):null;
          }
          return out;
        }""")
        rot={'1':'Esqueci tudo','3':'Com dificuldade','4':'Lembrei bem','5':'Sabia de cor'}
        for q in ('1','3','4','5'):
            print('   %-17s -> volta em %s dia(s)'%(rot[q],r[q]))
        assert r['1']<=r['3']<=r['4']<r['5'], r
        assert r['1']<=7, ('esquecer tudo volta no primeiro degrau da escada',r)
        print('')

        print('=== G2) o prazo NAO depende mais do tamanho da colecao ===')
        r3=await page.evaluate("""()=>{
          const s=simFindSub('s7');
          db.revisions['s7']=[{date:'2026-07-14',completed:true,quality:4}];
          const pequeno={}; [1,3,4,5].forEach(q=>pequeno[q]=revProxIntervalo(s,q));
          const t=db.topics.k1[0];
          for(let i=100;i<420;i++)t.subtopics.push({id:'x'+i,name:'X'+i,priority:70,
            studied:true,studiedAt:'2026-01-01'});
          const grande={}; [1,3,4,5].forEach(q=>grande[q]=revProxIntervalo(s,q));
          return {pequeno,grande,estudados:revEstado().estudados,ciclo:revEstado().ciclo};
        }""")
        print('   com 8 assuntos:   %s'%r3['pequeno'])
        print('   com %d assuntos: %s (ciclo %d dias)'
              %(r3['estudados'],r3['grande'],r3['ciclo']))
        assert r3['pequeno']==r3['grande'], r3
        print('   OK — a escada e a mesma; o ciclo so informa, nao manda mais no prazo\n')

        print('=== H) revisao ruim nao conta como progresso rumo ao piso ===')
        r2=await page.evaluate("""()=>{
          const s=simFindSub('s6');
          db.revisions['s6']=[{date:'2026-05-01',completed:true,quality:1},
                              {date:'2026-06-01',completed:true,quality:1},
                              {date:'2026-07-01',completed:true,quality:1}];
          const pesoRuins=revPeso(s), boasRuins=revPassadasBoas(s);
          db.revisions['s6']=[{date:'2026-05-01',completed:true,quality:5},
                              {date:'2026-06-01',completed:true,quality:5},
                              {date:'2026-07-01',completed:true,quality:5}];
          return {pesoRuins,boasRuins,pesoBoas:revPeso(s),boasBoas:revPassadasBoas(s)};
        }""")
        print('   3 revisoes "esqueci tudo": %d boas, peso %.2f'%(r2['boasRuins'],r2['pesoRuins']))
        print('   3 revisoes "sabia de cor": %d boas, peso %.2f'%(r2['boasBoas'],r2['pesoBoas']))
        assert r2['pesoRuins']>r2['pesoBoas'], r2
        print('   OK — esquecer mantem o assunto pesado; acertar e que estica\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(notas())
