# O painel ainda falava a lingua do modelo antigo: "DIVIDA DE REVISAO · 76 revisoes
# atrasadas", contado por getAllRevItems() (por data), sem saber de reino desligado nem
# de assunto dominado. E o botao "Atacar as 5 mais antigas" procurava a aba 'overdue',
# que deixou de existir — estava quebrado.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
def mb(i,nome):
    return {'id':'s%d'%i,'name':nome,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
seed=make_seed({'studyNickname':'Leo',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'🏥'},
              {'id':'k2','name':'Historia','icon':'🏰'}],
  'topics':{'k1':[{'id':'t1','name':'Centro Cirurgico','subtopics':[mb(1,'Pre-operatorio'),mb(2,'Transoperatorio'),mb(3,'Drenos')]}],
            'k2':[{'id':'t2','name':'Colonia','subtopics':[mb(4,'Capitanias'),mb(5,'Bandeirantes')]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{
          const d=n=>{const x=new Date();x.setDate(x.getDate()-n);return x.toISOString().slice(0,10);};
          db.revisions={};
          ['s1','s2','s3','s4','s5'].forEach(id=>{
            db.revisions[id]=[{date:d(90),completed:true,quality:4},{date:d(5),completed:false}];
          });
          db.revOrcamentoMin=60; db.revCustoMin=20;   // 3 por dia
          showScreen('dashboard');
        }""")
        await page.wait_for_timeout(300)

        print('=== A) o cartao conta pela mesma regua da Camara ===')
        r=await page.evaluate("""()=>({
          txt:document.getElementById('divida-resumo').textContent.replace(/\\s+/g,' ').trim(),
          titulo:[].map.call(document.querySelectorAll('.dash-sec'),e=>e.textContent.trim()).filter(t=>t.indexOf('Revis')>=0),
          fila:revCandidatos().length, estado:revEstado()})""")
        print('   titulo do cartao: %s'%r['titulo'])
        print('   cartao: %s'%r['txt'][:150])
        assert not any('Dívida' in t for t in r['titulo']), r['titulo']
        assert '5' in r['txt'] and 'prazo vencido' in r['txt'] and 'ciclo' in r['txt']
        assert 'atrasada' not in r['txt'], r['txt']
        print('   OK\n')

        print('=== B) reino desligado e assunto dominado somem da conta ===')
        r2=await page.evaluate("""()=>{
          const antes=revCandidatos().length;
          revToggleReino('k2'); revDominar('s3',true);
          showScreen('dashboard');
          const txt=document.getElementById('divida-resumo').textContent.replace(/\\s+/g,' ');
          const rec=computeStudyRecommendations().map(x=>x.subName);
          return {antes,depois:revCandidatos().length,txt:txt.slice(0,90),
                  temHistoria:rec.indexOf('Capitanias')>=0, temDominado:rec.indexOf('Drenos')>=0};
        }""")
        print('   na vez: %d -> %d'%(r2['antes'],r2['depois']))
        print('   cartao agora: %s'%r2['txt'])
        print('   "O que estudar agora" recomenda Historia? %s · dominado? %s'
              %(r2['temHistoria'],r2['temDominado']))
        assert r2['antes']==5 and r2['depois']==2
        assert not r2['temHistoria'] and not r2['temDominado']
        print('   OK\n')

        print('=== C) o botao do cartao leva pra Fila de hoje (estava quebrado) ===')
        r3=await page.evaluate("""async()=>{
          const btn=document.querySelector('#divida-resumo .div-btn');
          const rotulo=btn.textContent.trim();
          btn.click();
          await new Promise(r=>setTimeout(r,300));
          const tela=document.querySelector('.screen.active').id;
          const ativa=(document.querySelector('#screen-revisions .filter-row .chip.active')||{}).textContent;
          return {rotulo,tela,ativa:(ativa||'').trim(),
                  itens:document.querySelectorAll('#revisions-list .rev-name').length};
        }""")
        print('   botao: "%s" -> tela %s, aba "%s", %d itens'
              %(r3['rotulo'],r3['tela'],r3['ativa'],r3['itens']))
        assert r3['tela']=='screen-revisions' and 'Fila de hoje' in r3['ativa'] and r3['itens']>0
        print('   OK\n')

        print('=== D) as acoes do cartao sao as da fila ===')
        r4=await page.evaluate("""async()=>{
          revToggleReino('k2'); revDominar('s3',false);   // devolve tudo
          showScreen('dashboard'); await new Promise(r=>setTimeout(r,200));
          const linhas=document.querySelectorAll('#dash-overdue-revs .rev-item');
          const antes=revCandidatos().length;
          linhas[0].querySelector('.btn-green-s').click();
          await new Promise(r=>setTimeout(r,250));
          return {n:linhas.length,antes,depois:revCandidatos().length,
                  semJaReestudei:document.getElementById('dash-overdue-revs').innerHTML.indexOf('resetarRevisoes')<0};
        }""")
        print('   amostra no cartao: %d linhas · "✓" tirou da fila: %d -> %d'
              %(r4['n'],r4['antes'],r4['depois']))
        print('   botao "Ja reestudei" removido: %s'%r4['semJaReestudei'])
        assert r4['depois']==r4['antes']-1 and r4['semJaReestudei']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())

# ---- E/F/G: a OUTRA caixa do painel (renderNextSteps) ainda falava a lingua antiga —
# chamava-se "Fila de hoje" sem ser a fila, mostrava "revisão · 2d" e mandava todo mundo
# pro miniboss inteiro.
async def caixaEsquerda():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("""()=>{
          const d=n=>{const x=new Date();x.setDate(x.getDate()-n);return x.toISOString().slice(0,10);};
          db.revisions={};
          ['s1','s2'].forEach(id=>db.revisions[id]=[{date:d(90),completed:true,quality:4},{date:d(4),completed:false}]);
          // s3 com prazo LA NA FRENTE: nao pode virar recomendacao de revisao
          db.revisions['s3']=[{date:d(90),completed:true,quality:4},{date:'2027-01-01',completed:false}];
          // s4/s5 nunca estudados
          [simFindSub('s4'),simFindSub('s5')].forEach(x=>{x.studied=false;});
          showScreen('dashboard');
        }""")
        await page.wait_for_timeout(300)

        print('=== E) o nome nao colide mais com a fila de verdade ===')
        r=await page.evaluate("""()=>({
          titulos:[].map.call(document.querySelectorAll('.dash-sec'),e=>e.textContent.trim()),
          conta:document.getElementById('fila-conta').textContent.replace(/\\s+/g,' ').trim()})""")
        print('   titulos do painel: %s'%[t for t in r['titulos'] if 'fazer' in t or 'Revis' in t])
        print('   cabecalho: %s'%r['conta'])
        assert not any(t=='🧭 Fila de hoje' for t in r['titulos']), r['titulos']
        assert any('O que fazer agora' in t for t in r['titulos'])
        assert 'revis' in r['conta'] and 'por estudar' in r['conta']
        assert 'revisãoões' not in r['conta'], ('plural montado errado',r['conta'])
        print('   OK\n')

        print('=== F) o chip diz do que e o prazo, e so entra quem esta na vez ===')
        r2=await page.evaluate("""()=>{
          const rec=computeStudyRecommendations();
          const chips=[].map.call(document.querySelectorAll('#next-steps-list .fila-chip'),e=>e.textContent.trim());
          return {chips,revs:rec.filter(x=>x.tipo==='revisao').map(x=>[x.subName,x.reason]),
                  temS3:rec.some(x=>x.subId==='s3'&&x.tipo==='revisao')};
        }""")
        print('   chips: %s'%r2['chips'])
        print('   itens de revisao: %s'%r2['revs'])
        print('   assunto com prazo em 2027 virou revisao? %s'%r2['temS3'])
        assert not any('revisão ·' in c for c in r2['chips']), r2['chips']
        assert any('venceu há' in c for c in r2['chips']), r2['chips']
        assert not r2['temS3']
        print('   OK\n')

        print('=== G) clicar numa revisao abre a TELA de revisao ===')
        r3=await page.evaluate("""async()=>{
          const itens=[].slice.call(document.querySelectorAll('#next-steps-list .next-step-item'));
          const rec=computeStudyRecommendations();
          const iRev=rec.findIndex(x=>x.tipo==='revisao');
          const iNovo=rec.findIndex(x=>x.tipo==='novo');
          const onRev=itens[iRev].getAttribute('onclick');
          const onNovo=iNovo>=0&&iNovo<itens.length?itens[iNovo].getAttribute('onclick'):'';
          itens[iRev].click(); await new Promise(r=>setTimeout(r,250));
          const aberto=document.getElementById('modal').classList.contains('open');
          const largo=document.getElementById('modal').classList.contains('modal-wide');
          revFecharTela();
          return {onRev,onNovo,aberto,largo};
        }""")
        print('   revisao -> %s'%r3['onRev'])
        print('   nunca estudado -> %s'%(r3['onNovo'] or '(nao estava entre os 8)'))
        print('   abriu a tela de revisao: %s (modal largo: %s)'%(r3['aberto'],r3['largo']))
        assert 'revAbrirTela' in r3['onRev'] and r3['aberto'] and r3['largo']
        if r3['onNovo']: assert 'goToSubtopic' in r3['onNovo']
        print('   OK\n')
        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(caixaEsquerda())
