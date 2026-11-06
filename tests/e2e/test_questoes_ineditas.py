# -*- coding: utf-8 -*-
# Treinar > Questoes ineditas: gera o prompt (miniboss escolhido, formato, banca/estilo, ja tenho...) e importa a resposta da IA.
import asyncio, sys, json
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
from test_treino_filtros import seed, ACERVO

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        await page.evaluate("()=>{tf=TF_VAZIO();tfIniciado=true;tq.aberto=true;window.confirm=()=>true;showScreen('simgeral');renderSimGeralScreen();return true;}")

        print('=== A) o cartao existe em Treinar; Mundo > Chefe > Miniboss; prompt so libera com o alvo ===')
        r=await page.evaluate("""()=>{const c=document.getElementById('tq-card');const antes=c.querySelector('.tq-passo:nth-of-type(3) button').disabled;
          tqSet('mundo','Enfermagem');const ch=tqChefes().map(x=>x.name);tqSet('chefe','t1');const mi=tqMinis().map(x=>x.name);
          const dep=document.getElementById('tq-card').querySelector('.tq-passo:nth-of-type(3) button').disabled;
          return {existe:!!c,antes,ch,mi,dep,alvos:tqAlvos().length};}""")
        print('   ',r)
        assert r['existe'] and r['antes'] is True and r['ch']==['Saúde da Mulher','Saúde da Criança'] and r['mi']==['Pré-natal','Puerpério'] and r['dep'] is False and r['alvos']==2
        print('   OK\n')

        print('=== B) conteudo do prompt: lista numerada, formato, banca/estilo, ja tenho, regras de procedencia ===')
        r=await page.evaluate("""()=>{tqSet('qtd','12');const t=tqPromptTexto();
          tqAlternarMini('s2',true);const um=tqPromptTexto();
          tqTodosMinis();tqSet('fmt','multipla');tqSet('banca','FGV');const mu=tqPromptTexto();
          tqSet('banca','__outra__');tqSet('outra','AOCP');tqSet('real',true);tqSet('ano','2025');tqSet('prova','Prefeitura X, Enfermeiro, 2025');const real=tqPromptTexto();
          return {t,um:um.includes('1. Puerpério')&&!um.includes('Pré-natal'),mu,real};}""")
        t=r['t']
        for trecho in ['EXATAMENTE 12','itens de julgamento CERTO/ERRADO','1. Pré-natal','2. Puerpério','Saúde da Mulher','"banca":"Cebraspe (estilo)"','JÁ TENHO ESTAS','já tenho 4','NÃO invente ano nem nome de prova','"assuntoNome":"Pré-natal"','"afirmacao"','Responda APENAS com um array JSON','CONTINUA — faltam N itens','textoApoio']:
            assert trecho in t,trecho
        assert r['um']
        assert 'questões de múltipla escolha, de A a E' in r['mu'] and '"alternativas"' in r['mu'] and 'estilo FGV' in r['mu'] and '"banca":"FGV (estilo)"' in r['mu'] and 'promptRecorte' not in r['mu']
        assert 'estilo AOCP' in r['real'] and '"banca":"AOCP"' in r['real'] and '"ano":2025' in r['real'] and 'Prefeitura X, Enfermeiro, 2025' in r['real'] and 'prova real' in r['real']
        print('   prompt de %d caracteres'%len(t))
        print('   OK\n')

        print('=== C) importar: nome, numero do prompt, assunto desconhecido, gabarito invalido, repetida ===')
        await page.evaluate("()=>{tqSet('banca','Cebraspe');tqSet('real',false);tqSet('ano','');tqSet('prova','');tqSet('fmt','certoerrado');tqPromptTexto();return true;}")
        J=[
          {"assunto":1,"assuntoNome":"Pré-natal","afirmacao":"A primeira consulta de pré-natal deve ocorrer até a 12ª semana.","gabarito":"C","explicacao":"Ok.","fonte":"MS 2024"},
          {"assunto":2,"assuntoNome":"Puerpério","afirmacao":"O puerpério imediato vai até 10 dias após o parto.","gabarito":"C","explicacao":"Ok.","banca":"IDECAN","ano":2025,"prova":"Prova Y"},
          {"assunto":2,"afirmacao":"Item sem nome, so o numero 2 do prompt.","gabarito":"E","explicacao":"Ok."},
          {"assunto":9,"assuntoNome":"Assunto que nao existe de jeito nenhum","afirmacao":"Item de assunto desconhecido.","gabarito":"C","explicacao":"Ok."},
          {"assunto":1,"assuntoNome":"Pré-natal","afirmacao":"Item com gabarito invalido.","gabarito":"TALVEZ","explicacao":"Ok."},
          {"assunto":1,"assuntoNome":"Pré-natal","afirmacao":"A primeira consulta de pré-natal deve ocorrer até a 12ª semana.","gabarito":"C","explicacao":"Ok."}]
        r=await page.evaluate("""(j)=>{document.getElementById('tq-txt').value=JSON.stringify(j);const n0=db.acervo.length;tqImportar();
          const novas=db.acervo.filter(q=>/primeira consulta de pré-natal deve|puerpério imediato|Item sem nome/.test(q.questao));
          const por=t=>{const q=db.acervo.find(x=>x.questao.includes(t));return q&&{sub:q.subId,reino:q.kingdomName,chefe:q.topicName,banca:q.banca,ano:q.ano||null,prova:q.prova||null,origem:q.origem,fonte:q.fonte||null};};
          const rel=tq.resultado;return {cresceu:db.acervo.length-n0,rel,pend:tq.pend.map(x=>[x.nome,x.itens.length]),a:por('primeira consulta'),b:por('puerpério imediato'),c:por('Item sem nome'),
            html:document.getElementById('tq-card').innerText.includes('lidas = 3 novas + 1 já existentes + 1 aguardando assunto + 1 descartadas')};}""",J)
        print('   ',r['rel'],r['pend']); print('   ',r['a'],r['b'],r['c'])
        assert r['cresceu']==3 and r['rel']['novas']==3 and r['rel']['repetidas']==1 and r['rel']['lidas']==6 and r['rel']['pendentes']==1
        assert r['pend']==[['Assunto que nao existe de jeito nenhum',1]] and r['rel']['descartadas']=={'enunciado ou gabarito inválido':1}
        assert r['a']['sub']=='s1' and r['a']['banca']=='Cebraspe (estilo)' and r['a']['ano'] is None and r['a']['reino']=='Enfermagem' and r['a']['chefe']=='Saúde da Mulher' and r['a']['fonte']=='MS 2024'
        assert r['b']['sub']=='s2' and r['b']['banca']=='IDECAN' and r['b']['ano']==2025 and r['b']['prova']=='Prova Y','o que a IA preencheu vale mais que o padrao'
        assert r['c']['sub']=='s2','sem nome: usa o numero do prompt'
        assert r['html']
        print('   OK\n')

        print('=== D) pendente: escolher o assunto; resultado fecha a conta; treinar com as novas ===')
        r=await page.evaluate("""()=>{const sel=document.getElementById('tq-pend-0');sel.value='s3';tqPendenteUsar(0);
          const q=db.acervo.find(x=>x.questao.includes('assunto desconhecido'));const rel=tq.resultado;
          const salvo=(window.__root.users.TEST_UID_LEO.vdn_acervo||[]).filter(x=>x.banca==='Cebraspe (estilo)').length;
          tqTreinarNovas();const s=treinoSessao;const res={sub:q&&q.subId,pend:tq.pend.length,rel:[rel.novas,rel.pendentes],itens:s&&s.itens.length,titulo:s&&s.titulo,salvo};
          treinoSessao=null;treinoResumo=null;renderSimGeralScreen();return res;}""")
        print('   ',r)
        assert r['sub']=='s3' and r['pend']==0 and r['rel']==[4,0] and r['itens']==4 and r['titulo']=='Questões inéditas' and r['salvo']>=2
        print('   OK\n')

        print('=== E) JSON cortado aproveita o que esta inteiro; texto invalido e lote grande sao recusados; sem XSS ===')
        r=await page.evaluate("""()=>{const out={};const ta=()=>document.getElementById('tq-txt');
          ta().value='[{"assunto":1,"assuntoNome":"Pré-natal","afirmacao":"Item cortado A inteiro e valido.","gabarito":"C","explicacao":"."},{"assunto":1,"assuntoNome":"Pré-natal","afirmacao":"Item cortado B que fica pela met';
          const n0=db.acervo.length;tqImportar();out.cortado=db.acervo.length-n0;
          ta().value='isto nao e json';const n1=db.acervo.length;tqImportar();out.lixo=db.acervo.length-n1;
          ta().value=JSON.stringify(Array.from({length:501},(_,i)=>({assunto:1,afirmacao:'x'+i,gabarito:'C'})));const n2=db.acervo.length;tqImportar();out.grande=db.acervo.length-n2;
          ta().value=JSON.stringify([{assunto:1,assuntoNome:'Pré-natal',afirmacao:'<img src=x onerror=alert(1)> afirmação com html.',gabarito:'E',explicacao:'.'}]);tqImportar();
          out.xss=!document.getElementById('tq-card').innerHTML.includes('<img src=x');
          return out;}""")
        print('   ',r)
        assert r['cortado']==1 and r['lixo']==0 and r['grande']==0 and r['xss']
        print('   OK\n')

        print('=== F) celular: nada rola de lado; copiar prompt devolve o texto ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{tqRender();const w=document.documentElement.scrollWidth;const t=tqCopiarPrompt();return {w,iw:innerWidth,ok:typeof t==='string'&&t.length>2000};}""")
        print('   ',r); assert r['w']<=r['iw']+1 and r['ok']
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
