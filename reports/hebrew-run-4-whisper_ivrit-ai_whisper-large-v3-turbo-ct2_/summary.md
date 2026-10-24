# Hebrew word-guided editing (FLEURS he_il + inserted stutters)

60 utterances, 2 stutters inserted in each. Recogniser: whisper:ivrit-ai/whisper-large-v3-turbo-ct2.

| mode | word_rep removed | sound_rep removed | prolongation removed | block removed | real speech cut (stuttered input) | utterances with >50 ms real speech cut | real speech cut (fluent input) |
|---|---|---|---|---|---|---|---|
| gentle | 14% | 27% | 39% | 52% | 2.26s total | 13% | 0.60s total |
| full | 42% | 57% | 45% | 63% | 14.04s total | 58% | 12.85s total |
| strong | 43% | 59% | 45% | 76% | 14.04s total | 58% | 12.85s total |

## Examples (examples/NN-before.ogg / NN-after.ogg, full mode)

**01** inserted [('sound_rep', 'מיגרמניה'), ('sound_rep', 'הברי')], real speech cut 0.788s
- text: "הנמל היה האתר של סכסוך  ימי מפורסם מ-1889 כאשר שבע אוניות מגרמניה, ארה""ב ובריטניה סירבו לצאת את הנמל."
- heard: הנמל היה האתר של סכסוך ימים מפורסם ב -1889 כאשר שבע אוניות מגרמניה ארצות הברית ובריטניה סירבו לצאת את הנמל.
- edits: repetition 2.48-2.8 (1 repeat(s) of 'האתר'); repetition 6.04-6.93 (2 repeat(s) of 'כאשר'); block 6.49-6.93 (breath/strain noise, next to another stutter event, inside the word 'כאשר'); repetition 8.07-8.59 (2 repeat(s) of 'מגרמניה'); repetition 10.04-10.6 (2 repeat(s) of 'הברית'); repetition 11.02-11.31 (1 repeat(s) of 'ובריטניה')

**02** inserted [('word_rep', 'לעבראתרים'), ('block', 'ברופאא')], real speech cut 0.270s
- text: רולנדו מנדוזה ירה ברובה ה-M16 שלו אל עבר התיירים.
- heard: שלא אל עבר התיירים, אל עבר התיירים M16 רונלדו מנדוזה ירה ברופא אה.
- edits: repetition 0.66-1.7 (אל עבר התיירים, אל); block 4.83-5.7 (breath/strain noise, inside the word 'ברופא')

**03** inserted [('sound_rep', 'בחומ'), ('block', 'בלסקנה')], real speech cut 0.060s
- text: מומלץ בחום למטיילים לשים לב לסכנה של מזג אוויר קשה שפוקד את האזור מכיוון שהוא עלול לפגוע בתכניות הטיול.
- heard: מומלץ בחום למטיילים הסיפורים. שים לב לסכנה של מזג אוויר קשה שפוקד את האזור מכיוון שהוא עלול לפגוע בתוכניות הטיול.
- edits: block 2.25-3.29 (cut-off sound before the gap); block 3.78-4.2 (breath/strain noise, cut-off sound before the gap); block 4.25-4.73 (breath/strain noise, cut-off sound before the gap); block 4.74-5.18 (breath/strain noise, cut-off sound before the gap); block 5.22-5.7 (breath/strain noise, cut-off sound before the gap); block 5.93-6.24 (breath/strain noise, cut-off sound before the gap, next to another stutter event); repetition 6.24-6.41 (1 repeat(s) of 'עלול'); block 6.48-6.73 (breath/strain noise, cut-off sound before the gap, next to another stutter event)

**04** inserted [('sound_rep', 'טיול'), ('prolongation', 'חוויות')], real speech cut 0.000s
- text: שיתוף של טיול וירטואלי משותף הוא גם דרך נהדרת להתבונן בטיול ולשתף כיתות עתידיות בחוויות.
- heard: שיתוף של טיול וירטואלי משותף הוא גם דרך נהדרת להתבונן בטיול ולשתף כיתות עדידיות וחוויות.
- edits: repetition 1.8-2.32 (2 repeat(s) of 'טיול'); block 7.91-8.44 (cut-off sound before the gap); block 8.82-9.18 (breath/strain noise, next to another stutter event); pause 9.91-11.01 (long pause shortened)

**05** inserted [('sound_rep', 'לפני')], real speech cut 0.110s
- text: בין השעות 22:00-23:00 לפי אזור זמן ההרים (MDT), הוצתה שריפה על ידי האסירים בחצר.
- heard: פרשת אחת צעד, אה, זה, לפ -לפ -לפ -לפני עשור שבועים...
- edits: repetition 1.28-1.41 (1 repeat(s) of 'אה,'); repetition 1.96-2.24 (לפ -לפ -לפ); repetition 2.84-3.04 (1 repeat(s) of 'שבועים...')

**06** inserted [('prolongation', 'משקיף'), ('sound_rep', 'ויבזזוחנויות')], real speech cut 0.000s
- text: "בישקק תוארה כמתדרדרת למצב של ""אנרכיה"" על ידי משקיף אחד, כשכנופיות שוטטו ברחובות ובזזו חנויות של מוצרי צריכה."
- heard: פישקק תאורה כמתדרדרת למצב של אנרכיה על ידי משקיף אחד כשכנופיות שוטטו ברחובות ובזזו חנויות של מוצרי צריכה טוב
- edits: 

**07** inserted [('word_rep', 'מזרח'), ('word_rep', 'חשיבות')], real speech cut 0.407s
- text: באקלים החם של המזרח התיכון, לבית לא הייתה חשיבות רבה כל כך.
- heard: באקלים החם של המזרח, של המזרח התיכון, לבית לא הייתה חשיבות, הייתה חשיבות רבה כל כך.
- edits: repetition 0.27-0.46 (1 repeat(s) of 'באקלים'); repetition 0.8-1.3 (של המזרח, של); block 2.35-2.7 (next to another stutter event); repetition 3.06-3.72 (הייתה חשיבות, הייתה)

**08** inserted [('block', 'פותור'), ('sound_rep', 'השובר')], real speech cut 0.410s
- text: דל פוטרו החזיק ביתרון מוקדם במערכה השנייה, אך גם מערכה זו הצריכה שובר שוויון לאחר תוצאה של 6-6.
- heard: דל פוטרו החזיק ביתרון מוקדם במערכה השנייה, אך גם מערכה זו הצריכה שובר שוויון לאחר תוצאה של 6 -6. יש
- edits: block 1.71-2.65 (breath/strain noise); block 3.14-3.57 (breath/strain noise, inside the word 'החזיק'); block 4.21-4.5 (breath/strain noise, inside the word 'ביתרון'); repetition 7.78-8.48 (2 repeat(s) of 'הצריכה'); repetition 10.58-10.88 (6 -6.); block 11.45-11.91 (breath/strain noise)
