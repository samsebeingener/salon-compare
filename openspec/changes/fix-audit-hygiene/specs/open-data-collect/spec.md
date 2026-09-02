## ADDED Requirements

### Requirement: HTML только по явным маркерам
Живой `OpenHtmlParser` SHALL заполнить `about`, `rating`, `review_count` и `address`, если в открытом HTML есть явный маркер. About MUST браться из JSON-LD `description`, иначе из `meta name="description"`, иначе из текста после заголовка «О нас» или «О студии» (не длиннее 280 символов). Rating и число отзывов MUST браться из JSON-LD `aggregateRating` (`ratingValue`, `reviewCount`). Адрес — из JSON-LD `address`. Нет маркера — поле MUST остаться пустым, без угадывания по CSS-классу вроде `class="rating"`. Соседей из HTML MUST NOT выдумывать.

#### Scenario: JSON-LD с описанием и рейтингом
- GIVEN HTML с JSON-LD: description «Студия у метро», aggregateRating 4.6 и reviewCount 80, PostalAddress
- WHEN парсят открытую страницу
- THEN about содержит «Студия у метро»
- THEN rating 4.6 и review_count 80
- THEN address не пустой

#### Scenario: Нет маркеров — не выдумывать
- GIVEN HTML только с `<div class="rating">4.6</div>`
- WHEN парсят
- THEN rating, about и plus_minus пустые
