# Conteudo vindo da IA (alimentada por paginas da web via Tavily) nao pode executar.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='s1'; TOPIC='t1'; KING='k1'
PAY = '<img src=x onerror="window.__X=(window.__X||0)+1">'

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Sepse','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Choque séptico','priority':100,'studied':True}]}]}})

RESUMO = '''([id,p])=>{
  const s=simFindSub(id);
  s.resumo={texto:'Reposicao inicial 2 mL/kg. '+p, geradoEm:new Date().toISOString(),
            fontes:[{url:'https://x/"onmouseover="window.__X=(window.__X||0)+1',titulo:'Titulo '+p},
                    {url:'javascript:window.__X=(window.__X||0)+1',titulo:'Link ruim'}],
            consultas:['consulta '+p], grounded:true, via:'tavily'};
  openResumo.add(id);
  let h=document.getElementById('resumo-'+id);
  if(!h){h=document.createElement('div');h.id='resumo-'+id;document.body.appendChild(h);}
  h.innerHTML=resumoPanelHTML(s);
  const body=h.querySelector('.resumo-body');
  const links=[...h.querySelectorAll('.resumo-fontes-lista a')];
  const link=links[0];
  return {temImg:!!h.querySelector('img'),
          textoVisivel:body?body.textContent.trim():null,
          href:link?link.getAttribute('href'):null,
          onmouseover:link?link.getAttribute('onmouseover'):null,
          hrefs:links.map(a=>a.getAttribute('href'))};
}'''

QUESTAO = '''([id,p])=>{
  simActive[id]={questoes:[{questao:'Enunciado '+p,
    alternativas:[{letra:'A',texto:'alt '+p},{letra:'B',texto:'b'}],
    correta:'A',explicacao:'expl '+p,userAnswer:'B'}],quantidade:1,corrected:true,histId:'h1'};
  let h=document.getElementById('sim-'+id);
  if(!h){h=document.createElement('div');h.id='sim-'+id;document.body.appendChild(h);}
  h.innerHTML=simPanelHTML(simFindSub(id));
  const t=h.querySelector('.sim-q-text');
  return {temImg:!!h.querySelector('img'), textoVisivel:t?t.textContent.trim():null};
}'''

FLASH = '''([p])=>{
  db.flashcards={fc1:{id:'fc1',mbId:'t1',pergunta:'Pergunta '+p,resposta:'Resposta '+p,
    tags:'',dificuldade:2,acertos:0,erros:0,lastConf:0,criacao:new Date().toISOString(),ultimaRevisao:null}};
  fcSelectedMb=db.topics.k1[0];
  showScreen('flashcards');
  return true;
}'''

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            r1=await page.evaluate(RESUMO,[SUB,PAY])
            r2=await page.evaluate(QUESTAO,[SUB,PAY])
            await page.evaluate(FLASH,[PAY])
            await page.wait_for_timeout(800)
            x=await page.evaluate("()=>window.__X||0")
            corpo=await page.evaluate("()=>document.body.innerHTML.length")

            print('resumo  ->', json.dumps(r1,ensure_ascii=False))
            print('questao ->', json.dumps(r2,ensure_ascii=False))
            print('\nhandlers que executaram:', x)

            assert x==0, f'{x} manipulador(es) ainda executaram'
            assert not r1['temImg'], 'a tag ainda virou elemento no resumo'
            assert not r2['temImg'], 'a tag ainda virou elemento na questão'
            # o texto legítimo continua legível, e a tag aparece como texto
            assert '2 mL/kg' in r1['textoVisivel'], r1['textoVisivel']
            assert '<img' in r1['textoVisivel'], 'a tag devia aparecer como texto literal'
            assert '&lt;' not in r1['textoVisivel'], 'escapou duas vezes (aparece &lt; na tela)'
            assert 'Enunciado' in r2['textoVisivel'], r2['textoVisivel']
            # href da fonte: sem quebra de atributo, sem javascript:
            assert r1['onmouseover'] is None, f'a URL quebrou o atributo: {r1["onmouseover"]}'
            print('href da 1a fonte:', r1['href'])
            print('hrefs das fontes:', r1['hrefs'])
            assert not any(str(h).lower().startswith('javascript:') for h in r1['hrefs']), r1['hrefs']
            assert r1['hrefs'][1]=='#', f'o link javascript: devia virar #, veio {r1["hrefs"][1]}'
            assert not real_errors(errors), real_errors(errors)
            print('\nOK — conteúdo da IA e das fontes é exibido como texto, nunca executado')
        finally:
            await browser.close()
asyncio.run(main())
