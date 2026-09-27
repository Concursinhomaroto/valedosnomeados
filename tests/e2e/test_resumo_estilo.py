import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

async def main():
    async with async_playwright() as p:
        browser,page,_=await setup_page(p, make_seed({'studyNickname':'Leo'}))
        try:
            await page.set_viewport_size({'width':1600,'height':900})
            r=await page.evaluate("""() => {
              const cartao=document.createElement('div');
              cartao.style.width='1100px'; cartao.style.position='fixed'; cartao.style.top='0';
              const el=document.createElement('div');
              el.className='resumo-body';
              el.textContent=('palavra '.repeat(600));
              cartao.appendChild(el); document.body.appendChild(cartao);
              const cs=getComputedStyle(el);
              const b=el.getBoundingClientRect(), pai=cartao.getBoundingClientRect();
              const cv=document.createElement('canvas').getContext('2d');
              cv.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;
              const out={maxHeight:cs.maxHeight, overflowY:cs.overflowY,
                fonte:cs.fontSize, alturaLinha:cs.lineHeight,
                cortado: el.scrollHeight>el.clientHeight+2,
                chars: Math.round(b.width/cv.measureText('0').width),
                folgaEsq: Math.round(b.left-pai.left), folgaDir: Math.round(pai.right-b.right)};
              cartao.remove(); return out;
            }""")
            print('resumo-body ->', r)
            assert r['maxHeight']=='none', f"ainda cortado em {r['maxHeight']}"
            assert not r['cortado'], 'o texto continua com rolagem por dentro'
            # o resumo usa a LARGURA CHEIA do cartao — foi pedido explicitamente
            assert r['folgaEsq']<=2 and r['folgaDir']<=2, \
                f'o resumo voltou a ser estreitado (folga {r["folgaEsq"]}/{r["folgaDir"]}px)'
            print('\nOK — resumo abre inteiro e ocupa a largura cheia do cartão')
        finally:
            await browser.close()
asyncio.run(main())
