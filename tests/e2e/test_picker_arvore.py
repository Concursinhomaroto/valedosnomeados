# A lista de assuntos do Simulado Geral vira arvore dobravel + busca.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K1='k1'; K2='k2'

def seed():
    def chefao(i,nome,prio,n):
        return {'id':f't{i}','name':nome,'icon':'⚔️','priority':prio,
                'subtopics':[{'id':f's{i}_{j}','name':f'{nome} — assunto {j}','priority':70,'studied':True}
                             for j in range(n)]}
    return make_seed({'studyNickname':'R','studyCharacter':'ash',
        'kingdoms':[{'id':K1,'name':'Enfermagem','icon':'💉'},{'id':K2,'name':'Português','icon':'📘'}],
        'topics':{K1:[chefao(0,'Urgência e Emergência',3,24),
                      chefao(1,'Vacinação',2,18),
                      chefao(2,'Saúde Mental',1,20)],
                  K2:[chefao(3,'Morfologia',3,12)]}})

CONSTS = '''()=>{
  window.CLICA_T1='[data-chefao="t1"] .sg-linha';
  window.CLICA_K2='[data-reino="k2"] .sg-linha';
  window.BLOCO_K2='[data-reino="k2"]';
  return true;
}'''

MEDE = '''()=>{
  const box=document.getElementById('sg-picker');
  const r=box.getBoundingClientRect();
  const visiveis=el=>el.offsetParent!==null;
  return {alturaCaixa:Math.round(r.height), rolando:box.scrollHeight>box.clientHeight+2,
          linhasVisiveis:[...box.querySelectorAll('.sg-linha,.sg-sub-row')].filter(visiveis).length,
          assuntosVisiveis:[...box.querySelectorAll('.sg-sub-row')].filter(visiveis).length,
          chefoesVisiveis:[...box.querySelectorAll('.sg-linha-chefao')].filter(visiveis).length};
}'''

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.set_viewport_size({'width':1400,'height':900})
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            await page.evaluate(CONSTS)

            print('=== estado inicial: chefões fechados ===')
            m=await page.evaluate(MEDE)
            print(' ',m)
            assert m['assuntosVisiveis']==0, 'os assuntos deviam nascer fechados'
            assert m['chefoesVisiveis']==4, m
            assert not m['rolando'], 'a lista fechada não devia precisar de rolagem'
            print('  ✓ 74 assuntos cabem em 4 linhas de chefão, sem rolagem')

            print('\n=== abrir um chefão mostra só os assuntos dele ===')
            await page.evaluate("()=>document.querySelector(CLICA_T1).click()")
            await page.wait_for_timeout(200)
            m2=await page.evaluate(MEDE)
            print(' ',m2)
            assert m2['assuntosVisiveis']==18, m2
            assert m2['chefoesVisiveis']==4, 'os outros chefões continuam à vista'
            print('  ✓ abre 18 assuntos e os outros 3 chefões seguem visíveis')

            print('\n=== contador da linha dobrada ===')
            await page.evaluate("()=>sgToggleChefao('t1',true)")
            c=await page.evaluate('''()=>({chefao:document.getElementById('sg-cont-t-t1').textContent,
              reino:document.getElementById('sg-cont-k-k1').textContent,
              cbChefao:document.querySelector('[data-chefao-cb="t1"]').checked,
              cbReino:document.querySelector('[data-reino-cb="k1"]').indeterminate,
              resumo:document.getElementById('sg-summary').textContent.trim(),
              custo:(document.getElementById('sg-custo')||{}).textContent})''')
            print(' ',json.dumps(c,ensure_ascii=False,indent=1))
            assert c['chefao']=='18/18' and c['reino']=='18/62', c
            assert c['cbChefao'] and c['cbReino'], 'estado do checkbox pai errado'
            assert '18 de 74' in c['resumo'], c['resumo']
            # fechar o chefão não pode esconder a informação
            await page.evaluate("()=>document.querySelector(CLICA_T1).click()")
            await page.wait_for_timeout(150)
            fechado=await page.evaluate("()=>document.getElementById('sg-cont-t-t1').textContent")
            assert fechado=='18/18', fechado
            print('  ✓ fechado, o chefão continua dizendo 18/18')

            print('\n=== busca por nome ===')
            await page.evaluate("()=>sgFiltrar('vacinação — assunto 7')")
            await page.wait_for_timeout(200)
            b=await page.evaluate(MEDE)
            print(' ',b)
            assert b['assuntosVisiveis']==1, b
            assert b['chefoesVisiveis']==1, 'só o chefão que tem o assunto devia sobrar'
            print('  ✓ acha 1 assunto entre 74 e abre o bloco sozinho')

            print('\n=== "Limpar" limpa tudo; "Marcar todos" respeita o filtro ===')
            # com a busca ativa, Limpar tem que zerar inclusive o que esta escondido
            antes=await page.evaluate("()=>simGeralConfig.selectedSubIds.size")
            await page.evaluate("()=>sgMarcarTodos(false)")
            zerou=await page.evaluate("()=>simGeralConfig.selectedSubIds.size")
            print(f'  tinha {antes} selecionados com a busca ativa → Limpar deixou {zerou}')
            assert zerou==0, f'Limpar deixou {zerou} selecionados escondidos para trás'
            await page.evaluate("()=>{sgFiltrar('saúde mental');sgMarcarTodos(true);}")
            n=await page.evaluate("()=>simGeralConfig.selectedSubIds.size")
            print('  Marcar todos com o filtro ativo:',n)
            assert n==20, f'devia marcar só os 20 filtrados, marcou {n}'
            await page.evaluate("()=>sgFiltrar('')")
            await page.wait_for_timeout(150)
            v=await page.evaluate(MEDE)
            assert v['chefoesVisiveis']==4, 'limpar a busca devia trazer todos de volta'
            print('  ✓ marca só o que está à vista, e limpar a busca traz todos de volta')

            print('\n=== busca sem resultado avisa ===')
            await page.evaluate("()=>sgFiltrar('zzzzz')")
            await page.wait_for_timeout(150)
            aviso=await page.evaluate("()=>document.getElementById('sg-vazio').style.display")
            assert aviso=='block', aviso
            await page.evaluate("()=>sgFiltrar('')")
            print('  ✓ mostra "nenhum assunto com esse nome"')

            print('\n=== o estado do reino sobrevive ao re-render ===')
            await page.evaluate("()=>document.querySelector(CLICA_K2).click()")
            await page.wait_for_timeout(150)
            await page.evaluate(CONSTS)
            await page.evaluate("()=>renderSimGeralScreen()")
            await page.wait_for_timeout(300)
            k2=await page.evaluate("()=>document.querySelector(BLOCO_K2).classList.contains('aberto')")
            print('  reino Português continua fechado:',not k2)
            assert not k2, 'o reino fechado reabriu ao redesenhar'
            print('  ✓ fechar um reino fica salvo')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — lista dobrável, com busca, contadores e seleção respeitando o filtro')
        finally:
            await browser.close()
asyncio.run(main())
