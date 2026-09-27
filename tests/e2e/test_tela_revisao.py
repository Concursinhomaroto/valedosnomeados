# "Revisar" jogava no miniboss inteiro (cronometro, simulado, flashcards, edicao) e
# revisar virava uma hora. Com 326 assuntos isso e 31% de cobertura contra 92% a 20 min.
# A tela de revisao mostra so resumo + fluxograma + os botoes de responder.
# Aqui: (1) abre com o material, (2) comunica o que falta e oferece gerar OU ir ao
# miniboss, (3) responder conclui e reagenda, (4) gerar dali funciona e a tela se atualiza.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

FLUXO={'raizId':'n1','nos':{
  'n1':{'texto':'Suspeita de choque','tipo':'inicio','ramos':[{'rotulo':'pele fria','to':'n2'},
                                                              {'rotulo':'pele quente','to':'n3'}]},
  'n2':{'texto':'Hipovolemico ou cardiogenico','tipo':'acao','ramos':[]},
  'n3':{'texto':'Distributivo','tipo':'acao','ramos':[]}}}
RESUMO={'texto':'CLASSIFICACAO DOS CHOQUES: O choque e classificado em quatro tipos.\n\n'
                'Na pratica: vitima de trauma com hemorragia evolui com taquicardia.',
        'geradoEm':'2026-08-01T10:00:00Z','origem':'web'}
SUBS=[
 {'id':'s1','name':'Choque','priority':70,'studied':True,'studiedAt':'2026-05-01',
  'resumo':RESUMO,'fluxograma':FLUXO,
  'simStats':{'tentativas':2,'questoesTotal':30,'acertosTotal':14}},
 {'id':'s2','name':'BCG','priority':70,'studied':True,'studiedAt':'2026-05-01'},          # sem nada
 {'id':'s3','name':'Crase','priority':70,'studied':True,'studiedAt':'2026-05-01',
  'resumo':RESUMO},                                                                        # so resumo
]
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'🏥'}],
  'topics':{'k1':[{'id':'t1','name':'Urgencia','subtopics':SUBS}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.route('**generativelanguage.googleapis.com/**', lambda r: asyncio.ensure_future(
          r.fulfill(status=200,content_type='application/json',body=json.dumps({'candidates':[{'content':{'parts':[
            {'text':'SINAIS DE ALERTA: taquicardia vem antes da queda de pressao.'}]},'finishReason':'STOP'}]}))))
        await page.route('**api.tavily.com/**', lambda r: asyncio.ensure_future(
          r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))

        print('=== A) assunto completo: resumo e fluxograma na mesma tela ===')
        r=await page.evaluate("""async()=>{
          revAbrirTela('s1');
          await new Promise(r=>setTimeout(r,200));
          const m=document.getElementById('modal');
          const h=document.getElementById('modal-body').innerHTML;
          return {largo:m.classList.contains('modal-wide'),aberto:m.classList.contains('open'),
                  titulo:document.getElementById('modal-title').textContent,
                  temResumoH:h.indexOf('resumo-h')>=0, temPratica:h.indexOf('resumo-pratica')>=0,
                  nosFluxo:document.querySelectorAll('#revfluxo-s1 .fluxo-node').length,
                  svg:document.querySelectorAll('#revfluxo-s1 svg').length,
                  botoes:[].map.call(document.querySelectorAll('.revtela-rodape .btn'),e=>e.textContent.trim()),
                  cab:document.getElementById('modal-body').textContent.slice(0,120)};
        }""")
        print('   modal largo: %s | titulo: %s'%(r['largo'],r['titulo'].strip()))
        print('   resumo formatado (titulo+Na pratica): %s / %s'%(r['temResumoH'],r['temPratica']))
        print('   nos do fluxograma desenhados: %d (svg de ligacao: %d)'%(r['nosFluxo'],r['svg']))
        print('   rodape: %s'%r['botoes'])
        print('   cabecalho: %s'%' '.join(r['cab'].split())[:110])
        assert r['largo'] and r['temResumoH'] and r['temPratica']
        assert r['nosFluxo']>=3, r['nosFluxo']
        assert any('Revisei' in x for x in r['botoes']) and any('Esqueci' in x for x in r['botoes'])
        assert any('miniboss' in x for x in r['botoes'])
        print('   OK\n')

        print('=== B) sem resumo e sem fluxograma: comunica e oferece os dois caminhos ===')
        r2=await page.evaluate("""async()=>{
          revFecharTela(); revAbrirTela('s2');
          await new Promise(r=>setTimeout(r,150));
          const h=document.getElementById('modal-body');
          return {vazios:h.querySelectorAll('.revtela-vazio').length,
                  txt:' '.join=undefined||h.textContent.replace(/\\s+/g,' '),
                  gerar:[].map.call(h.querySelectorAll('.revtela-vazio .btn'),e=>e.textContent.trim())};
        }""")
        print('   blocos "falta material": %d'%r2['vazios'])
        print('   botoes oferecidos: %s'%r2['gerar'])
        assert r2['vazios']==2, r2['vazios']
        assert 'ainda não tem resumo' in r2['txt'] and 'ainda não tem fluxograma' in r2['txt']
        assert any('Gerar resumo' in x for x in r2['gerar']) and any('Gerar fluxograma' in x for x in r2['gerar'])
        assert sum(1 for x in r2['gerar'] if 'miniboss' in x)==2
        print('   OK\n')

        print('=== C) so um dos dois faltando ===')
        r3=await page.evaluate("""async()=>{
          revFecharTela(); revAbrirTela('s3');
          await new Promise(r=>setTimeout(r,150));
          const h=document.getElementById('modal-body');
          return {vazios:h.querySelectorAll('.revtela-vazio').length,
                  temResumo:h.innerHTML.indexOf('resumo-h')>=0,
                  txt:h.textContent.replace(/\\s+/g,' ')};
        }""")
        print('   resumo aparece: %s | blocos vazios: %d'%(r3['temResumo'],r3['vazios']))
        assert r3['temResumo'] and r3['vazios']==1
        assert 'ainda não tem fluxograma' in r3['txt']
        print('   OK\n')

        print('=== D) responder da tela conclui, reagenda e fecha ===')
        r4=await page.evaluate("""async()=>{
          revFecharTela(); revAbrirTela('s1');
          await new Promise(r=>setTimeout(r,150));
          revTelaResponder('s1',1);
          await new Promise(r=>setTimeout(r,200));
          const revs=db.revisions['s1']||[];
          const pend=revs.filter(r=>!r.completed);
          const m=document.getElementById('modal');
          return {feitas:revs.filter(r=>r.completed).length,
                  nota:(revs.filter(r=>r.completed).pop()||{}).quality,
                  volta:pend.length?daysDiff(todayStr(),pend[pend.length-1].date):null,
                  fechou:!m.classList.contains('open'),largoLimpo:!m.classList.contains('modal-wide')};
        }""")
        print('   concluidas: %d · nota gravada: %s · volta em %s dia(s)'
              %(r4['feitas'],r4['nota'],r4['volta']))
        print('   modal fechou: %s · classe larga removida: %s'%(r4['fechou'],r4['largoLimpo']))
        assert r4['feitas']==1 and r4['nota']==1 and r4['volta']<=7
        assert r4['fechou'] and r4['largoLimpo']
        print('   OK\n')

        print('=== E) gerar resumo sem sair da revisao ===')
        r5=await page.evaluate("""async()=>{
          revFecharTela(); revAbrirTela('s2');
          await new Promise(r=>setTimeout(r,150));
          revTelaGerar('s2','resumo');
          await new Promise(r=>setTimeout(r,120));
          const durante=document.getElementById('modal-body').textContent.indexOf('Gerando o resumo')>=0;
          for(let i=0;i<60;i++){ if(!resumoGenerating.has('s2'))break; await new Promise(r=>setTimeout(r,150)); }
          await new Promise(r=>setTimeout(r,1200));
          const h=document.getElementById('modal-body');
          return {durante, salvou:!!(simFindSub('s2').resumo||{}).texto,
                  apareceu:h.innerHTML.indexOf('resumo-h')>=0,
                  aindaAberto:document.getElementById('modal').classList.contains('open')};
        }""")
        print('   mostrou "Gerando o resumo...": %s'%r5['durante'])
        print('   resumo salvo: %s · tela se atualizou sozinha: %s · modal seguiu aberto: %s'
              %(r5['salvou'],r5['apareceu'],r5['aindaAberto']))
        assert r5['durante'] and r5['salvou'] and r5['apareceu'] and r5['aindaAberto']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
