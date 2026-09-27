# Achado 02: data da proxima revisao de flashcard em Brasilia, nao em UTC.
# Achado 03: questao com gabarito impossivel nao entra no simulado.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='s1'; TOPIC='t1'; KING='k1'

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Sepse','icon':'⚔️','subtopics':[
            {'id':SUB,'name':'Choque séptico','priority':100,'studied':True}]}]}})

DATAS = '''()=>{
  const casos=[
    {rot:'22h de Brasília (01:00Z do dia seguinte)', ts:'2026-09-05T01:00:00.000Z', dia:1, esperado:'2026-09-05'},
    {rot:'23h59 de Brasília',                        ts:'2026-09-05T02:59:00.000Z', dia:1, esperado:'2026-09-05'},
    {rot:'meio-dia de Brasília',                     ts:'2026-09-04T15:00:00.000Z', dia:1, esperado:'2026-09-05'},
    {rot:'00h30 de Brasília',                        ts:'2026-09-05T03:30:00.000Z', dia:6, esperado:'2026-09-11'},
  ];
  return casos.map(c=>({...c,
    obtido:fcNextReview({acertos:1,erros:0,sm2:{interval:c.dia},ultimaRevisao:c.ts})}));
}'''

VENCIMENTO = '''()=>{
  // carta revisada ontem as 22h, intervalo 1 -> tem que estar vencida hoje
  const ontem=new Date(); ontem.setDate(ontem.getDate()-1);
  const ts=new Date(Date.UTC(ontem.getFullYear(),ontem.getMonth(),ontem.getDate()+1,1,0,0)).toISOString();
  const card={acertos:1,erros:0,sm2:{interval:1},ultimaRevisao:ts};
  return {carimbo:ts, proxima:fcNextReview(card), hoje:todayStr(), status:fcStatus(card)};
}'''

GABARITO = '''()=>{
  const alts5=['A','B','C','D','E'].map(l=>({letra:l,texto:'texto '+l}));
  const casos=[
    {rot:'gabarito fora das alternativas', q:{questao:'X?',alternativas:[{letra:'A',texto:'a'},{letra:'B',texto:'b'}],correta:'F'}},
    {rot:'uma alternativa só',             q:{questao:'X?',alternativas:[{letra:'A',texto:'a'}],correta:'A'}},
    {rot:'letras repetidas',               q:{questao:'X?',alternativas:[{letra:'A',texto:'a'},{letra:'A',texto:'b'}],correta:'A'}},
    {rot:'alternativa sem texto',          q:{questao:'X?',alternativas:[{letra:'A',texto:''},{letra:'B',texto:''}],correta:'A'}},
    {rot:'normal, 5 alternativas',         q:{questao:'X?',alternativas:alts5,correta:'C'}},
    {rot:'gabarito em minúscula',          q:{questao:'X?',alternativas:alts5,correta:'c'}},
    {rot:'gabarito escrito "B)"',          q:{questao:'X?',alternativas:alts5,correta:'B)'}},
    {rot:'gabarito veio como TEXTO',       q:{questao:'X?',alternativas:alts5,correta:'Texto D'}},
    {rot:'texto ambíguo (2 iguais)',       q:{questao:'X?',alternativas:[{letra:'A',texto:'igual'},{letra:'B',texto:'igual'}],correta:'igual'}},
  ];
  return casos.map(c=>{
    const r=simNormalizaQuestao(c.q,'multipla');
    return {rot:c.rot, aceitou:!!r, correta:r?r.correta:null, n:r?r.alternativas.length:0};
  });
}'''

def resp(itens):
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            print('=== Achado 02: data da próxima revisão ===')
            for c in await page.evaluate(DATAS):
                ok='✓' if c['obtido']==c['esperado'] else '✗'
                print(f"  {ok} {c['rot']:<42} +{c['dia']}d → {c['obtido']} (esperado {c['esperado']})")
                assert c['obtido']==c['esperado'], c

            v=await page.evaluate(VENCIMENTO)
            print(f"  carta de ontem 22h → vence {v['proxima']}, hoje é {v['hoje']}, status: {v['status']}")
            assert v['status']=='due', f"devia estar vencida hoje, veio {v['status']}"
            print('  ✓ quem estuda à noite não perde mais um dia de revisão')

            print('\n=== Achado 03: validação do gabarito ===')
            esperado={'gabarito fora das alternativas':None,'uma alternativa só':None,
                      'letras repetidas':None,'alternativa sem texto':None,
                      'normal, 5 alternativas':'C','gabarito em minúscula':'C',
                      'gabarito escrito "B)"':'B','gabarito veio como TEXTO':'D',
                      'texto ambíguo (2 iguais)':None}
            for r in await page.evaluate(GABARITO):
                alvo=esperado[r['rot']]
                ok='✓' if r['correta']==alvo else '✗'
                print(f"  {ok} {r['rot']:<34} aceitou={str(r['aceitou']):<5} correta={r['correta']}")
                assert r['correta']==alvo, (r,alvo)

            # o laço de geração repõe o que foi descartado
            print('\n=== o simulado ainda sai com a quantidade pedida ===')
            chamadas={'n':0}
            async def gem(route, request):
                chamadas['n']+=1
                if chamadas['n']==1:
                    # 5 questões, 3 delas com gabarito impossível
                    itens=[{'questao':f'Ruim {i}?','alternativas':[{'letra':'A','texto':'a'},{'letra':'B','texto':'b'}],
                            'correta':'F'} for i in range(3)]
                    itens+=[{'questao':f'Boa {i}?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
                             'correta':'A','explicacao':'x'} for i in range(2)]
                else:
                    itens=[{'questao':f'Reposta {chamadas["n"]}-{i}?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
                            'correta':'B','explicacao':'x'} for i in range(3)]
                await route.fulfill(status=200, content_type='application/json', body=resp(itens))
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            r=await page.evaluate('''async ()=>{
              const k=db.kingdoms[0], t=db.topics[k.id][0], s=t.subtopics[0];
              const out=await generateQuestionsForSubject('FAKE',k,t,s,5,{formato:'multipla',pesquisar:false});
              return {n:out.questoes.length,
                      todasValidas:out.questoes.every(q=>q.alternativas.some(a=>a.letra===q.correta))};
            }''')
            print(f"  chamadas ao modelo: {chamadas['n']} | questões entregues: {r['n']}")
            assert r['n']==5, f"esperava 5 questões, veio {r['n']}"
            assert r['todasValidas'], 'entrou questão sem gabarito válido'
            print('  ✓ as 3 ruins foram descartadas e repostas — o simulado saiu completo e respondível')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — revisão de flashcard no dia certo e simulado sem questão impossível')
        finally:
            await browser.close()
asyncio.run(main())
