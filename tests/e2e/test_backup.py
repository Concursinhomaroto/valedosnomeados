import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SEED = make_seed({'studyNickname':'Leo','studyAvatar':'Adam_idle_anim_16x16.png',
                  'kingdoms':[{'id':'k1','name':'Enfermagem','color':'#7c3aed','icon':'fa-heart'}]})

async def estado(page):
    return await page.evaluate("""() => ({
        estado: backupEstado.estado,
        ultima: backupEstado.ultima,
        erro: backupEstado.erro,
        visivel: (()=>{const e=document.getElementById('backup-badge');
            return !!e && getComputedStyle(e).display!=='none';})(),
        texto: (document.getElementById('backup-badge')||{}).textContent||'',
        classe: (document.getElementById('backup-badge')||{}).className||'',
        meta: Object.keys((window.__root.users.TEST_UID_LEO||{}).vdn_v1_backupMeta||{}),
        copias: Object.keys((window.__root.users.TEST_UID_LEO||{}).vdn_v1_backups||{}),
    })""")

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, SEED)
        try:
            await page.evaluate("() => showScreen('dashboard')")
            await page.wait_for_timeout(600)

            # --- 1) o backup roda sozinho no primeiro save da sessao ---
            hoje=await page.evaluate("() => todayStr()")
            r=await estado(page)
            print('1) depois do boot ->', r['estado'], '|', repr(r['texto'].strip()),
                  '| meta:', r['meta'], '| cópias:', r['copias'])
            assert r['visivel'], 'o selo do backup não aparece no painel'
            assert r['estado']=='ok' and r['ultima']==hoje, r
            assert 'bk-ok' in r['classe'], r['classe']
            assert 'backup de hoje' in r['texto']
            assert r['meta']==[hoje] and r['copias']==[hoje], r

            # --- 2) a copia e o banco inteiro, nao um pedaco ---
            copia_ok=await page.evaluate("() => { const c=window.__root.users.TEST_UID_LEO.vdn_v1_backups[todayStr()];"
                                         "return !!c && Array.isArray(c.kingdoms) && c.kingdoms.length===1 && c.xp===db.xp; }")
            print('2) a cópia contém o banco completo?', copia_ok)
            assert copia_ok

            # --- 3) o selo não mente quando o backup some do servidor ---
            await page.evaluate("""() => { delete window.__root.users.TEST_UID_LEO.vdn_v1_backupMeta;
                                           backupEstadoChecado=false; backupCheckInicial(); }""")
            await page.wait_for_timeout(400)
            r=await estado(page)
            print('3) backup apagado no servidor ->', r['estado'], '|', repr(r['texto'].strip()))
            assert r['estado']=='nunca', 'o selo continuou dizendo que existe backup'
            assert 'sem backup' in r['texto'], f"o selo continuou escrito {r['texto']!r} depois do backup sumir"
            assert 'bk-erro' in r['classe'], r['classe']

            # --- 4) botão "fazer backup agora" grava mesmo com o cache local dizendo que já rodou hoje ---
            await page.evaluate("() => { localStorage.setItem('vdn_backup_last_date', todayStr()); }")
            await page.evaluate("() => { db.xp=(db.xp||0)+1; saveDB(); }")
            await page.wait_for_timeout(1200)
            r=await estado(page)
            print('4a) com o cache local dizendo "já fiz hoje", meta:', r['meta'], '(esperado: vazio)')
            assert r['meta']==[], 'o curto-circuito do localStorage não está funcionando'
            await page.evaluate("() => forcarBackupAgora()")
            await page.wait_for_timeout(900)
            r=await estado(page)
            print('4b) depois do "fazer backup agora" ->', r['estado'], '| meta:', r['meta'])
            assert r['estado']=='ok' and r['meta']==[hoje], r

            # --- 5) falha de permissão: o selo fica vermelho em vez de mentir ---
            await page.evaluate("""() => {
                const orig=firebaseDB.ref;
                firebaseDB.ref=(p)=>{ const r=orig(p);
                    const up=r.update.bind(r);
                    r.update=(v)=>{ if(Object.keys(v).some(k=>k.indexOf('vdn_v1_backup')===0))
                        return Promise.reject(new Error('permission_denied at /users/uid/vdn_v1_backups'));
                        return up(v); };
                    return r; };
                delete window.__root.users.TEST_UID_LEO.vdn_v1_backupMeta;
                localStorage.removeItem('vdn_backup_last_date');
                backupFailedThisSession=false; backupCheckInFlight=false;
                maybeBackupDB();
            }""")
            await page.wait_for_timeout(900)
            r=await estado(page)
            print('5) gravação negada ->', r['estado'], '|', repr(r['texto'].strip()), '|', r['classe'])
            print('   motivo guardado:', repr(r['erro']))
            assert r['estado']=='erro', r
            assert 'bk-erro' in r['classe']
            assert 'backup falhou' in r['texto']
            assert 'permission_denied' in r['erro']

            # --- 6) o modal de detalhes abre e explica o que fazer ---
            await page.evaluate("() => abrirDetalhesBackup()")
            await page.wait_for_timeout(250)
            m=await page.evaluate("""() => ({aberto:document.getElementById('modal').classList.contains('open'),
                titulo:(document.getElementById('modal-title')||{}).textContent||'',
                corpo:(document.getElementById('modal-body')||{}).textContent||''})""")
            print('6) modal:', repr(m['titulo'].strip()), '| aberto:', m['aberto'])
            assert m['aberto']
            assert 'vdn_v1_backups' in m['corpo'], 'o modal não diz qual caminho liberar nas regras'
            assert 'Fazer backup agora' in m['corpo']

            errs=real_errors(errors)
            assert not errs, errs
            print('\nTODOS OS 6 TESTES DE BACKUP PASSARAM')
        finally:
            await browser.close()

asyncio.run(main())
