# Участие в разработке

Репозиторий принадлежит **Никите Куликову** ([samsebeingener](https://github.com/samsebeingener)). Сайт: [samsebeingener.ru](https://samsebeingener.ru). Зеркало: [GitVerse](https://gitverse.ru/samsebeingener).

## Где слать изменения

Основной канал — **GitHub**: issues и pull request в `https://github.com/samsebeingener/salon-compare`. GitVerse — зеркало; PR туда не обязательны, если нет отдельной договорённости.

В этом репозитории каждый шаг идёт отдельной веткой и PR в `main`.

## Как предложить патч

1. Форкните репозиторий на GitHub (или ветку в своём форке).
2. Сделайте осмысленный коммит с понятным сообщением.
3. Откройте PR в `main`.
4. Кратко опишите, что меняется и зачем.

Перед крупным рефакторингом лучше сначала issue.

## OpenSpec

Перед кодом согласуйте изменение через OpenSpec — так в репозитории остаётся понятная «правда» о продукте.

| Папка | Смысл |
|-------|--------|
| `openspec/specs/` | Что продукт делает **сейчас** |
| `openspec/changes/<имя>/` | Активная работа (proposal, design, tasks, дельты) |
| `openspec/changes/archive/` | Завершённые изменения |

**Обязательный цикл** (фичи и багфиксы с изменением поведения):

1. Создайте change в `openspec/changes/<имя>/`.
2. Напишите падающие тесты, реализуйте, пройдите quality gate.
3. Откройте PR в `main`.
4. После merge — заархивируйте change (`openspec archive <имя>` или sync по `.cursor/skills/openspec-sync-specs/SKILL.md`): перенос в `archive/`, дельты → `openspec/specs/`.

В `openspec/changes/` не должно копиться готовое: держите **0–1** активный change. Нельзя мержить код, расходящийся со `openspec/specs/`, без обновления спеков в том же PR или сразу после него. Мелкие опечатки и правки docs без смены поведения — без change.

Подробности: `openspec/config.yaml`, скиллы `.cursor/skills/openspec-*`.

## Авторство коммитов

Коммиты владельца: имя `Nikita Kulikov`, email `mashajetruj@gmail.com`. Не подставляйте чужой GitHub-аккаунт в историю этого репозитория.

Для своих коммитов используйте свой реальный git author. Не коммитьте секреты, ключи и `.env`.

## Вопросы

Почта: mashajetruj@gmail.com. Не дублируйте туда то, что уже есть в GitHub issue, без нужды.
