## ADDED Requirements

### Requirement: Рубрики 2ГИС из items.rubrics
Система SHALL заполнить поле `twogis_rubrics` из JSON карточки 2ГИС, если в объекте есть массив `rubrics` с именами. Значение SHALL быть строкой топ-рубрик (не больше трёх имён `name` по порядку в массиве). Запрос карточки SHALL включать `items.rubrics`. Если массива нет, он пуст или без имён — значение MUST быть «не найдено». Система MUST NOT выдумывать услуги и MUST NOT брать рубрики с HTML сайта салона.

#### Scenario: Три рубрики в JSON
- GIVEN карточка 2ГИС с `rubrics`: «Маникюр», «Педикюр», «Ногтевой сервис», «Косметология»
- WHEN собирают поля точки
- THEN `twogis_rubrics` содержит «Маникюр», «Педикюр» и «Ногтевой сервис»
- THEN четвёртая рубрика в значение не входит
- THEN HTML сайта салона ради рубрик не вызывается

#### Scenario: Нет rubrics
- GIVEN карточка 2ГИС без массива `rubrics`
- WHEN собирают поля точки
- THEN `twogis_rubrics` — «не найдено», не ноль и не заглушка

### Requirement: Тип места ТЦ улица этаж
Система SHALL заполнить `place_type` только из JSON 2ГИС: `address.building_name` и `address_comment` (плюс улица в `address_name` / `full_address_name` для метки «улица»). Правила: имя здания с маркером ТЦ/ТРЦ/торговый → «ТЦ»; иначе если в комментарии есть «этаж» → метка этажа (MAY оставить текст комментария, например «1 этаж»); иначе если есть адрес улицы без здания → «улица». Нет этих маркеров — «не найдено». Система MUST NOT выдумывать тип места и MUST NOT брать его с сайта салона.

#### Scenario: ТЦ и этаж в JSON
- GIVEN `address.building_name` «ТЦ Атриум» и `address_comment` «1 этаж»
- WHEN собирают поля точки
- THEN `place_type` — «ТЦ»

#### Scenario: Этаж без ТЦ
- GIVEN нет `building_name`, `address_comment` «2 этаж»
- WHEN собирают поля точки
- THEN `place_type` содержит «этаж»

#### Scenario: Только улица
- GIVEN `address_name` «ул. Таганская, 1» без `building_name` и без этажа в комментарии
- WHEN собирают поля точки
- THEN `place_type` — «улица»

#### Scenario: Нет маркеров места
- GIVEN карточка без имени здания, без комментария с этажом и без адреса улицы
- WHEN собирают поля точки
- THEN `place_type` — «не найдено»

### Requirement: Уровень цен только явное поле JSON
Система SHALL заполнить `twogis_price_level` только если в JSON карточки 2ГИС есть явное поле уровня цен (`price_level` или `price` у item, либо атрибут с явным признаком цены). Нет такого поля — значение MUST быть «не найдено». Система MUST NOT делать GET сайта салона, агрегаторов или HTML карточки 2ГИС ради этого поля. Система MUST NOT выводить средний чек из «о нас» или из модели. Каскад сайта для поля `site_about` MUST NOT менять `twogis_price_level`.

#### Scenario: В JSON есть price_level
- GIVEN item 2ГИС с `price_level` «₽₽»
- WHEN собирают поля точки
- THEN `twogis_price_level` содержит это значение
- THEN GET сайта салона из‑за этого поля нет

#### Scenario: В JSON нет цены
- GIVEN карточка без `price_level`, без `price` и без атрибута цены
- WHEN собирают поля точки
- THEN `twogis_price_level` — «не найдено»
- THEN сайт салона не открывают, чтобы угадать чек

### Requirement: Свежесть отзывов честный MISSING
Поля `twogis_last_review`, `twogis_reviews_90d` и `twogis_plus_minus` SHALL оставаться в записи точки. Если каскад API/HTML их не заполнил, значения MUST быть «не найдено», MUST NOT нулём и MUST NOT средним. Этот change MUST NOT добавлять скрейп сайта салона, чтобы их заполнить.

#### Scenario: Поля свежести пусты
- GIVEN JSON 2ГИС без даты отзыва, без окна 90 дней и без плюс/минус
- WHEN собирают поля точки
- THEN три поля свежести — «не найдено»
- THEN значения не подменяются нулём
