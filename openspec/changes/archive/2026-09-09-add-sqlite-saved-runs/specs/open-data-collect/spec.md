## ADDED Requirements

### Requirement: Сбор не повторяется на rerun
Если в одной сессии уже собраны поля для тех же трёх точек и того же выбора юрлица, система MUST NOT вызывать `collect_three` повторно.

#### Scenario: Тот же ключ точек
- GIVEN сбор уже выполнен для набора venue_id и legal_choices
- WHEN интерфейс перерисовывается без смены точек и юрлица
- THEN повторного collect_three нет
