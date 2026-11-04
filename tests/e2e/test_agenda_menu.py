# Agenda mora no menu HOJE: o botao abre so o card da agenda (grade); o Painel nao repete a semana.
import asyncio,sys
sys.path.insert(0,'/home/user/valedosnomeados/tests/e2e')
from playwright.async_api import async_playwright
from test_aba_dicas import abrir, graves
from _cron_fixture import seed_cron
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(b,seed_cron(),viewport={'width':1300,'height':900})
        r=await page.evaluate("""()=>{window.todayStr=()=>'2026-11-04';db.cronograma={ativo:true,inicio:'2026-11-03',v:2,feitos:{},lidos:{}};
          const vis=s=>{const e=document.querySelector(s);return !!e&&e.offsetParent!==null;};
          showScreen('dashboard');const painel={agenda:vis('.dash-agenda'),hoje:vis('.dash-hoje')};
          document.getElementById('nav-agenda').click();
          const ag={agenda:vis('.dash-agenda'),grade:vis('.cron-grade'),hoje:vis('.dash-hoje'),aba:crAba,
            nav:document.getElementById('nav-agenda').classList.contains('active'),
            labs:[...document.querySelectorAll('.cg-hora')].map(x=>x.textContent)};
          document.getElementById('nav-dashboard').click();
          return {painel,ag,volta:vis('.dash-agenda')};}""")
        print(r,errs)
        assert not r['painel']['agenda'] and r['painel']['hoje']
        a=r['ag']
        assert a['agenda'] and a['grade'] and not a['hoje'] and a['aba']=='grade' and a['nav']
        assert a['labs'][0]=='06:00' and a['labs'][-1]>='22:00'
        assert not r['volta'] and not graves(errs)
        print('erros de JS: nenhum\nOK')
asyncio.run(main())
