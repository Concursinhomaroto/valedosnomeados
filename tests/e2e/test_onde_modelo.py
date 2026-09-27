import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
seed=make_seed({'studyNickname':'Leo','plan':'full','onboardingCompleted':True,'geminiApiKey':'K',
  'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],'topics':{'k1':[]}})
async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        r=await page.evaluate("""()=>{
            openAISettingsModal();
            const m=document.querySelector('.modal-body')||document.body;
            const btn=t=>[...m.querySelectorAll('button,label')].some(x=>x.textContent.includes(t));
            return {titulo:(document.querySelector('.modal-title')||{}).textContent||'',
                    exportar:btn('Exportar meu modelo'),
                    importar:btn('Importar um modelo'),
                    backup:btn('Ver cópias de segurança'),
                    input:!!document.getElementById('modelo-import-inp')};}""")
        print('--- ⚙️ da barra lateral')
        for k,v in r.items(): print('    %-10s %s'%(k+':',v))
        r2=await page.evaluate("""()=>{closeModal();abrirDetalhesBackup();
            const m=document.querySelector('.modal-body')||document.body;
            return [...m.querySelectorAll('button,label')].some(x=>x.textContent.includes('Exportar meu modelo'));}""")
        print('\n--- modal do selo de backup ainda tem o bloco: %s'%r2)
        r3=await page.evaluate("""()=>{closeModal();
            backupEstado={estado:'ok',ultima:todayStr(),ts:Date.now(),erro:null};
            renderBackupBadge();
            const el=document.getElementById('backup-badge');
            return {visivel:el.style.display,texto:el.textContent.trim(),
                    seta:!!el.querySelector('.fa-chevron-right'),papel:el.getAttribute('role'),
                    titulo:el.getAttribute('title')};}""")
        print('\n--- selo de backup: %s'%r3)
        print('erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await b.close()
asyncio.run(main())
