import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1';S='s1';S2='s2'

def card(i,sub,q,a,cri,ac=0,er=0):
    return {'id':i,'mbId':T,'subId':sub,'pergunta':q,'resposta':a,'tags':'','dificuldade':2,
            'acertos':ac,'erros':er,'lastConf':0,'criacao':cri,'ultimaRevisao':None}

FC={c['id']:c for c in [
  # par 1: texto identico. O VELHO tem historico -> sugestao e apagar o novo.
  card('v1',S,'Qual a meta de PAM no choque séptico?','65 mmHg.','2026-01-01T10:00:00Z',ac=4,er=1),
  card('n1',S,'Qual a meta de PAM, no choque séptico','65 mmHg.','2026-02-01T10:00:00Z'),
  # par 2: parecidas. O NOVO e que tem historico -> sugestao tem que inverter.
  card('v2',S,'Qual o prazo para iniciar o antibiótico na sepse?','1 hora.','2026-01-02T10:00:00Z'),
  card('n2',S,'Qual é o prazo para iniciar os antibióticos na sepse?','1 hora.','2026-02-02T10:00:00Z',ac=9,er=2),
  # par 3: FALSO POSITIVO classico - tem que dar pra dizer "sao diferentes"
  card('v3',S,'Qual a classificação de risco da dengue grupo A?','Sem sinais de alarme.','2026-01-03T10:00:00Z'),
  card('n3',S,'Qual a classificação de risco da dengue grupo B?','Com comorbidade.','2026-02-03T10:00:00Z'),
  # controle: assunto DIFERENTE com a mesma pergunta do par 1 -> nao pode parear
  card('o1',S2,'Qual a meta de PAM no choque séptico?','65 mmHg.','2026-01-04T10:00:00Z'),
  card('o2',S2,'Pergunta solta do outro assunto','X.','2026-01-05T10:00:00Z'),
]}
seed=make_seed({'studyNickname':'Leo','flashcards':FC,
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'Urgência','subtopics':[
    {'id':S,'name':'Choque Séptico','priority':70,'studied':True},
    {'id':S2,'name':'Trauma','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            pares=await page.evaluate("""()=>{
              const all=Object.values(db.flashcards);
              return fcAcharPares(all).map(p=>({a:p.a.id,b:p.b.id,exato:p.exato,acao:p.acao,sugerido:p.sugerido}));}""")
            print('1) pares achados:',len(pares))
            for x in pares: print('    ',x)
            assert len(pares)==3, f'esperava 3 pares, veio {len(pares)}'
            byb={p['b']:p for p in pares}
            assert byb['n1']['exato'] is True and byb['n1']['acao']=='b', 'par identico: devia sugerir apagar o novo'
            # Par apenas PARECIDO entra sem marcacao ('pular'): so texto identico ja vem
            # sugerido. A sugestao continua existindo em .sugerido, poupando quem tem
            # historico de estudo — ela so nao e aplicada sozinha.
            assert byb['n2']['sugerido']=='a', 'a sugestao devia poupar o card com historico (n2)'
            assert byb['n2']['acao']=='pular', 'par so parecido nao pode vir marcado pra apagar'
            assert byb['n3']['exato'] is False and byb['n3']['acao']=='pular'
            print('2) sugestao poupa quem tem historico, e parecidas entram sem marca -> ok')
            print('3) mesma pergunta em OUTRO assunto nao foi pareada ->', 'o1' not in [p['a'] for p in pares]+[p['b'] for p in pares])
            assert 'o1' not in [p['a'] for p in pares]+[p['b'] for p in pares]

            # abre o modal de verdade
            await page.evaluate("()=>fcRevisarDupChefao()")
            await page.wait_for_timeout(300)
            aberto=await page.evaluate("()=>document.getElementById('modal').classList.contains('open')")
            radios=await page.evaluate("()=>document.querySelectorAll('#modal-body .dup-op').length")
            print('4) modal abriu:',aberto,'| opcoes na tela:',radios,'(3 por par x 3 pares)')
            assert aberto and radios==9

            # par 3 e falso positivo: marca "sao diferentes"
            idx=[i for i,x in enumerate(pares) if x['b']=='n3'][0]
            await page.evaluate("(i)=>fcDupEscolha(i,'nenhum')",idx)
            rot=await page.evaluate("()=>document.querySelector('.dup-rodape .btn-danger').innerText.trim()")
            print('5) rotulo do botao depois de liberar 1 par ->',repr(rot))
            assert 'Apagar 1' in rot and 'liberar 1' in rot

            await page.evaluate("()=>fcDupAplicar()")
            await page.wait_for_timeout(300)
            r=await page.evaluate("""()=>({ids:Object.keys(db.flashcards).sort(),
              nr:(db.flashcards.v3&&db.flashcards.v3.naoRepete)||[]})""")
            print('6) cards que sobraram:',r['ids'])
            # so o par identico estava marcado, entao so n1 sai; v2/n2 ficam pra decidir
            assert r['ids']==['n2','n3','o1','o2','v1','v2','v3'], r['ids']
            assert 'n3' in r['nr'], 'par liberado nao foi gravado'
            print('7) par liberado gravado em v3.naoRepete ->',r['nr'])

            # nao pode voltar a aparecer
            restam=await page.evaluate("()=>fcAcharPares(Object.values(db.flashcards)).length")
            print('8) pares restantes depois da revisao ->',restam,'(o par liberado sumiu; o nao decidido fica)')
            assert restam==1, f'esperava so o par sem decisao, veio {restam}'
            marc=await page.evaluate("()=>flashSuspeitasDup(Object.values(db.flashcards).filter(c=>c.subId==='%s')).size" % S)
            print('9) marcas laranja restantes ->',marc,'(o par liberado saiu)')
            assert marc==1

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
