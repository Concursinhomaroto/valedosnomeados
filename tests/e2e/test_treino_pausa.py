# -*- coding: utf-8 -*-
# Pausar o tempo dentro do Treinar: o relogio para, nada entra no estudo do dia enquanto pausado, continua de onde parou,
# sobrevive a responder (re-desenho) e nao vaza pra proxima sessao. Botao e tecla P.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from test_treino_filtros import seed, ACERVO

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{window.confirm=()=>true;tf=TF_VAZIO();tfIniciado=true;showScreen('simgeral');renderSimGeralScreen();return true;}")
        await page.evaluate("()=>{const pool=treinoPoolCompleto().slice(0,5);treinoIniciar(pool,{titulo:'Teste'});renderSimGeralScreen();return true;}")

        print('=== A) botao Pausar ao lado do relogio; pausa para o tempo e nao entra no estudo do dia ===')
        r=await page.evaluate("""async()=>{const s=treinoSessao;
          const btn0=document.getElementById('treino-pausa');const txt0=btn0.textContent.trim();
          // simula 3 s correndo
          s.ultimoTick=Date.now()-3000;treinoTempoTick();const seg0=Math.floor(s.seg);
          const lancado0=s.segLancado,estudo0=db.lifetimeSeconds||0;
          treinoPausar();
          const pausado={flag:s.pausado,btn:document.getElementById('treino-pausa').textContent.trim(),relogio:document.getElementById('treino-relogio').textContent,classe:document.querySelector('.treino-sessao-wrap').classList.contains('treino-pausado'),
            lancou:s.segLancado-lancado0,estudo:(db.lifetimeSeconds||0)-estudo0};
          // 10 s "passam" pausado
          s.ultimoTick=Date.now()-4000;treinoTempoTick();treinoTempoTick();
          const segPausado=Math.floor(s.seg),pend=Math.floor(s.segPend);
          treinoPausar();   // continua
          s.ultimoTick=Date.now()-2000;treinoTempoTick();
          return {txt0,seg0,pausado,segPausado,pend,continuou:{flag:s.pausado,btn:document.getElementById('treino-pausa').textContent.trim(),relogio:document.getElementById('treino-relogio').textContent,seg:Math.floor(s.seg)}};}""")
        print('   ',r)
        assert r['txt0']=='Pausar' and r['seg0']>=3 and r['pausado']['flag'] is True and r['pausado']['btn']=='Continuar' and r['pausado']['relogio'].startswith('⏸') and r['pausado']['classe']
        assert r['pausado']['lancou']>=3 and r['pausado']['estudo']>=3,'ao pausar o que ja correu entra no estudo do dia'
        assert r['segPausado']==r['seg0'] and r['pend']==0,'pausado nao soma nada'
        assert r['continuou']['flag'] is False and r['continuou']['btn']=='Pausar' and r['continuou']['relogio'].startswith('⏱') and r['continuou']['seg']>=r['seg0']+2
        print('   OK\n')

        print('=== B) tecla P pausa e continua; nao age dentro de campo de texto ===')
        r=await page.evaluate("""()=>{const s=treinoSessao;const ev=(k,alvo)=>{const e=new KeyboardEvent('keydown',{key:k,bubbles:true});Object.defineProperty(e,'target',{value:alvo||document.body});treinoAtalhoTeclado(e);};
          ev('p');const a=s.pausado;ev('P');const b=s.pausado;
          const ta=document.createElement('textarea');ev('p',ta);const c=s.pausado;
          const e2=new KeyboardEvent('keydown',{key:'p',ctrlKey:true});treinoAtalhoTeclado(e2);const d=s.pausado;return {a,b,c,d};}""")
        print('   ',r); assert r=={'a':True,'b':False,'c':False,'d':False}
        print('   OK\n')

        print('=== C) pausar, responder (re-desenho) e continuar: o estado se mantem; tempo nao conta pausado ===')
        r=await page.evaluate("""()=>{const s=treinoSessao;treinoPausar();
          treinoSelecionar(s.itens[s.idx].alternativas[0].letra);treinoConfirmarResposta();
          const depois={flag:s.pausado,btn:document.getElementById('treino-pausa').textContent.trim(),classe:document.querySelector('.treino-sessao-wrap').classList.contains('treino-pausado'),relogio:document.getElementById('treino-relogio').textContent.startsWith('⏸'),resp:s.respondidas};
          const seg=s.seg;s.ultimoTick=Date.now()-3000;treinoTempoTick();const parado=s.seg===seg;
          treinoProxima();const proxima={flag:s.pausado,idx:s.idx};
          treinoPausar();return {depois,parado,proxima,flag:s.pausado};}""")
        print('   ',r)
        assert r['depois']['flag'] and r['depois']['btn']=='Continuar' and r['depois']['classe'] and r['depois']['relogio'] and r['depois']['resp']==1 and r['parado'] and r['proxima']['flag'] and r['flag'] is False
        print('   OK\n')

        print('=== D) nova sessao comeca sem pausa; celular sem rolar de lado ===')
        r=await page.evaluate("""()=>{treinoSessao.pausado=true;treinoSessao=null;treinoResumo=null;renderSimGeralScreen();
          treinoIniciar(treinoPoolCompleto().slice(0,3),{titulo:'Outra'});renderSimGeralScreen();return {flag:treinoSessao.pausado,btn:document.getElementById('treino-pausa').textContent.trim()};}""")
        print('   ',r); assert r=={'flag':False,'btn':'Pausar'}
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>{treinoPausar();return {w:document.documentElement.scrollWidth,iw:innerWidth};}")
        print('   ',r); assert r['w']<=r['iw']+1
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
