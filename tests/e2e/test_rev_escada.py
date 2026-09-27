# Quatro pedidos do usuario numa rodada:
#  - prazo previsivel (escada fixa) que ELE escolhe, no lugar do numero derivado do ciclo
#  - "Dominado" por assunto, igual ao do flashcard: sai da fila, reversivel e visivel
#  - bloquear um reino inteiro da revisao sem apagar nada
#  - o resumo na tela de revisao estava sem o wrapper .resumo-body (todo o CSS e escopado
#    nele), entao saia no tamanho padrao do modal — o "ficou feio"
import asyncio, json, re, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
RESUMO={'texto':'VISAO GERAL: O emprego dos porques e cobrado em concursos.\n\n'
                'Na pratica: a banca pede a grafia correta numa frase interrogativa.',
        'geradoEm':'2026-08-01T10:00:00Z','origem':'web'}
def mb(i,nome,**kw):
    s={'id':'s%d'%i,'name':nome,'priority':70,'studied':True,'studiedAt':'2026-01-01',
       'resumo':RESUMO}
    s.update(kw); return s
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'🏥'},
              {'id':'k2','name':'Historia','icon':'🏰'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':[
                     mb(1,'Choque'),mb(2,'BCG'),mb(3,'Crase')]}],
            'k2':[{'id':'t2','name':'Brasil Colonia','subtopics':[
                     mb(4,'Capitanias'),mb(5,'Bandeirantes')]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{db.revisions={};['s1','s2','s3','s4','s5'].forEach(id=>{db.revisions[id]=[{date:'2026-03-01',completed:true,quality:4}];});}")

        print('=== A) a escada e previsivel: 7/14/21/30/45/60/90 ===')
        r=await page.evaluate("""()=>{
          const esc=revEscada(); const out={esc,degraus:[]};
          for(let boas=0;boas<=7;boas++){
            db.revisions['s1']=[];
            for(let i=0;i<boas;i++)db.revisions['s1'].push({date:'2026-0'+((i%9)+1)+'-01',completed:true,quality:4});
            out.degraus.push([boas,revProxIntervalo(simFindSub('s1'),4)]);
          }
          db.revisions['s1']=[{date:'2026-03-01',completed:true,quality:4}];
          const s=simFindSub('s1');
          out.notas={1:revProxIntervalo(s,1),3:revProxIntervalo(s,3),4:revProxIntervalo(s,4),5:revProxIntervalo(s,5)};
          return out;
        }""")
        print('   escada: %s'%r['esc'])
        print('   revisoes boas -> prazo: %s'%', '.join('%d→%dd'%(a,c) for a,c in r['degraus']))
        print('   com 1 boa, por nota: esqueci %dd · dificuldade %dd · revisei %dd · de cor %dd'
              %(r['notas']['1'],r['notas']['3'],r['notas']['4'],r['notas']['5']))
        assert r['esc']==[7,14,21,30,45,60,90]
        assert [c for _,c in r['degraus']][:4]==[7,14,21,30]
        assert r['notas']['1']<=7 and r['notas']['3']<r['notas']['4']<r['notas']['5']
        print('   OK\n')

        print('=== B) o prazo que EU escolho ganha do sugerido ===')
        r2=await page.evaluate("""async()=>{
          revAbrirTela('s1'); await new Promise(r=>setTimeout(r,150));
          const sel=document.querySelector('.revtela-rodape select');
          const opcoes=[].map.call(sel.options,o=>o.value);
          const preSel=sel.value;
          revSetPrazo(45);                      // usuario escolhe 45 no lugar do sugerido
          revTelaResponder('s1',4);
          await new Promise(r=>setTimeout(r,200));
          const pend=(db.revisions['s1']||[]).filter(r=>!r.completed);
          return {opcoes,preSel,dias:daysDiff(todayStr(),pend[pend.length-1].date)};
        }""")
        print('   opcoes no seletor: %s | pre-selecionado: %s'%(r2['opcoes'],r2['preSel']))
        print('   escolhi 45 -> agendou para %d dias'%r2['dias'])
        assert r2['dias']==45, r2
        print('   OK\n')

        print('=== C) "esqueci tudo" ignora o prazo escolhido (teto de 7) ===')
        r3=await page.evaluate("""async()=>{
          db.revisions['s2']=[{date:'2026-03-01',completed:true,quality:4}];
          revAbrirTela('s2'); await new Promise(r=>setTimeout(r,120));
          revSetPrazo(90); revTelaResponder('s2',1);
          await new Promise(r=>setTimeout(r,200));
          const pend=(db.revisions['s2']||[]).filter(r=>!r.completed);
          return daysDiff(todayStr(),pend[pend.length-1].date);
        }""")
        print('   escolhi 90 mas respondi "esqueci tudo" -> %d dias'%r3)
        assert r3<=7
        print('   OK\n')

        print('=== D) a data escolhida segura o assunto fora da fila ate chegar ===')
        r4=await page.evaluate("""()=>{
          db.revOrcamentoMin=240;                     // 12 por dia: cabe todo mundo
          const ids=revCandidatos().map(c=>c.sub.id);
          return {naFila:ids, s1fora:ids.indexOf('s1')<0};
        }""")
        print('   fila agora: %s'%r4['naFila'])
        print('   s1 (agendado pra daqui 45 dias) ficou de fora: %s'%r4['s1fora'])
        assert r4['s1fora']
        print('   OK\n')

        print('=== E) Dominado: sai da fila, aparece na aba e volta ===')
        r5=await page.evaluate("""()=>{
          revDominar('s3',true);
          const fora=revCandidatos().every(c=>c.sub.id!=='s3');
          const dom=revDominados().map(d=>d.sub.name);
          filterRevs('dominados',document.querySelector('#screen-revisions .chip'));
          const txt=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          revDominar('s3',false);
          const voltou=revCandidatos().some(c=>c.sub.id==='s3');
          return {fora,dom,temNaAba:txt.indexOf('Crase')>=0,temBotao:txt.indexOf('Voltar pra fila')>=0,voltou};
        }""")
        print('   saiu da fila: %s | lista de dominados: %s'%(r5['fora'],r5['dom']))
        print('   aparece na aba com "Voltar pra fila": %s / %s'%(r5['temNaAba'],r5['temBotao']))
        print('   desfez e voltou pra fila: %s'%r5['voltou'])
        assert r5['fora'] and r5['dom']==['Crase'] and r5['temNaAba'] and r5['temBotao'] and r5['voltou']
        print('   OK\n')

        print('=== F) bloquear reino tira da revisao sem apagar nada ===')
        r6=await page.evaluate("""()=>{
          const antes=revCandidatos().map(c=>c.sub.name);
          revToggleReino('k2');
          const depois=revCandidatos().map(c=>c.sub.name);
          const reinoIntacto=db.kingdoms.some(k=>k.id==='k2');
          const minibossIntactos=(db.topics.k2[0].subtopics||[]).length;
          revToggleReino('k2');
          return {antes,depois,reinoIntacto,minibossIntactos,voltou:revCandidatos().length};
        }""")
        print('   antes: %s'%r6['antes'])
        print('   com Historia desligada: %s'%r6['depois'])
        print('   reino continua no mapa: %s · minibosses intactos: %d'
              %(r6['reinoIntacto'],r6['minibossIntactos']))
        assert 'Capitanias' in r6['antes'] and 'Capitanias' not in r6['depois']
        assert r6['reinoIntacto'] and r6['minibossIntactos']==2
        print('   OK\n')

        print('=== G) o resumo na tela agora usa o CSS do resumo (era o "ficou feio") ===')
        r7=await page.evaluate("""async()=>{
          filterRevs('fila',document.querySelector('#screen-revisions .chip'));
          revAbrirTela('s4'); await new Promise(r=>setTimeout(r,200));
          const body=document.querySelector('.revtela-corpo .resumo-body');
          const h=document.querySelector('.revtela-corpo .resumo-body .resumo-h');
          const p=document.querySelector('.revtela-corpo .resumo-body .resumo-p');
          return {temWrapper:!!body,
                  fonteP:p?getComputedStyle(p).fontSize:null,
                  fonteH:h?getComputedStyle(h).fontSize:null,
                  scrolls:document.querySelectorAll('.revtela-corpo .revtela-scroll').length};
        }""")
        print('   wrapper .resumo-body presente: %s'%r7['temWrapper'])
        print('   tamanho do paragrafo: %s | do titulo: %s'%(r7['fonteP'],r7['fonteH']))
        print('   colunas com rolagem propria: %d'%r7['scrolls'])
        assert r7['temWrapper'] and r7['fonteP'] and float(r7['fonteP'].replace('px',''))<=14
        assert float(r7['fonteH'].replace('px',''))<=12
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())

# ---- H/I/J: a fila ja foca os atrasados (a aba "Atrasadas" separada fica redundante),
# o modal ficou maior e o fluxograma ganhou zoom.
async def extras():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== H) quem passou do prazo ha mais tempo vem primeiro ===')
        r=await page.evaluate("""()=>{
          db.revOrcamentoMin=240;
          const atras={s1:30,s2:3,s3:0};          // dias que o prazo venceu
          db.revisions={};
          Object.keys(atras).forEach(id=>{
            const d=new Date(); d.setDate(d.getDate()-atras[id]);
            db.revisions[id]=[{date:'2026-02-01',completed:true,quality:4},
                              {date:d.toISOString().slice(0,10),completed:false}];
          });
          // s4/s5 sem prazo nenhum, so tempo parado
          ['s4','s5'].forEach(id=>db.revisions[id]=[{date:'2026-02-01',completed:true,quality:4}]);
          const c=revCandidatos();
          return c.map(x=>[x.sub.name,x.atraso,Math.round(x.urg)]);
        }""")
        for nome,at,urg in r:
            print('   %-13s prazo venceu ha %-5s urgencia %d'%(nome,('—' if at is None else str(at)+'d'),urg))
        nomes=[n for n,_,_ in r]
        assert nomes[0]=='Choque', r     # s1, 30 dias de prazo vencido
        assert nomes.index('Choque')<nomes.index('BCG'), r
        print('   OK — a fila ja e a aba "Atrasadas", so que ordenada junto com o resto\n')

        print('=== I) o item mostra o atraso, em vez de esconder ===')
        r2=await page.evaluate("""()=>{renderRevisions();
          return document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');}""")
        print('   texto do item: %s'%[t for t in r2.split('·') if 'venceu' in t][:1])
        assert re.search(r'prazo venceu há (29|30) dias',r2), r2[:300]
        assert 'na vez hoje' in r2
        print('   OK\n')

        print('=== J) modal maior e zoom do fluxograma ===')
        r3=await page.evaluate("""async()=>{
          const s=simFindSub('s1');
          s.fluxograma={raizId:'n1',nos:{n1:{texto:'A',tipo:'inicio',ramos:[{rotulo:'x',to:'n2'},{rotulo:'y',to:'n3'}]},
            n2:{texto:'B',tipo:'acao',ramos:[]},n3:{texto:'C',tipo:'acao',ramos:[]}}};
          revAbrirTela('s1'); await new Promise(r=>setTimeout(r,250));
          const box=document.querySelector('#modal.modal-wide .modal-box');
          const antes=fluxoZoomMode.get('s1')||'fit';
          const btn=document.getElementById('revzoom-s1');
          const rot1=btn?btn.textContent.trim():null;
          btn.click(); await new Promise(r=>setTimeout(r,200));
          const depois=fluxoZoomMode.get('s1');
          const rot2=document.getElementById('revzoom-s1').textContent.trim();
          const sc=document.querySelector('.revtela-scroll');
          return {larguraModal:Math.round(box.getBoundingClientRect().width),
                  janela:window.innerWidth, alturaScroll:Math.round(sc.getBoundingClientRect().height),
                  antes,depois,rot1,rot2,
                  fonte:getComputedStyle(document.querySelector('.revtela-corpo .resumo-body .resumo-p')).fontSize};
        }""")
        print('   modal %dpx numa janela de %dpx · coluna com %dpx de altura'
              %(r3['larguraModal'],r3['janela'],r3['alturaScroll']))
        print('   fonte do resumo: %s'%r3['fonte'])
        print('   zoom: %s -> %s  (botao: "%s" -> "%s")'%(r3['antes'],r3['depois'],r3['rot1'],r3['rot2']))
        assert r3['larguraModal']>=min(1500,r3['janela']*0.9), r3
        assert r3['antes']=='fit' and r3['depois']=='real'
        assert 'Tamanho real' in r3['rot1'] and 'Caber' in r3['rot2']
        assert float(r3['fonte'].replace('px',''))>=14
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(extras())

# ---- K/L: o usuario viu assuntos vencidos ha 3 dias fora do topo e perguntou se estavam
# sendo ignorados; e por que ainda existiam as abas que a fila substituiu.
async def vencidos():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== K) nada que NAO venceu passa na frente do que venceu ===')
        r=await page.evaluate("""()=>{
          db.revOrcamentoMin=240;
          const hoje=new Date();
          const d=n=>{const x=new Date(hoje);x.setDate(x.getDate()-n);return x.toISOString().slice(0,10);};
          db.revisions={
            // vencido ha 3 dias, mas visto ha pouco
            s1:[{date:d(60),completed:true,quality:4},{date:d(3),completed:false}],
            // vencido ha 1 dia, parado ha muito
            s2:[{date:d(200),completed:true,quality:4},{date:d(1),completed:false}],
            // SEM prazo, parado ha muitissimo tempo
            s3:[{date:d(400),completed:true,quality:4}],
            s4:[{date:d(500),completed:true,quality:4}],
            s5:[{date:d(500),completed:true,quality:4}]};
          const c=revCandidatos();
          return c.map(x=>[x.sub.name,x.atraso,x.dias,Math.round(x.urg)]);
        }""")
        for nome,at,dias,urg in r:
            print('   %-13s venceu ha %-6s parado ha %-5s urgencia %d'
                  %(nome,('—' if at is None else str(at)+'d'),str(dias)+'d',urg))
        vencidos_=[x for x in r if x[1]]
        semprazo=[x for x in r if not x[1]]
        pos=[x[0] for x in r]
        assert all(pos.index(v[0])<pos.index(s[0]) for v in vencidos_ for s in semprazo), r
        print('   OK — os dois vencidos vem antes dos 3 sem prazo, mesmo com 400+ dias parados\n')

        print('=== L) as abas que a fila substituiu sairam ===')
        r2=await page.evaluate("""()=>({
          chips:[].map.call(document.querySelectorAll('#screen-revisions .filter-row .chip'),e=>e.textContent.trim())
        })""")
        print('   abas agora: %s'%r2['chips'])
        assert not any('Atrasadas' in c for c in r2['chips']), r2
        assert not any('Próximos 7' in c for c in r2['chips']), r2
        assert any('Fila de hoje' in c for c in r2['chips'])
        assert any('Dominados' in c for c in r2['chips'])
        print('   OK\n')

        print('=== M) a barra conta quantos venceram ===')
        r3=await page.evaluate("""()=>{renderRevisions();
          const t=document.getElementById('revisions-list').textContent.replace(/\\s+/g,' ');
          return {estado:revEstado(),tem:t.indexOf('com prazo vencido')>=0};}""")
        print('   vencidos no estado: %d · aparece na barra: %s'
              %(r3['estado']['vencidos'],r3['tem']))
        # conta so quem passou do prazo; "vence hoje" (atraso 0) nao entra, e e assim mesmo
        esperado=len([x for x in r if x[1]])
        assert r3['estado']['vencidos']==esperado>=1 and r3['tem'], (r3,esperado)
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(vencidos())

# ---- N: "Assuntos que mais erro em questoes" ocupava o topo da tela inteira, empurrando
# a fila pra baixo em toda visita. Virou aba, ao lado de "Todas".
async def abaErros():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        print('=== N) a caixa de erros virou aba ===')
        r=await page.evaluate("""()=>{
          const tela=document.getElementById('screen-revisions');
          const chips=[].map.call(tela.querySelectorAll('.filter-row .chip'),e=>e.textContent.trim());
          const caixa=document.getElementById('err-assuntos-card');
          const linha=tela.querySelector('.filter-row');
          // a caixa tem que estar DEPOIS dos chips no documento, nao antes
          const depois=!!(linha.compareDocumentPosition(caixa)&Node.DOCUMENT_POSITION_FOLLOWING);
          filterRevs('fila',tela.querySelector('.filter-row .chip'));
          const naFila={caixa:caixa.style.display,lista:document.getElementById('revisions-list').style.display};
          const chipErro=[].find.call(tela.querySelectorAll('.filter-row .chip'),e=>e.textContent.indexOf('Mais erro')>=0);
          chipErro.click();
          const naAba={caixa:caixa.style.display,lista:document.getElementById('revisions-list').style.display,
                       temInput:!!document.getElementById('err-assunto-input')};
          return {chips,depois,naFila,naAba};
        }""")
        print('   abas: %s'%r['chips'])
        print('   a caixa esta depois dos chips no HTML: %s'%r['depois'])
        print('   na Fila de hoje  -> caixa: "%s" · lista: "%s"'%(r['naFila']['caixa'],r['naFila']['lista']))
        print('   na aba Mais erro -> caixa: "%s" · lista: "%s" · campo funciona: %s'
              %(r['naAba']['caixa'],r['naAba']['lista'],r['naAba']['temInput']))
        assert r['depois'], 'a caixa tem que sair de cima da tela'
        assert any('Mais erro' in c for c in r['chips'])
        assert r['naFila']['caixa']=='none' and r['naFila']['lista']!='none'
        assert r['naAba']['caixa']!='none' and r['naAba']['lista']=='none' and r['naAba']['temInput']
        print('   OK\n')

        print('=== N2) registrar um erro continua funcionando na aba ===')
        r2=await page.evaluate("""()=>{
          document.getElementById('err-assunto-input').value='Regencia verbal';
          addErroAssunto();
          const txt=document.getElementById('err-assuntos-list').textContent.replace(/\\s+/g,' ');
          return {n:(db.erroAssuntos||[]).length,txt:txt.slice(0,80)};
        }""")
        print('   registrados: %d · lista: %s'%(r2['n'],r2['txt']))
        assert r2['n']==1 and 'Regencia' in r2['txt']
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(abaErros())
