"""Readable passport assembled from accepted artifacts, without another LLM call."""

from dataclasses import asdict
from typing import Literal

from .inputs import Source
from .models import Extraction, FieldVerdict, Payload, Synthesis, Text


class PassportSection(Payload):
    id: Text
    title: Text
    state: Literal['not_processed', 'extracted', 'reviewed']
    depends_on: list[str]
    checklist: list[dict[str, str]]
    extraction: Extraction | None
    verdict: FieldVerdict | None


class ProjectPassport(Payload):
    schema_version: Literal['project-passport.v1'] = 'project-passport.v1'
    run_status: str
    mode: str
    sources: list[dict[str, str]]
    sections: list[PassportSection]
    synthesis: Synthesis | None


def build_passport(result: dict, sources: dict[str, Source], fields) -> ProjectPassport:
    sections = []
    for field in fields:
        extraction = result['extractions'].get(field.id)
        verdict = result['verdicts'].get(field.id)
        sections.append(PassportSection(
            id=field.id, title=field.title,
            state='reviewed' if verdict else 'extracted' if extraction else 'not_processed',
            depends_on=list(field.depends_on), checklist=[asdict(c) for c in field.checks],
            extraction=Extraction.model_validate(extraction) if extraction else None,
            verdict=FieldVerdict.model_validate(verdict) if verdict else None,
        ))
    return ProjectPassport(run_status=result['status'], mode=result['mode'],
                           sources=[s.metadata() for s in sources.values()], sections=sections,
                           synthesis=Synthesis.model_validate(result['synthesis']) if result.get('synthesis') else None)


def render_passport(passport: ProjectPassport, sources: dict[str, Source]) -> str:
    lines = ['# Паспорт проекта', '', f'Статус прогона: **{passport.run_status}**; режим: {passport.mode}.',
             '', 'Это внутренний рабочий паспорт, не согласованное ТЗ и не единый источник истины.',
             'Ссылки относятся к сохранённым снимкам. Непроверенные выводы не заменяют экспертную оценку.', '']
    if passport.mode == 'replay':
        lines += ['Учебный replay: ответы заранее записаны, качество LLM не измерялось.', '']
    if passport.synthesis:
        lines += ['## Общее понимание', '', passport.synthesis.summary, '']
    else:
        lines += ['Итоговый синтез не принят. Разделы ниже содержат только принятые локальные результаты.', '']
    for section in passport.sections:
        lines += [f'## {section.title} ({section.id})', '', f'Состояние: {section.state}.',
                  f'Основания из разделов: {", ".join(section.depends_on) or "нет заданных зависимостей"}.', '']
        items = {i.check_id: i for i in section.extraction.items} if section.extraction else {}
        checks = {c.check_id: c for c in section.verdict.checks} if section.verdict else {}
        for rule in section.checklist:
            lines += [f'### {rule["id"]}', '', f'Что ищем: {rule["extract"]}', f'Что проверяем: {rule["evaluate"]}', '']
            item = items.get(rule['id'])
            if item is None:
                lines += ['Ещё не обработано; это не означает отсутствие сведений в документе.', '']
            elif not item.evidence:
                lines += ['Извлекатель не нашёл сведений. Это не доказательство их отсутствия.', '']
            else:
                for e in item.evidence:
                    lines += [f'Текст модели: {e.quote}',
                              f'Основание {e.id}: [{e.source_id}:{e.start_line}–{e.end_line}](sources/{e.source_id}.md#L{e.start_line})',
                              f'Роль источника: {sources[e.source_id].role}. Оригинал:', '']
                    lines += ['> ' + line for line in sources[e.source_id].text.splitlines()[e.start_line-1:e.end_line]]
                    lines.append('')
            check = checks.get(rule['id'])
            if check:
                lines += [f'Заключение: **{check.status}**. {check.reason}', '']
        if section.verdict:
            for finding in section.verdict.findings:
                lines += [f'Замечание {finding.id} ({finding.severity}): {finding.statement}',
                          f'Вопрос: {finding.question}', '']
    if passport.synthesis:
        lines += ['## Межраздельные замечания и приоритеты', '']
        for index, finding in enumerate(passport.synthesis.findings, 1):
            lines += [f'{index}. **{finding.severity}** — {finding.statement}',
                      f'   Вопрос: {finding.question}', f'   Влияние: {finding.impact}',
                      f'   Поля: {", ".join(finding.field_ids)}; затронуты: {", ".join(finding.affected_fields)}.', '']
        lines += ['## Проработанность компонентов', '']
        for maturity in passport.synthesis.maturity:
            lines += [f'- {maturity.component}: **{maturity.level}** — {maturity.reason}']
        lines += ['', '## Исключённые замечания', '']
        lines += [f'- {e.finding_id}: {e.reason}' for e in passport.synthesis.excluded_findings]
    return '\n'.join(lines) + '\n'
