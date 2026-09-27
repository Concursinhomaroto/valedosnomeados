import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def fc(i,mb,ac,er): return {'id':i,'mbId':mb,'pergunta':'p'+i,'resposta':'r','dificuldade':2,
                            'acertos':ac,'erros':er,'lastConf':0,'criacao':'2026-01-01T10:00:00Z'}
# Historia: 1 acerto / 7 erros = 12%, mas so 8 revisoes -> amostra minuscula
# Enfermagem: 177/300 = 59% com 300 revisoes -> esse sim e o problema real
# Portugues: 100% em 2 revisoes -> tambem nao pode virar "reino modelo"
FC={}
FC['h']=fc('h','th',1,7)
FC['e']=fc('e','te',177,123)
FC['p']=fc('p','tp',2,0)
seed=make_seed({'studyNickname':'Leo','flashcards':FC,
  'kingdoms':[{'id':'kh','name':'História','icon':'🕌'},
              {'id':'ke','name':'Enfermagem','icon':'💊'},
              {'id':'kp','name':'Português','icon':'📖'}],
  'topics':{'kh':[{'id':'th','name':'T','subtopics':[]}],
            'ke':[{'id':'te','name':'T','subtopics':[]}],
            'kp':[{'id':'tp','name':'T','subtopics':[]}]}})

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            await page.evaluate("()=>renderKingdomsNeedingAttention()")
            await page.wait_for_timeout(200)
            linhas=await page.evaluate("""()=>[...document.querySelectorAll('#avg-time-list .atencao-item')].map(d=>({
              nome:d.querySelector('.atencao-nome').textContent.trim(),
              pct:d.querySelector('.atencao-pct b')?.textContent.trim(),
              cor:d.querySelector('.atencao-pct b')?getComputedStyle(d.querySelector('.atencao-pct b')).color:null,
              sub:d.querySelector('.atencao-pct small')?.textContent.trim()}))""")
            for l in linhas: print('   ',l)
            nomes=[l['nome'] for l in linhas]
            print('\n1) ordem ->',nomes)
            assert nomes[0]=='Enfermagem', f'o reino com amostra de verdade tem que vir primeiro, veio {nomes[0]}'
            h=[l for l in linhas if l['nome']=='História'][0]
            e=[l for l in linhas if l['nome']=='Enfermagem'][0]
            print('2) História ->',h['pct'],'|',h['sub'])
            assert h['pct']=='13%' and '8 revisões' in h['sub'] and 'pouco' in h['sub']
            print('3) História sai em cinza (não grita vermelho) ->',h['cor'])
            assert h['cor']!=e['cor'], 'amostra pequena tem que sair em cor neutra'
            print('4) Enfermagem ->',e['pct'],'|',e['sub'])
            assert e['pct']=='59%' and '300 revisões' in e['sub']
            leg=await page.evaluate("()=>document.querySelector('.atencao-legenda')?.textContent.trim()")
            print('5) legenda ->',repr(leg))
            assert 'acerto nos flashcards desde sempre' in leg and 'não é quanto do reino' in leg
            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
