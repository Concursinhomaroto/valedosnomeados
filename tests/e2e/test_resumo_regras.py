# Duas regras novas no prompt do resumo:
#  - numero sempre em algarismo ("36 graus", nao "trinta e seis graus")
#  - nao afirmar competencia profissional (quem pode executar) sem estar no material
# Os 4 prompts de resumo tem que carregar as duas, e o LEMBRETE FINAL — que e a ultima
# coisa que o modelo le — tambem.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'studyNickname':'Leo'}))

        print('=== A) os 4 prompts de resumo carregam as duas regras ===')
        r=await page.evaluate("""()=>{
          const ps={
            unico:resumoPromptUnico('CTX','MATERIAL'),
            parcial:resumoPromptParcial('CTX','MATERIAL',1,3),
            consolida:resumoPromptConsolida('CTX',['a','b']),
            web:resumoPromptWeb('CTX','')};
          const out={};
          for(const k in ps)out[k]={
            num:ps[k].indexOf('algarismo')>=0,
            comp:ps[k].indexOf('competência profissional')>=0};
          return out;}""")
        for k,v in r.items():
            print('   %-10s algarismo:%s  competencia:%s'%(k,v['num'],v['comp']))
            assert v['num'] and v['comp'], k
        print('   OK\n')

        print('=== B) o LEMBRETE FINAL (ultima coisa lida) tem as regras 4 e 5 ===')
        r=await page.evaluate("""()=>({
          titulo:RESUMO_FECHAMENTO.indexOf('LEMBRETE FINAL —')>=0,
          r4:RESUMO_FECHAMENTO.indexOf('TODO número vai em ALGARISMO')>=0,
          r5:RESUMO_FECHAMENTO.indexOf('quem pode ou não pode executar')>=0,
          cofen:RESUMO_FECHAMENTO.indexOf('COFEN')>=0,
          sondagem:RESUMO_FECHAMENTO.indexOf('privativa')>=0})""")
        print('   %s'%r)
        assert r['titulo'] and r['r4'] and r['r5'] and r['cofen']
        print('   OK\n')

        print('=== C) o exemplo dentro do lembrete nao contraria a regra 4 ===')
        # o exemplo e a ultima coisa que o modelo le; se ele mesmo escrever numero por
        # extenso, e ele que o modelo vai copiar.
        r=await page.evaluate("""()=>{
          const ex=RESUMO_FECHAMENTO.split('Exemplo do formato esperado:')[1]||'';
          const ruins=['um','dois','três','quatro','cinco','seis','sete','oito','nove','dez',
                       'vinte','trinta','quarenta','cinquenta','cem','mil'];
          const achou=ruins.filter(w=>new RegExp('\\\\b'+w+'\\\\b','i').test(ex));
          return {ex:ex.trim(),achou};}""")
        print('   numeros por extenso no exemplo: %s'%(r['achou'] or 'nenhum'))
        assert not r['achou'], r['achou']
        print('   OK\n')

        print('=== D) o fechamento continua sendo colado DEPOIS do material ===')
        r=await page.evaluate("""()=>{
          const p=resumoPromptUnico('CTX','MATERIAL_AQUI')+RESUMO_FECHAMENTO;
          return {depois:p.lastIndexOf('MATERIAL_AQUI')<p.indexOf('LEMBRETE FINAL —'),
                  fim:p.trim().endsWith('choque hipovolêmico.')};}""")
        print('   lembrete depois do material: %s · termina no exemplo: %s'%(r['depois'],r['fim']))
        assert r['depois'] and r['fim']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
