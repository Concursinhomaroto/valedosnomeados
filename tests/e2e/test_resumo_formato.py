# O formato bom do resumo (titulo em maiuscula destacado + "Na pratica:") so saia em
# ALGUNS resumos. Causa: as regras de formato ficavam ANTES do material no prompt --
# o mesmo erro que ja tinha acontecido no fluxograma (FLUXO_FECHAMENTO).
# Aqui: (1) o lembrete chega no FIM do prompt nos 3 caminhos de resumo,
#       (2) resumoFormatar estiliza titulo colado no texto, que e como a IA escreve.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1'
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Urgencia','subtopics':[
    {'id':'s1','name':'Choque','priority':30,'studied':True}]}]}})

TEXTO_IA=("CLASSIFICACAO DOS CHOQUES: O choque e classificado em quatro tipos conforme o mecanismo.\n\n"
          "Na pratica: Paciente com hemorragia externa evolui com taquicardia.\n\n"
          "CHOQUE HIPOVOLEMICO:\nPerda de volume circulante efetivo.")

async def caminho(p,modo):
    """modo: 'arquivo' | 'tavily' | 'grounding'. Devolve a lista de prompts enviados."""
    seed2=dict(seed)
    b,page,errs=await setup_page(p,seed)
    prompts=[]
    async def g(route,request):
        body=json.loads(request.post_data or '{}')
        prompts.append(body['contents'][0]['parts'][0]['text'])
        await route.fulfill(status=200,content_type='application/json',
          body=json.dumps({'candidates':[{'content':{'parts':[{'text':TEXTO_IA}]},
                                          'finishReason':'STOP'}]}))
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
    tav_hits=[]
    async def tav(route,request):
        tav_hits.append(1)
        await route.fulfill(status=200,content_type='application/json',
          body=json.dumps({'results':[{'url':'https://x.gov.br/a','title':'A',
                                       'content':'conteudo pesquisado '*50}]}))
    await page.route('**api.tavily.com/search**', tav)
    if modo in ('arquivo','arquivo-grande'):
        rep=200 if modo=='arquivo' else 9000   # >60000 chars = cai no caminho fatiado
        await page.evaluate("""rep=>{
          db.tavilyApiKey='';
          const f=new File(['MATERIAL DE ESTUDO. '.repeat(rep)],'mat.txt',{type:'text/plain'});
          return generateResumo('s1',f);
        }""",rep)
    elif modo=='tavily':
        await page.evaluate("()=>{db.tavilyApiKey='TAV';return generateResumoWeb('s1');}")
    else:
        await page.evaluate("()=>{db.tavilyApiKey='';return generateResumoWeb('s1');}")
    for _ in range(100):
        if await page.evaluate("()=>!resumoGenerating.has('s1')"): break
        await page.wait_for_timeout(200)
    tem=await page.evaluate("()=>{const x=simFindSub('s1');return !!(x&&x.resumo&&x.resumo.texto);}")
    await b.close()
    return prompts,tem,len(tav_hits)

async def formata(p,txt):
    b,page,errs=await setup_page(p,seed)
    html=await page.evaluate("t=>resumoFormatar(t)",txt)
    await b.close()
    return html

async def main():
    async with async_playwright() as p:
        print('=== A) o LEMBRETE FINAL chega no fim do prompt nos 3 caminhos ===')
        falhas=[]
        for modo in ('arquivo','arquivo-grande','tavily','grounding'):
            prompts,tem,tav=await caminho(p,modo)
            ult=prompts[-1] if prompts else ''
            perto='LEMBRETE FINAL DE FORMATO' in ult[-1500:]
            print('   %-14s prompts: %d | gerou: %s | lembrete nos ultimos 1500 chars: %s'
                  %(modo,len(prompts),tem,perto))
            if not perto or not tem: falhas.append(modo)
        assert not falhas, 'o lembrete nao chegou ao fim em: %s'%falhas
        print('   OK\n')

        print('=== B) resumoFormatar estiliza o titulo COLADO no texto ===')
        h=await formata(p,TEXTO_IA)
        casos=[
          ('titulo colado vira <h4>', 'resumo-h">CLASSIFICACAO DOS CHOQUES<' in h),
          ('corpo do titulo colado vira <p>', 'resumo-p">O choque e classificado' in h),
          ('titulo sozinho na linha vira <h4>', 'resumo-h">CHOQUE HIPOVOLEMICO<' in h),
          ('"Na pratica:" tem classe propria', 'resumo-pratica' in h),
        ]
        for nome,ok in casos:
            print('   %-38s %s'%(nome,'OK' if ok else 'FALHOU'))
        assert all(ok for _,ok in casos), h[:600]
        print()

        print('=== C) nao confunde frase comum que tem dois-pontos com titulo ===')
        h2=await formata(p,'O paciente apresentou o seguinte: taquicardia e hipotensao.')
        print('   frase mista NAO virou titulo: %s'%('OK' if 'resumo-h' not in h2 else 'FALHOU -> '+h2))
        assert 'resumo-h' not in h2, h2
        h3=await formata(p,'SIGLAS: PCR, SAE e PAV sao siglas usadas na prova.')
        print('   titulo curto em MAIUSCULA colado ainda vira titulo: %s'
              %('OK' if 'resumo-h">SIGLAS<' in h3 else 'FALHOU -> '+h3))
        assert 'resumo-h">SIGLAS<' in h3, h3
        print('\nOK')

asyncio.run(main())
