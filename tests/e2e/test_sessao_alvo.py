# "Quando eu minimizo a tela, ele retira o que marquei": floatTimerOpen reconstruia o
# seletor de reino do zero e a escolha ia junto — com o cronometro rodando. O tempo da
# sessao acabaria no lugar errado sem ninguem perceber.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'d'},
                  {'id':'k2','name':'Portugues','icon':'p'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'x','subtopics':[
                        {'id':'u0','name':'Choque','priority':70,'studied':True,'studiedAt':'2026-01-01'}]},
                      {'id':'t2','name':'Legislacao','icon':'x','subtopics':[]}],
                'k2':[{'id':'t3','name':'Gramatica','icon':'x','subtopics':[]}]}})

LER = """()=>({tipo:document.getElementById('ft-tipo').value,
                reino:document.getElementById('ft-reino').value,
                chefao:document.getElementById('ft-chefao').value,
                chefaoTxt:document.getElementById('ft-chefao').selectedOptions[0].textContent.trim()})"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())

        print('=== A) escolher reino + chefao + tipo ===')
        r=await page.evaluate("""()=>{floatTimerOpen();
          const t=document.getElementById('ft-tipo'); t.value='leitura'; ftLembrarAlvo();
          const rr=document.getElementById('ft-reino'); rr.value='k1';
          ftPreencherChefoes(); ftLembrarAlvo();
          const c=document.getElementById('ft-chefao'); c.value='t1'; ftLembrarAlvo();
          return {alvo:ftAlvo,tela:(%s)()};}"""%LER)
        print('   na tela: %s'%r['tela'])
        print('   lembrado: %s'%r['alvo'])
        assert r['tela']['reino']=='k1' and r['tela']['chefao']=='t1'
        print('   OK\n')

        print('=== B) minimizar e reabrir: a escolha continua ===')
        r=await page.evaluate("""()=>{
          ftAccumulated=15; ftRunning=false;          // sessao em andamento
          floatTimerClose();
          floatTimerOpen();
          return {tela:(%s)(),relogio:ftGetElapsed()};}"""%LER)
        print('   depois de fechar e abrir: %s'%r['tela'])
        print('   cronômetro seguiu em %ss'%r['relogio'])
        assert r['tela']['reino']=='k1' and r['tela']['chefao']=='t1' and r['tela']['tipo']=='leitura'
        assert 'Urgencia' in r['tela']['chefaoTxt']
        print('   OK\n')

        print('=== C) trocar de reino zera o chefao (nao carrega o do outro reino) ===')
        r=await page.evaluate("""()=>{
          const rr=document.getElementById('ft-reino'); rr.value='k2';
          ftPreencherChefoes(); ftLembrarAlvo();
          return {tela:(%s)(),opcoes:[...document.getElementById('ft-chefao').options].map(o=>o.textContent.trim())};}"""%LER)
        print('   %s · opções: %s'%(r['tela'],r['opcoes']))
        assert r['tela']['chefao']=='' and len(r['opcoes'])==2
        print('   OK\n')

        print('=== D) a escolha sobrevive ao recarregar a pagina ===')
        r=await page.evaluate("""()=>{
          document.getElementById('ft-reino').value='k1'; ftPreencherChefoes();
          document.getElementById('ft-chefao').value='t2'; ftLembrarAlvo();
          return localStorage.getItem('vdn_ft_alvo');}""")
        print('   gravado: %s'%r)
        await page.reload(); await page.wait_for_timeout(1200)
        r=await page.evaluate("""()=>{floatTimerOpen();return (%s)();}"""%LER)
        print('   depois de recarregar: %s'%r)
        assert r['reino']=='k1' and r['chefao']=='t2'
        print('   OK\n')

        print('=== E) reino apagado nao trava o seletor ===')
        r=await page.evaluate("""()=>{
          db.kingdoms=db.kingdoms.filter(k=>k.id!=='k1');
          delete db.topics['k1'];
          floatTimerClose(); floatTimerOpen();
          const t=(%s)();
          return {tela:t,opcoesReino:[...document.getElementById('ft-reino').options].length};}"""%LER)
        print('   %s · reinos no seletor: %s'%(r['tela'],r['opcoesReino']))
        assert r['tela']['reino']=='' and r['tela']['chefao']==''
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
