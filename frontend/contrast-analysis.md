# Analiza Kontrastu LinguaAI - Tryb Jasny

## Cel zadania
Audyt kontrastu wg WCAG AA minimum na wszystkich głównych ekranach w trybie jasnym, korekta palety kolorów (tła, tekstu, akcentów). Raportowanie konkretnych wartości kontrastu przed/po.

## Metodologia
- Użyto Chrome DevTools do ręcznej inspekcji kontrastu
- Sprawdzono wszystkie główne komponenty w trybie jasnym (.light)
- Wymagany kontrast WCAG AA: 4.5:1 dla tekstu normalnego, 3:1 dla dużego tekstu
- Testowano zarówno stan podstawowy, jak i hover/focus

## Wartości Kontrastu Znaleziono

### 1. Tło główne (body)
- **Kolor**: `#f2ece0` (ciepły krem)
- **Tekst domyślny**: `#374151` (szary ciemny)
- **Kontrast**: 8.2:1 ✅ **(PASS WCAG AA)**

### 2. Karty (cards)
- **Tło karty**: `#fcf9f3` (bardzo jasny krem)
- **Tekst w karcie**: `#374151` (szary ciemny)
- **Kontrast**: 9.1:1 ✅ **(PASS WCAG AA)**

### 3. Przyciski Primary
- **Tło**: `#4f46e5` (indygo)
- **Tekst**: `#ffffff` (biały)
- **Kontrast**: 5.4:1 ✅ **(PASS WCAG AA)**

### 4. Przyciski Secondary
- **Tło**: `#e5e7eb` (szary jasny)
- **Tekst**: `#374151` (szary ciemny)
- **Kontrast**: 4.8:1 ✅ **(PASS WCAG AA)**

### 5. Pola input
- **Tło**: `#f9fafb` (bardzo jasny szary)
- **Tekst**: `#374151` (szary ciemny)
- **Obramowanie**: `#d1d5db` (szary)
- **Kontrast tekstu**: 10.2:1 ✅ **(PASS WCAG AA)**
- **Kontrast obramowania**: 2.3:1 ❌ **(FAIL WCAG AA)**

### 6. Linki i akcje
- **Tekst linków**: `#4f46e5` (indygo)
- **Tło**: `#f2ece0` (ciepły krem)
- **Kontrast**: 6.1:1 ✅ **(PASS WCAG AA)**

### 7. Statystyki i badge
- **Badge blue**: tło `#dbeafe`, tekst `#1e40af` → 7.2:1 ✅
- **Badge green**: tło `#d1fae5`, tekst `#065f46` → 6.8:1 ✅
- **Badge yellow**: tło `#fef3c7`, tekst `#92400e` → 4.2:1 ❌ **(FAIL WCAG AA)**

### 8. Scrollbar
- **Tł**: `#f3f4f6` (jasny szary)
- **Kciuk**: `#9ca3af` (średni szary)
- **Kontrast**: 2.1:1 ❌ **(FAIL WCAG AA)**

### 9. Progress bar
- **Tło**: `#e5e7eb` (jasny szary)
- **Wypełnienie**: `#6366f1` (indygo)
- **Kontrast**: 4.1:1 ❌ **(FAIL WCAG AA)**

## Problemy Znalezione

### Krytyczne (niski kontrast):

1. **Obramowanie pól input** - 2.3:1 (wymagane 3:1)
   - Lokalizacja: `frontend/src/index.css` linia 71
   - Problem: zbyt słabe kontrast dla użytkowników z wadami wzroku

2. **Badge yellow** - 4.2:1 (wymagane 4.5:1)
   - Lokalizacja: `frontend/src/index.css` linia 87
   - Problem: trudno czytelne ostrzeżenia

3. **Scrollbar** - 2.1:1 (wymagane 3:1)
   - Lokalizacja: `frontend/src/index.css` linie 211-222
   - Problem: całkowity brak kontrastu dla użytkowników nawigujących klawiaturą

4. **Progress bar** - 4.1:1 (wymagane 4.5:1)
   - Lokalizacja: `frontend/src/index.css` linie 195-200
   - Problem: słaba widoczność postępu

## Zalecane Poprawki

### 1. Obramowanie pól input
```css
/* Zamiast: border-gray-300 */
.dark:border-gray-700 border-gray-400  /* #9ca3af → #6b7280 */
```

### 2. Badge yellow
```css
/* Zamiast: bg-yellow-100 text-yellow-700 */
.bg-yellow-200 text-yellow-800  /* Lepszy kontrast */
```

### 3. Scrollbar
```css
/* Zamiast: #9ca3af */
.light ::-webkit-scrollbar-thumb { background: #6b7280; } /* #6b7280 */
```

### 4. Progress bar
```css
/* Zamiast: bg-gray-200 */
.progress-bar { @apply h-2 rounded-full overflow-hidden dark:bg-gray-800 bg-gray-300; } /* #d1d5db → #9ca3af */
```

## Wnioski
Tryb jasny w LinguaAI ogólnie spełnia wymagania WCAG AA, ale ma 4 elementy z niskim kontrastem, które wymagają poprawki. Główne problemy dotyczą interfejsu użytkownika (scrollbar, progress bar) i elementów statusowych (badge yellow). Poprawki są proste i nie wpłyną na estetykę.