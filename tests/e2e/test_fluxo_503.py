# "ainda segue com o mesmo erro, sempre e o fluxograma". Os tres Flash voltaram 503
# ("experiencing high demand") e o modelo reserva — o Lite, que e outro pool e tem cota
# bem maior — nunca era tentado: eu tinha deixado o 503 de fora achando que era queda
# geral da Google. Nao e: e pressao de capacidade NAQUELE modelo.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

SUB='s1'
def seed():
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':SUB,'name':'Choque septico','priority':100,'studied':True,
           'resumo':{'texto':'CHOQUE SEPTICO:\nReposicao inicial de 30 mL/kg de cristaloide.',
                     'geradoEm':'2026-09-01T10:00:00.000Z','origem':'web'}}]}]}})

# fetch falso: 503 em tudo que nao for o modelo passado em window.__respondem
MOCK = r"""()=>{
  window.__chamadas=[];
  window.__respondem=[];
  window.__atraso=0;
  const realFetch=window.fetch;
  window.fetch=async(url,opts)=>{
    const u=String(url);
    if(u.indexOf('generativelanguage')<0)return realFetch(url,opts);
    const m=(u.match(/models\/([^:]+):/)||[])[1]||'?';
    window.__chamadas.push(m);
    if(window.__atraso){
      await new Promise((res,rej)=>{
        const t=setTimeout(res,window.__atraso);
        if(opts&&opts.signal)opts.signal.addEventListener('abort',()=>{clearTimeout(t);
          const e=new Error('The operation was aborted.');e.name='AbortError';rej(e);});
      });
    }
    if(window.__respondem.indexOf(m)>=0){
      return new Response(JSON.stringify({candidates:[{content:{parts:[{text:
        JSON.stringify({titulo:'Choque septico',filhos:[{titulo:'Reposicao 30 mL/kg',filhos:[]}]})}]}}]}),
        {status:200,headers:{'Content-Type':'application/json'}});
    }
    return new Response(JSON.stringify({error:{message:'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.'}}),
      {status:503,headers:{'Content-Type':'application/json'}});
  };
  return true;
}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(MOCK)

        print('=== A) a reserva existe e nao esta na fila normal ===')
        r=await page.evaluate("()=>({fila:GEMINI_MODEL_CANDIDATES,reserva:GEMINI_MODELO_RESERVA})")
        print('   fila: %s'%r['fila'])
        print('   reserva: %s'%r['reserva'])
        assert r['reserva'] not in r['fila']
        print('   OK\n')

        print('=== B) 503 nos tres Flash: agora a reserva E tentada, e salva ===')
        r=await page.evaluate("""async()=>{
          geminiLimparSobrecarga(); window.__chamadas=[]; window.__respondem=[GEMINI_MODELO_RESERVA];
          let erro=null,parsed=null;
          try{const x=await callGeminiJSON('FAKE','gere um json',false,8192);parsed=x.parsed;}
          catch(e){erro=e.message;}
          return {chamadas:window.__chamadas,parsed,erro};}""")
        print('   requisições: %s'%' → '.join(r['chamadas']))
        print('   resultado: %s'%json.dumps(r['parsed'],ensure_ascii=False))
        assert r['erro'] is None and r['parsed']
        assert len(r['chamadas'])==4 and r['chamadas'][3]=='gemini-flash-lite-latest'
        print('   OK\n')

        print('=== C) o fluxograma inteiro passa a sair no 503 ===')
        r=await page.evaluate("""async()=>{
          geminiLimparSobrecarga(); window.__chamadas=[]; window.__respondem=[GEMINI_MODELO_RESERVA];
          openFluxo.add('%s');
          let h=document.getElementById('fluxo-%s');
          if(!h){h=document.createElement('div');h.id='fluxo-%s';document.body.appendChild(h);}
          await generateFluxograma('%s');
          const s=simFindSub('%s');
          return {chamadas:window.__chamadas.length,
                  temFluxo:!!(s.fluxograma&&s.fluxograma.nos),
                  nos:s.fluxograma?Object.keys(s.fluxograma.nos).length:0};}"""%((SUB,)*5))
        print('   requisições: %s · fluxograma gerado: %s (%s nós)'
              %(r['chamadas'],r['temFluxo'],r['nos']))
        assert r['temFluxo'] and r['nos']>=1 and r['chamadas']==4
        print('   OK\n')

        print('=== D) 503 em TUDO: erro honesto, e nao mais que 4 requisições ===')
        r=await page.evaluate("""async()=>{
          geminiLimparSobrecarga(); window.__chamadas=[]; window.__respondem=[];
          let erro=null;
          try{await callGeminiJSON('FAKE','gere um json',false,8192);}catch(e){erro=e.message;}
          return {chamadas:window.__chamadas,erro};}""")
        print('   requisições: %s'%len(r['chamadas']))
        print('   erro: %s'%r['erro'])
        assert len(r['chamadas'])==4
        assert 'sobrecarregada' in r['erro'] and 'reserva' in r['erro']
        assert 'não gastou cota' in r['erro']
        print('   OK\n')

        print('=== E) requisição pendurada é cortada, e conta como temporária ===')
        r=await page.evaluate("""async()=>{
          geminiLimparSobrecarga(); window.__chamadas=[]; window.__respondem=[GEMINI_MODELO_RESERVA];
          window.__atraso=5000;              // servidor pendurado
          window.geminiTimeoutMs=()=>150;    // teto curto só pra este teste
          const t0=Date.now();
          let parsed=null,erro=null;
          try{const x=await callGeminiJSON('FAKE','gere um json',false,8192);parsed=x.parsed;}
          catch(e){erro=e.message;}
          const ms=Date.now()-t0;
          window.__atraso=0;
          return {ms,chamadas:window.__chamadas.length,parsed:!!parsed,erro};}""")
        print('   servidor pendurado em 5s, teto de 150ms -> desistiu em %sms'%r['ms'])
        print('   requisições tentadas: %s · erro: %s'%(r['chamadas'],r['erro']))
        assert r['chamadas']==4, 'o corte tem que contar como temporário e seguir pro próximo'
        assert r['ms']<3000, 'nao pode esperar os 5s do servidor'
        assert 'não respondeu a tempo' in (r['erro'] or ''), r['erro']
        print('   OK\n')

        print('=== F) o teto de espera cresce com o tamanho do pedido ===')
        r=await page.evaluate("""()=>{delete window.geminiTimeoutMs;return null;}""")
        await page.reload()
        await page.wait_for_timeout(1200)
        r=await page.evaluate("()=>[geminiTimeoutMs(8192),geminiTimeoutMs(22200)]")
        print('   pedido normal: %ss · pedido grande: %ss'%(r[0]/1000,r[1]/1000))
        assert r[1]>r[0]
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        await b.close()
        print('OK')

asyncio.run(main())
