# Prompt — Agenda semanal dentro de "Hoje"

Contexto: plataforma "Vale dos Nomeados" (`app/index.html`), preparação para Enfermeiro Ebserh/HU Brasil (FGV). A agenda semanal por hora já existe (aba "Grade por hora" dentro do Painel), alimentada pelo cronograma ativo (`docs/cronograma/ebserh-2026.json`, motor `crPlano`).

## Objetivo
Ter **uma só tela de agenda**, dentro do grupo **HOJE** do menu, sem duplicar a semana em vários lugares.

## Requisitos
1. **Menu**: criar o item "📅 Agenda" dentro de HOJE (entre Painel e Revisões). O Painel mostra só um resumo do dia (próximo bloco + progresso) com link "Abrir agenda".
2. **Grade por hora de 06:00 às 23:00**, sempre completa (nunca cortar às 22h/23h), abrindo rolada para o próximo bloco de hoje. Linha do "agora" visível.
3. **Visões**: Hoje (lista do dia) e Semana (grade). Sem a lista "Próximos 7 dias".
4. **Compromissos** (trabalho, plantão, academia, etc.): adicionar por toque no horário, com hora de início/fim e repetição semanal opcional. O cronograma encaixa o estudo nos horários livres.
5. **Estudo por hora**: respeitar horas/dia por fase, pausa de 15 min a cada ~80 min, rodízio de matérias, revisões D+1/D+7/D+30 e "Erros" ao final do dia.
6. **Marcar como feito** direto no bloco; atraso reagenda sem bagunçar a semana.
7. **Celular**: sem rolagem lateral da página; grade rola por dentro.
8. Não apagar dados existentes (`db.cronograma`, `db.weeklyPlan`); itens antigos continuam ocultos/recuperáveis.

## Entrega
Código em `app/index.html`, testes e2e em `tests/e2e`, bump do cache em `sw.js`, nota em `docs/cronograma/README.md`.

## O que ainda quero melhorar (preencher)
- [ ]
- [ ]
