# -*- coding: utf-8 -*-
# Treinar > "Explicar meu erro com IA": prompt com enunciado/alternativas/gabarito/o que o aluno marcou, resultado na tela e guardado
# na questao, sem chave avisa, erro da IA aparece sem quebrar, nao vaza pra outra questao, texto da IA escapado.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    sub=lambda i,n:{'id':i,'name':n,'priority':70,'studied':True,'studiedAt':'2026-01-01'}
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':[sub('s1','Hérnia inguinal')]}]}})

ACERVO="""()=>{db.acervo=[];
  const mk=(txt,i)=>{const q={questao:txt,correta:'C',formato:'multipla',alternativas:[{letra:'A',texto:'Alt A '+i},{letra:'B',texto:'Alt B '+i},{letra:'C',texto:'Alt C certa '+i},{letra:'D',texto:'Alt D '+i},{letra:'E',texto:'Alt E '+i}],
    explicacao:'Explicacao oficial '+i,subId:'s1',subName:'Hérnia inguinal',topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'x',banca:'IDECAN',ano:2024,prova:'PB Saude'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});};
  mk('A hernia inguinal e comum na pediatria. Qual o manejo?',1);mk('Segunda questao sobre hernia.',2);return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{window.confirm=()=>true;window.__prompts=[];tf=TF_VAZIO();tfIniciado=true;ACERVO_PRONTO=true;showScreen('simgeral');renderSimGeralScreen();treinoIniciar(db.acervo.slice(),{titulo:'T',ordenado:true});renderSimGeralScreen();return true;}")

        print('=== A) so aparece depois de responder; errou -> botao em destaque; sem chave avisa ===')
        r=await page.evaluate("""()=>{const antes=!!document.getElementById('treino-ia-btn');
          const s=treinoSessao;treinoSelecionar('D');treinoConfirmarResposta();
          const btn=document.getElementById('treino-ia-btn');
          db.geminiApiKey='';let aviso='';const t=window.toast;window.toast=(m)=>{aviso=m;};let abriu=false;const o=window.openAISettingsModal;window.openAISettingsModal=()=>{abriu=true;};
          treinoExplicarIA();window.toast=t;window.openAISettingsModal=o;
          return {antes,btn:btn&&btn.textContent.trim(),primario:btn&&btn.className.includes('btn-primary'),aviso,abriu,rodando:treinoIARodando};}""")
        print('   ',r)
        assert r['antes'] is False and r['btn']=='Explicar meu erro com IA' and r['primario'] and 'Sem chave do Gemini' in r['aviso'] and r['abriu'] and r['rodando'] is False
        print('   OK\n')

        print('=== B) gera: prompt completo; resultado na tela e guardado na questao; markdown seguro ===')
        r=await page.evaluate("""async()=>{db.geminiApiKey='CHAVE-DE-TESTE';
          const real=window.callGeminiGenerate;window.callGeminiGenerate=async(k,pr,o)=>{window.__prompts.push({k,pr,o});await new Promise(r=>setTimeout(r,80));
            return '**Por que a certa é certa:** porque sim <img src=x onerror=alert(1)>.\\n**Macete:** hérnia no prematuro = encarcera.\\n- item um\\n- item dois';};
          const s=treinoSessao,item=s.itens[s.idx];
          const p=treinoExplicarIA();const durante={btnDesab:document.getElementById('treino-ia-btn').disabled,txt:document.getElementById('treino-ia-box').innerText};
          await p;window.callGeminiGenerate=real;
          const box=document.getElementById('treino-ia-box');
          return {durante,pr:window.__prompts[0].pr,k:window.__prompts[0].k,max:window.__prompts[0].o&&window.__prompts[0].o.maxOutputTokens,html:box.innerHTML,txt:box.innerText,
            guardado:!!(item.explicacaoIA&&item.explicacaoIA.texto),em:item.explicacaoIA&&item.explicacaoIA.em,btn:document.getElementById('treino-ia-btn').textContent.trim(),desab:document.getElementById('treino-ia-btn').disabled,
            noAcervo:!!db.acervo.find(q=>q.questao.startsWith('A hernia')).explicacaoIA};}""")
        print('   ',{k:r[k] for k in ('durante','k','max','guardado','btn','desab','noAcervo')})
        for t in ['A hernia inguinal e comum na pediatria','D) Alt D 1','C) Alt C certa 1','Gabarito: C','O aluno marcou: D','Explicação que consta na questão: Explicacao oficial 1','Procedência: IDECAN · 2024 · PB Saude','Enfermagem › Urgência › Hérnia inguinal','NO MÁXIMO 180 palavras','não invente número de lei','ERROU']:
            assert t in r['pr'],t
        assert r['k']=='CHAVE-DE-TESTE' and r['max']==900 and r['durante']['btnDesab'] and 'explicando' in r['durante']['txt']
        assert r['guardado'] and r['btn']=='Gerar outra explicação' and r['desab'] is False and r['noAcervo']
        assert '<b>Por que a certa é certa:</b>' in r['html'] and '<img' not in r['html'] and 'item um' in r['txt'] and 'pode errar' in r['txt']
        print('   OK\n')

        print('=== C) volta sozinha ao reabrir a questao; o botao da proxima questao e novo (nao vaza) ===')
        r=await page.evaluate("""()=>{const s=treinoSessao;renderSimGeralScreen();const volta=document.getElementById('treino-ia-box').innerText.includes('Macete');
          treinoProxima();const prox={tem:!!document.getElementById('treino-ia'),box:document.getElementById('treino-ia-box')?document.getElementById('treino-ia-box').innerText:'sem'};
          treinoSelecionar('C');treinoConfirmarResposta();
          const acertou=document.getElementById('treino-ia-btn').textContent.trim();
          return {volta,prox,acertou,box2:document.getElementById('treino-ia-box').innerText};}""")
        print('   ',r)
        assert r['volta'] and r['prox']['tem'] is False and r['acertou']=='Explicar com IA' and r['box2'].strip()==''
        print('   OK\n')

        print('=== D) erro da IA aparece em texto, sem quebrar; da pra tentar de novo; resposta chegando depois de trocar de questao nao suja a tela ===')
        r=await page.evaluate("""async()=>{const real=window.callGeminiGenerate;
          window.callGeminiGenerate=async()=>{throw new Error('Você estourou o limite POR MINUTO <b>x</b>');};
          await treinoExplicarIA();const erro=document.getElementById('treino-ia-box').innerHTML;const livre=treinoIARodando===false&&!document.getElementById('treino-ia-btn').disabled;
          window.callGeminiGenerate=async()=>'';await treinoExplicarIA();const vazio=document.getElementById('treino-ia-box').innerText;
          // resposta lenta: troca de questao no meio
          treinoProxima&&0;
          window.callGeminiGenerate=async()=>{await new Promise(r=>setTimeout(r,200));return 'Resposta lenta.';};
          const s=treinoSessao,item=s.itens[s.idx];const p=treinoExplicarIA();
          treinoAnterior();   // volta pra outra questao enquanto a IA pensa
          await p;window.callGeminiGenerate=real;
          const outroBox=document.getElementById('treino-ia-box');
          return {erro,livre,vazio,item:!!item.explicacaoIA,outroSujo:!!(outroBox&&outroBox.innerText.includes('Resposta lenta'))};}""")
        print('   ',r)
        assert 'limite POR MINUTO' in r['erro'] and '<b>x</b>' not in r['erro'] and r['livre'] and 'não devolveu texto' in r['vazio'] and r['item'] and r['outroSujo'] is False
        print('   OK\n')

        print('=== E) celular: sem rolar de lado ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("()=>({w:document.documentElement.scrollWidth,iw:innerWidth})")
        print('   ',r); assert r['w']<=r['iw']+1
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
