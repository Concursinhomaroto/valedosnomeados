import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1'
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
  'topics':{K:[
    {'id':'t1','name':'Saúde Mental','priority':2,'subtopics':[
      {'id':'s1','name':'Esquizofrenia','priority':70},
      {'id':'s2','name':'Transtorno Bipolar','priority':30}]},
    {'id':'t2','name':'Cardiologia','priority':3,'subtopics':[
      {'id':'s3','name':'Parada cardiorrespiratória','priority':100},
      {'id':'s4','name':'Infarto agudo do miocárdio <b>teste</b>','priority':70}]},
    {'id':'t3','name':'Urgência','priority':1,'subtopics':[
      {'id':'s5','name':'Choque séptico','priority':100}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        await page.evaluate("()=>{currentKingdom=db.kingdoms[0];showScreen('kingdom');renderTopics();}")
        await page.wait_for_timeout(400)

        async def busca(termo):
            await page.evaluate("(t)=>{document.getElementById('busca-miniboss').value=t;filtrarReino(t);}",termo)
            await page.wait_for_timeout(250)
            return await page.evaluate("""()=>{
                const cards=[...document.querySelectorAll('.topic-card')];
                return {
                  chefoes:cards.map(c=>c.querySelector('.topic-name-el').textContent.trim()),
                  abertos:cards.filter(c=>c.querySelector('.topic-body').style.display!=='none')
                          .map(c=>c.querySelector('.topic-name-el').textContent.trim()),
                  minisVisiveis:[...document.querySelectorAll('.topic-body')]
                     .filter(b=>b.style.display!=='none')
                     .flatMap(b=>[...b.querySelectorAll('.sub-name')].map(n=>n.textContent.trim())),
                  contador:(document.getElementById('busca-cont')||{}).textContent||'',
                  marcados:[...document.querySelectorAll('.busca-hit')].map(x=>x.textContent),
                  vazio:!!document.querySelector('.empty')};}""")

        for termo,titulo in [('esquizo','miniboss, sem acento e no meio da palavra'),
                             ('CARDIO','casa no chefão E num miniboss de outro'),
                             ('choque','miniboss em chefão de baixa prioridade'),
                             ('xyz','nada encontrado')]:
            r=await busca(termo)
            print('--- busca "%s"  (%s)'%(termo,titulo))
            print('    chefões na lista : %s'%r['chefoes'])
            print('    abertos sozinhos : %s'%r['abertos'])
            print('    minibosses à vista: %s'%r['minisVisiveis'])
            print('    contador: %-22s trecho marcado: %s'%(r['contador'],r['marcados']))
            print()

        r=await busca('')
        print('--- limpou a busca: volta tudo')
        print('    chefões: %s | abertos: %s | contador: %r'%(r['chefoes'],r['abertos'],r['contador']))

        # o nome com HTML nao pode virar tag
        await page.evaluate("()=>{document.getElementById('busca-miniboss').value='infarto';filtrarReino('infarto');}")
        await page.wait_for_timeout(200)
        inj=await page.evaluate("()=>{const n=[...document.querySelectorAll('.sub-name')].find(x=>x.textContent.includes('Infarto'));return {texto:n?n.textContent.trim():null,temTagB:!!(n&&n.querySelector('b'))};}")
        print('\n--- nome com HTML dentro: %r | virou tag <b>? %s'%(inj['texto'],inj['temTagB']))
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
