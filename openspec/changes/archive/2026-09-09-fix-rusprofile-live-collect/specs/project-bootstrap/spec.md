## ADDED Requirements

### Requirement: README про живой POST DuckDuckGo
README SHALL кратко сказать, что поиск DuckDuckGo идёт POST и что JSON `has_captcha` на rusprofile не считается закрытой страницей.

#### Scenario: README после живого фикса
- GIVEN README репозитория
- WHEN его читают
- THEN есть POST и has_captcha либо «ложн» капч
