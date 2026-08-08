# Упрощенная диаграмма моделей данных (GraphViz)

В этом документе представлена упрощенная диаграмма моделей данных проекта FEP Time Management в формате GraphViz (DOT).

## Диаграмма связей

```dot
digraph DataModel {
    // Настройки графа
    rankdir = LR;
    node [shape=rectangle, style=filled, fillcolor=lightgrey, fontname="Arial"];
    edge [fontname="Arial", fontsize=10];
    
    // Основные сущности
    Specialist [label="{Specialist|id\nfull_name\nemail\nrole\nhourly_rate\nactive\nhire_date\nleave_date}", shape=record];
    Project [label="{Project|id\nname\ndescription\nclient_name\nstatus\nproject_type\ntimesheet_id\nstart_date\nend_date\nbudget\nrepository_url\nspecialist_ids[]}", shape=record];
    TimeEntry [label="{TimeEntry|id\nspecialist_id\nproject_id\ndate\nhours\ndescription}", shape=record];
    PaymentPeriod [label="{PaymentPeriod|id\nname\nstart_date\nend_date\nstatus\nreport_id\ntime_entries[]\nspecialist_totals{}\nproject_totals{}\ntotal_hours}", shape=record];
    ProjectMeta [label="{ProjectMeta|name\ndescription\nclient_name\nproject_type\nstart_date\nend_date\nbudget\ncontract_number\ndrive_folder_id}", shape=record];
    ProjectMetaResponse [label="{ProjectMetaResponse|project_id\nspreadsheet_id\nspreadsheet_url\ndrive_folder_id\ndrive_folder_url\n...}", shape=record];
    
    // Перечисления
    SpecialistRole [label="{SpecialistRole|DEVELOPER\nQA\nDESIGNER\nPROJECT_MANAGER\nDEVOPS}", shape=record, fillcolor=lightyellow];
    ProjectStatus [label="{ProjectStatus|PLANNING\nACTIVE\nON_HOLD\nCOMPLETED\nCANCELLED}", shape=record, fillcolor=lightyellow];
    ProjectType [label="{ProjectType|FIXED_PRICE\nTIME_AND_MATERIALS\nRETAINER}", shape=record, fillcolor=lightyellow];
    PaymentStatus [label="{PaymentStatus|DRAFT\nSUBMITTED\nAPPROVED\nPAID\nREJECTED}", shape=record, fillcolor=lightyellow];
    PeriodStatus [label="{PeriodStatus|OPEN\nCLOSED\nLOCKED}", shape=record, fillcolor=lightyellow];
    
    // Связи
    Specialist -> SpecialistRole [label="has role"];
    Project -> ProjectStatus [label="has status"];
    Project -> ProjectType [label="has type"];
    ProjectMeta -> ProjectType [label="has type"];
    PaymentPeriod -> PaymentStatus [label="has status"];
    
    Specialist -> TimeEntry [label="1 → many", dir=back, arrowhead=crow];
    Project -> TimeEntry [label="1 → many", dir=back, arrowhead=crow];
    Project -> Specialist [label="many → many", dir=both, arrowhead=crow, arrowtail=crow, color=blue];
    PaymentPeriod -> TimeEntry [label="contains", arrowhead=diamond];
    
    ProjectMeta -> Project [label="creates", style=dashed];
    ProjectMeta -> ProjectMetaResponse [label="results in", style=dashed];
}
```

## Как использовать диаграмму

Для визуализации этой диаграммы можно использовать:

1. Онлайн-инструменты, такие как [GraphvizOnline](https://dreampuf.github.io/GraphvizOnline/)
2. Локальные утилиты GraphViz (`dot -Tpng -o data_model.png data_model.dot`)
3. Плагины для IDE, поддерживающие GraphViz

## Сводная таблица отношений

| От | К | Тип отношения |
|---|---|---|
| Specialist | TimeEntry | Один ко многим |
| Project | TimeEntry | Один ко многим |
| Project | Specialist | Многие ко многим |
| PaymentPeriod | TimeEntry | Композиция (содержит) |
| Specialist | SpecialistRole | Ассоциация |
| Project | ProjectStatus | Ассоциация |
| Project | ProjectType | Ассоциация |
| PaymentPeriod | PaymentStatus | Ассоциация |
| ProjectMeta | Project | Создание |
| ProjectMeta | ProjectMetaResponse | Результат создания | 