# 503 em todos os modelos, de novo, e uns 25 no console: cada clique repetia a varredura
# inteira. Duas respostas: disjuntor (nao repetir prova ja feita) e a saida que ja
# funcionou no simulado — gerar no Gemini Pro e colar.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUB='s1'
ARVORE={"texto":"Choque septico","tipo":"inicio","ramos":[
  {"rotulo":None,"no":{"texto":"Suspeita: infeccao + hipotensao","tipo":"acao","ramos":[
    {"rotulo":None,"no":{"texto":"Responde a volume?","tipo":"decisao","ramos":[
      {"rotulo":"Sim","no":{"texto":"Sepse com hipoperfusao","tipo":"fim","ramos":[]}},
      {"rotulo":"Nao","no":{"texto":"Choque septico: vasopressor","tipo":"fim","ramos":[]}}]}}]}}]}

def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':SUB,'name':'Choque septico','priority':100,'studied':True,
           'resumo':{'texto':'CHOQUE SEPTICO:\nReposicao inicial de 30 mL/kg de cristaloide.',
                     'geradoEm':'2026-09-01T10:00:00.000Z','origem':'web'}}]}]}})

MOCK503 = """()=>{
  window.__n=0;
  const real=window.fetch;
  window.fetch=async(u,o)=>{
    if(String(u).indexOf('generativelanguage')<0)return real(u,o);
    window.__n++;
    return new Response(JSON.stringify({error:{message:'This model is currently experiencing high demand.'}}),
      {status:503,headers:{'Content-Type':'application/json'}});
  };
  let h=document.getElementById('fluxo-%s');
  if(!h){h=document.createElement('div');h.id='fluxo-%s';document.body.appendChild(h);}
  openFluxo.add('%s');
  h.innerHTML=fluxoPanelHTML(simFindSub('%s'));
  return true;
}""" % (SUB,SUB,SUB,SUB)

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MOCK503)

        print('=== A) primeira tentativa: varre tudo uma vez (3 + reserva) ===')
        r=await page.evaluate("""async()=>{geminiLimparSobrecarga();window.__n=0;
          let erro=null;
          try{await callGeminiJSON('FAKE','x',false,8192);}catch(e){erro=e.message;}
          return {n:window.__n,erro};}""")
        print('   requisições: %s'%r['n'])
        assert r['n']==4
        print('   OK\n')

        print('=== B) clicar de novo NAO repete a varredura ===')
        r=await page.evaluate("""async()=>{window.__n=0;
          const erros=[];
          for(let i=0;i<5;i++){try{await callGeminiJSON('FAKE','x',false,8192);}catch(e){erros.push(e.message);}}
          return {n:window.__n,msg:erros[0],iguais:erros.every(e=>e===erros[0])};}""")
        print('   5 cliques seguidos -> %s requisições'%r['n'])
        print('   aviso: %s'%r['msg'])
        assert r['n']==0 and 'Não vou repetir' in r['msg'] and 'cole aqui' in r['msg']
        print('   OK\n')

        print('=== C) o fluxograma falha na hora, sem gastar nada ===')
        r=await page.evaluate("""async()=>{window.__n=0;
          const t0=Date.now();
          await generateFluxograma('%s');
          return {n:window.__n,ms:Date.now()-t0,
                  tem:!!(simFindSub('%s').fluxograma)};}"""%(SUB,SUB))
        print('   requisições: %s · tempo: %sms'%(r['n'],r['ms']))
        assert r['n']==0 and r['ms']<1500
        print('   OK\n')

        print('=== D) o painel oferece colar ===')
        r=await page.evaluate("""()=>{const t=document.getElementById('fluxo-%s').textContent;
          return t.indexOf('colar aqui')>=0;}"""%SUB)
        print('   botão presente: %s'%r); assert r
        print('   OK\n')

        print('=== E) o prompt leva o Resumo como material ===')
        r=await page.evaluate("""()=>{const t=fluxoColarPromptTexto('%s');
          return {n:t.length,
            material:t.indexOf('30 mL/kg de cristaloide')>=0,
            assunto:t.indexOf('MINIBOSS/ASSUNTO ESPECÍFICO: Choque septico')>=0,
            formato:t.indexOf('FORMATO EXATO')>=0,
            teto:t.indexOf('No MÁXIMO 25 nós')>=0,
            naoInvente:t.indexOf('Não invente nada que não esteja nele')>=0};}"""%SUB)
        print('   %s caracteres'%r['n'])
        for k,v in r.items():
            if k!='n': print('   %-12s %s'%(k,v))
        assert all(v for k,v in r.items() if k!='n')
        print('   OK\n')

        print('=== F) colar o JSON monta o fluxograma, sem tocar na API ===')
        sujo="Claro! Aqui está:\n```json\n"+json.dumps(ARVORE,ensure_ascii=False)+"\n```"
        r=await page.evaluate("""(txt)=>{window.__n=0;
          fluxoAbrirColar('%s');
          document.getElementById('fluxo-colar-%s').value=txt;
          fluxoColarAplicar('%s');
          const f=simFindSub('%s').fluxograma;
          const t=document.getElementById('fluxo-%s').textContent;
          return {n:window.__n,nos:f?Object.keys(f.nos).length:0,origem:f?f.origem:null,
                  raiz:f?f.nos[f.raizId].texto:null,
                  naTela:t.indexOf('Choque septico: vasopressor')>=0,
                  rodape:t.indexOf('Gerado no Gemini e colado aqui')>=0};}"""%((SUB,)*5),sujo)
        print('   requisições à API: %s'%r['n'])
        print('   nós: %s · raiz: %r · origem: %s'%(r['nos'],r['raiz'],r['origem']))
        print('   desenhou na tela: %s · rodapé diz de onde veio: %s'%(r['naTela'],r['rodape']))
        assert r['n']==0 and r['nos']==5 and r['origem']=='colado'
        assert r['naTela'] and r['rodape']
        print('   OK\n')

        print('=== G) lixo colado nao apaga o fluxograma que ja existe ===')
        r=await page.evaluate("""()=>{
          const antes=Object.keys(simFindSub('%s').fluxograma.nos).length;
          fluxoAbrirColar('%s');
          document.getElementById('fluxo-colar-%s').value='Claro! Vou montar o fluxograma.';
          fluxoColarAplicar('%s');
          const a=Object.keys(simFindSub('%s').fluxograma.nos).length;
          document.getElementById('fluxo-colar-%s').value='{"texto":"so isso","tipo":"inicio","ramos":[]}';
          fluxoColarAplicar('%s');
          const b=Object.keys(simFindSub('%s').fluxograma.nos).length;
          return {antes,semJson:a,umNoSo:b};}"""%((SUB,)*8))
        print('   antes: %s nós · texto sem JSON: %s · árvore de 1 nó: %s'
              %(r['antes'],r['semJson'],r['umNoSo']))
        assert r['antes']==r['semJson']==r['umNoSo']==5
        print('   OK\n')

        print('=== H) o disjuntor expira e uma geração boa o limpa ===')
        r=await page.evaluate("""async()=>{
          const bloqueado=geminiSobrecarregado();
          window.fetch=async(u,o)=>new Response(JSON.stringify({candidates:[{content:{parts:[{text:
            JSON.stringify({texto:'ok',tipo:'inicio',ramos:[]})}]}}]}),{status:200});
          geminiSobrecargaAte=Date.now()-1;      // prazo vencido
          const x=await callGeminiJSON('FAKE','x',false,8192);
          return {bloqueado,depois:geminiSobrecarregado(),ok:!!x.parsed};}""")
        print('   estava bloqueado: %s · gerou depois do prazo: %s · segue bloqueado: %s'
              %(r['bloqueado'],r['ok'],r['depois']))
        assert r['bloqueado'] and r['ok'] and not r['depois']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
