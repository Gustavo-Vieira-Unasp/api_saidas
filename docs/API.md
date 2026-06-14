# Referência da API

URL base: `http://localhost:8000`

Todos os endpoints, exceto `/auth/register` e `/auth/login`, exigem um token bearer:

```
Authorization: Bearer <access_token>
```

O FastAPI também serve docs interativas em `/docs` (Swagger) e `/redoc`.

---

## Autenticação

### `POST /auth/register`
Cria uma conta na plataforma. O RA e a senha são os mesmos usados no site do UNASP;
a senha é armazenada com hash (login) e criptografada (automação).

```json
{ "ra": "123456", "password": "senha-unasp", "profile": "Aluno Graduação", "full_name": "Nome do Amigo" }
```

- `profile`: um de `"Funcionário"`, `"Aluno Graduação"`, `"Aluno Educação Básica"`.
- `full_name`: opcional.

Resposta: `201` com o usuário criado (sem a senha).

### `POST /auth/login`
Obtém um JWT. Aceita `username` (RA) + `password` no formato form-encoded (fluxo OAuth2 password).

Resposta:
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### `GET /auth/me`
Retorna o usuário autenticado atual.

### `PUT /auth/me/profile`
Atualiza o perfil de acesso UNASP usado na automação.

```json
{ "profile": "Aluno Graduação" }
```

### `PUT /auth/me/password`
Atualiza a senha da plataforma e re-criptografa as credenciais UNASP.

```json
{ "current_password": "...", "new_password": "..." }
```

---

## Tipos de saída (templates)

Um tipo de saída armazena dados reutilizáveis do formulário como um `payload` JSON.

### Chaves canônicas do `payload`
Use sempre estas chaves (idênticas ao `field_map.py` do backend):

| Chave | Tipo | Observação |
| ------------- | ------- | --------------------------------------------- |
| `dormir_fora` | radio | `"Sim"` ou `"Não"` |
| `destino` | texto | livre |
| `motivo` | select | ex.: `"Médico"`, `"Visitar família"` |
| `com_quem` | select | `"Sozinho"`, `"Amigo"`, `"Familiar"`, `"UNASP"` |
| `nome_pessoa` | texto | quando aplicável |
| `data_saida` | data | `YYYY-MM-DD` |
| `hora_saida` | hora | `HH:MM` |
| `hora_retorno`| hora | `HH:MM` |
| `descricao` | texto | detalhes adicionais |

### `GET /templates`
Lista os tipos de saída do usuário atual.

### `POST /templates`
```json
{ "name": "Academia dia útil", "payload": { "dormir_fora": "Não", "destino": "Academia", "motivo": "Passeio", "com_quem": "Sozinho", "hora_saida": "18:00", "hora_retorno": "21:00", "descricao": "Treino" } }
```

### `GET /templates/{id}`
### `PUT /templates/{id}`
### `DELETE /templates/{id}`

---

## Saídas (envios)

### `POST /exits/send`
Envia um pedido de saída imediatamente via motor de automação.

```json
{ "template_id": 1 }
```
ou passe dados inline:
```json
{ "payload": { "dormir_fora": "Sim", "destino": "Casa", "motivo": "Visitar família", "com_quem": "Sozinho", "data_saida": "2026-06-20", "hora_saida": "17:00", "hora_retorno": "22:00" } }
```

Resposta:
```json
{
  "id": 10,
  "status": "sent",
  "message": "Submitted successfully",
  "screenshot_path": "/data/screenshots/exit_....png",
  "source": "manual",
  "created_at": "2026-06-13T18:00:00"
}
```

Para exibir o comprovante, use `GET /exits/{id}/screenshot` com o token bearer.

### `POST /exits/batch`
Planeja várias saídas em um intervalo de datas a partir de um tipo de saída ou
`payload`. Para cada data em `[start_date, end_date]` o `payload` base é copiado
com `data_saida` ajustado para aquele dia.

```json
{
  "template_id": 1,
  "start_date": "2026-06-15",
  "end_date": "2026-06-19",
  "weekdays_only": true,
  "hora_saida": "07:00",
  "hora_retorno": "22:00",
  "schedule_at": "06:30"
}
```

- `weekdays_only`: quando `true`, ignora sábados e domingos.
- `hora_saida` / `hora_retorno`: sobrescrevem os horários do `payload` (opcional).
- `schedule_at` (`HH:MM`): se informado, cria um agendamento único por dia nesse
  horário; se omitido, todos os dias são enviados imediatamente.
- O intervalo é limitado a 366 dias.

Resposta:
```json
{
  "sent": [ /* ExitRequestOut quando enviado agora */ ],
  "scheduled": [ /* ScheduleOut quando agendado */ ],
  "failed": [ { "date": "2026-06-16", "error": "mensagem" } ]
}
```

### `GET /exits`
Lista o histórico de envios (mais recentes primeiro). Aceita `?status=sent|failed|pending&limit=50`.

### `GET /exits/{id}`
Detalhes de um único envio.

### `GET /exits/{id}/screenshot`
Retorna a imagem do comprovante (se capturada).

---

## Agendamentos

Um agendamento envia um modelo automaticamente em uma hora / recorrência.

### `GET /schedules`
Lista os agendamentos do usuário.

### `POST /schedules`
```json
{
  "name": "Saída diária academia",
  "template_id": 1,
  "trigger_type": "weekdays",   // um de: once | daily | weekdays | cron
  "run_at": "2026-06-20T18:00:00", // para "once"
  "hour": 18,                       // para daily/weekdays
  "minute": 0,
  "cron": "0 18 * * 1-5",          // para "cron"
  "date_strategy": "today",         // fixed | today | tomorrow
  "enabled": true
}
```

`date_strategy` controla como `data_saida` é resolvida quando o agendamento roda:
`fixed` mantém a data do tipo de saída, enquanto `today`/`tomorrow` calculam a
data no momento da execução (útil para envios diários).

### `GET /schedules/{id}`
### `PUT /schedules/{id}`
Atualiza campos e/ou ativa/desativa. Re-registra a tarefa no APScheduler.

### `DELETE /schedules/{id}`
Remove o agendamento e sua tarefa.

### `POST /schedules/{id}/run-now`
Dispara o envio do agendamento imediatamente (útil para testar).

---

## Valores de status

| Status   | Significado                              |
| -------- | ---------------------------------------- |
| `pending`| Criado, ainda não processado             |
| `sent`   | Enviado com sucesso ao UNASP             |
| `failed` | Envio falhou (veja `message`)            |

## Formato de erro

Os erros seguem o formato padrão do FastAPI:
```json
{ "detail": "Mensagem legível para humanos" }
```
