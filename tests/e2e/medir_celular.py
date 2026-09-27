import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

KING='k1'; TOPIC='t1'
def seed():
    subs=[{'id':f's{i}','name':f'Assunto {i}','priority':70,'studied':True} for i in range(6)]
    fc={}
    for i in range(40):
        fc[f'fc{i}']={'id':f'fc{i}','mbId':TOPIC,'pergunta':f'Pergunta bem comprida numero {i} sobre o regime juridico dos servidores civis do Estado?',
                      'resposta':f'Resposta detalhada numero {i} com varias linhas de conteudo para ocupar espaco de verdade na tela.',
                      'tags':'lei','dificuldade':3,'acertos':0,'erros':0,'lastConf':0,
                      'criacao':'2026-09-01T10:00:00.000Z','ultimaRevisao':None}
    return make_seed({'studyNickname':'Leo','flashcards':fc,
      'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
      'topics':{KING:[{'id':TOPIC,'name':'Lei Estadual 5.247/1991 (Regime Jurídico dos Servidores)','subtopics':subs}]}})

async def main():
    async with async_playwright() as p:
        browser,page,_=await setup_page(p, seed())
        try:
            for w,h,nome in [(393,852,'iPhone 15'),(390,844,'iPhone 13/14'),(360,800,'Android comum')]:
                await page.set_viewport_size({'width':w,'height':h})
                await page.evaluate("() => showScreen('flashcards')")
                await page.wait_for_timeout(700)
                r=await page.evaluate("""() => {
                  const de=document.documentElement;
                  const estoura=[...document.querySelectorAll('.screen.active *')].filter(e=>{
                    const r=e.getBoundingClientRect();
                    return r.width>0 && r.right > window.innerWidth+1;
                  }).map(e=>({c:(typeof e.className==='string'?e.className:e.tagName).split(' ')[0],
                              sobra:Math.round(e.getBoundingClientRect().right-window.innerWidth)}));
                  const vistos={}; estoura.forEach(x=>{if(!vistos[x.c]||vistos[x.c]<x.sobra)vistos[x.c]=x.sobra;});
                  return {rolagemLateral:de.scrollWidth-window.innerWidth,
                          alturaTotal:de.scrollHeight,
                          estourando:vistos};
                }""")
                print(f'{nome} ({w}x{h}): rolagem lateral {r["rolagemLateral"]}px')
                itens=sorted(r['estourando'].items(), key=lambda x:-x[1])[:8]
                print(f'{nome} ({w}x{h}): {len(itens)} elementos passando da borda')
                for c,sob in itens: print(f'    {c or "(sem classe)"} passa {sob}px')
                print()
        finally:
            await browser.close()
asyncio.run(main())
