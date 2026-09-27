# Chefoes de prioridade alta primeiro; e o botao "Intensivo" dizendo o que faz.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

KING='k1'

def seed():
    # criados fora de ordem de proposito: baixa, alta, media, alta, baixa, media
    plano=[('Saúde do Homem',1),('Urgência e Emergência',3),('Vacinação',2),
           ('Legislação de Enfermagem',3),('Saúde Ocupacional',1),('Saúde Mental',2)]
    topics=[{'id':f't{i}','name':n,'icon':'⚔️','priority':p,
             'subtopics':[{'id':f's{i}','name':f'Miniboss de {n}','priority':70,'studied':True}]}
            for i,(n,p) in enumerate(plano)]
    return make_seed({'studyNickname':'R','studyCharacter':'ash',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:topics},
        'revisions':{'s1':[{'date':'2099-01-01','completed':False}],
                     's3':[{'date':'2099-01-01','completed':False}]}})

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);renderTopics();}",[KING])
            await page.wait_for_timeout(300)

            r=await page.evaluate('''()=>{
              const cards=[...document.querySelectorAll('#topics-list .topic-card')];
              return {tela:cards.map(c=>({
                        nome:c.querySelector('.topic-name-el').textContent.trim(),
                        fogo:(c.querySelector('[title="Prioridade"]')||{}).textContent.length})),
                      gravado:db.topics.k1.map(t=>t.name)};
            }''')
            print('=== ordem na tela ===')
            for t in r['tela']: print(f"  {'🔥'*t['fogo']:<9} {t['nome']}")
            nomes=[t['nome'] for t in r['tela']]
            prios=[t['fogo'] for t in r['tela']]
            assert prios==sorted(prios,reverse=True), prios
            # dentro da mesma prioridade, a ordem de criação é preservada
            assert nomes[:2]==['Urgência e Emergência','Legislação de Enfermagem'], nomes[:2]
            assert nomes[2:4]==['Vacinação','Saúde Mental'], nomes[2:4]
            assert nomes[4:]==['Saúde do Homem','Saúde Ocupacional'], nomes[4:]
            print('  ✓ alta → média → baixa, e ordem de criação preservada dentro da faixa')

            print('\n=== a lista gravada NÃO foi reordenada ===')
            print(' ',r['gravado'])
            assert r['gravado']==['Saúde do Homem','Urgência e Emergência','Vacinação',
                                 'Legislação de Enfermagem','Saúde Ocupacional','Saúde Mental'], r['gravado']
            print('  ✓ a tela ordena uma cópia; o banco continua na ordem de criação')

            print('\n=== o Simulado Geral usa a mesma ordem ===')
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            sg=await page.evaluate("()=>[...document.querySelectorAll('#sg-picker .sg-linha-chefao .sg-linha-nome')].map(e=>e.textContent.trim())")
            print(' ',sg)
            assert [x.replace('⚔️ ','') for x in sg][:2]==['Urgência e Emergência','Legislação de Enfermagem'], sg
            print('  ✓ mesma ordem nas duas telas')

            print('\n=== botão explica o que faz ===')
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);showScreen('kingdom');renderTopics();}",[KING])
            await page.wait_for_timeout(300)
            b=await page.evaluate('''()=>{
              const btn=[...document.querySelectorAll('#topics-list button')].find(x=>/Revisar hoje/.test(x.textContent));
              return btn?{rotulo:btn.textContent.trim(),dica:btn.getAttribute('title')}:null;}''')
            print(' ',json.dumps(b,ensure_ascii=False))
            assert b and 'Revisar hoje' in b['rotulo'], b
            assert b['dica'] and 'HOJE' in b['dica'], b
            print('  ✓ rótulo e dica dizem o que o botão faz')

            print('\n=== o que o botão faz, na prática ===')
            # t1 tem revisão marcada para 2099 -> deve ser antecipada para hoje
            antes=await page.evaluate("()=>db.revisions.s1[0].date")
            await page.evaluate("()=>intensiveTraining('t1')")
            depois=await page.evaluate("()=>({s1:db.revisions.s1[0].date,hoje:todayStr()})")
            print(f"  revisão de s1: {antes} → {depois['s1']} (hoje é {depois['hoje']})")
            assert depois['s1']==depois['hoje'], depois
            # rodar de novo não empilha nada
            n1=await page.evaluate("()=>db.revisions.s1.length")
            await page.evaluate("()=>intensiveTraining('t1')")
            n2=await page.evaluate("()=>db.revisions.s1.length")
            assert n1==n2==1, (n1,n2)
            print('  ✓ antecipa a revisão pendente e, repetindo, não empilha fila')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — chefões por prioridade e botão "Revisar hoje" explicado')
        finally:
            await browser.close()
asyncio.run(main())
